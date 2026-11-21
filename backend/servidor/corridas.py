"""Una corrida: varias variantes de una política preguntadas a los mismos agentes, en paralelo.

Los lotes de agentes se reparten en un grupo de hilos; cada lote que termina se publica como
evento para que la interfaz encienda esos puntos en el mapa. Si se piden iteraciones, al
terminar las variantes escritas un agente redacta una versión nueva que responde a las
objeciones de quienes estuvieron en contra, y se pregunta otra vez.
"""

import hashlib
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from .agentes import Agente
from . import metodo
from .metodo import temas_de
from .motor import PRIORIDAD, Consumo, Motor, Respuesta

CARPETA_CACHE = Path(__file__).resolve().parent.parent / "data" / "cache"

SISTEMA_ITERACION = (
    "Eres un asesor de políticas públicas en Chile. Reescribes propuestas para que más personas "
    "las apoyen sin abandonar su objetivo, respondiendo a las objeciones concretas que dieron las "
    "personas consultadas. Escribes en lenguaje simple, como se le explicaría a cualquier vecino."
)

ESQUEMA_ITERACION = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string"},
        "texto": {"type": "string"},
        "cambio": {"type": "string"},
    },
    "required": ["titulo", "texto", "cambio"],
    "additionalProperties": False,
}

SISTEMA_RESUMEN = (
    "Resumes documentos legales o de políticas públicas de Chile para que cualquier persona los "
    "entienda. Explicas qué cambia, a quién afecta, quién paga y qué gana cada parte, sin opinar."
)

ESQUEMA_RESUMEN = {
    "type": "object",
    "properties": {"titulo": {"type": "string"}, "resumen": {"type": "string"}},
    "required": ["titulo", "resumen"],
    "additionalProperties": False,
}

# A cuántas personas de cada lote se les pide, aparte, una frase sobre lo que respondieron.
VOCES_POR_LOTE = 2
# Las frases son una llamada aparte por lote. Con estas alcanza para los globos del mapa y para
# redactar la variante siguiente; pedirlas a todos los lotes duplicaba los procesos y la espera.
MAXIMO_LLAMADAS_VOCES = 30
# Personas que van primero, en lotes chicos, para que haya respuestas a los pocos segundos. Un lote
# tarda más mientras más personas lleva (2 personas, unos 3 s; 5, unos 5 s; 20, unos 13 s), así que
# la partida va en escalera: (personas, tamaño del lote). Sin ella el avance se queda pegado entre
# las primeras respuestas y la llegada de los lotes grandes.
ESCALERA = [(24, 2), (40, 5)]
AVANZADA = sum(personas for personas, _ in ESCALERA)

# Segundos en que se reproduce lo que ya estaba en caché.
REPRODUCCION = 6.0

# Sobre este largo, el documento se resume antes de dárselo a los agentes.
LARGO_RESUMIR = 3500


def postura(acuerdo: int) -> str:
    return "favor" if acuerdo >= 5 else "contra" if acuerdo <= 3 else "indecisa"


@dataclass
class Caso:
    id: str
    letra: str
    texto: str
    documento: dict | None = None
    iteracion: dict | None = None
    titulo: str = ""
    respuestas: dict[int, Respuesta] = field(default_factory=dict)

    def politica(self) -> str:
        partes = [self.texto.strip()] if self.texto.strip() else []
        if self.documento:
            partes.append(self.documento["texto"].strip())
        return "\n\n".join(partes)

    def apoyo(self) -> float:
        if not self.respuestas:
            return 0.0
        return sum(1 for r in self.respuestas.values() if r.acuerdo >= 5) / len(self.respuestas)


class Cache:
    """Respuestas ya obtenidas, por política y agente: repetir una pregunta no vuelve a gastar."""

    def __init__(self, carpeta: Path = CARPETA_CACHE):
        carpeta.mkdir(parents=True, exist_ok=True)
        self._archivo = carpeta / "respuestas.jsonl"
        self._datos: dict[tuple[str, str, str], tuple[list[int], str]] = {}
        self._cerrojo = threading.Lock()
        if self._archivo.exists():
            with open(self._archivo, encoding="utf-8") as f:
                for linea in f:
                    try:
                        fila = json.loads(linea)
                    except ValueError:
                        continue
                    if isinstance(fila.get("r"), list):
                        self._datos[(fila["p"], fila["m"], fila["a"])] = (fila["r"], fila.get("f", ""))

    @staticmethod
    def huella(politica: str) -> str:
        return hashlib.sha256(" ".join(politica.split()).lower().encode()).hexdigest()[:20]

    def buscar(self, huella: str, modelo: str, agente: Agente) -> tuple[list[int], str] | None:
        return self._datos.get((huella, modelo, agente.id))

    def guardar(self, huella: str, modelo: str, agentes: dict[int, Agente], respuestas: list[Respuesta]) -> None:
        with self._cerrojo, open(self._archivo, "a", encoding="utf-8") as f:
            for r in respuestas:
                clave = (huella, modelo, agentes[r.agente].id)
                self._datos[clave] = (r.respuestas, r.frase)
                f.write(json.dumps({"p": huella, "m": modelo, "a": clave[2], "r": r.respuestas, "f": r.frase}, ensure_ascii=False) + "\n")


class Corrida:
    def __init__(self, motor: Motor, cache: Cache, agentes: list[Agente], casos: list[Caso],
                 iteraciones: int, lote: int, concurrencia: int, letras: str):
        self.id = uuid.uuid4().hex[:12]
        self.motor = motor
        #: La encuesta, fija: cada agente pone una nota de 1 a 7 a cada pregunta, con su escala.
        self.preguntas = list(metodo.PREGUNTAS)
        #: Lo que distingue estas respuestas en la caché: el modelo y todo lo que leyó.
        self.clave = motor.clave()
        self.cache = cache
        self.agentes = agentes
        self.por_indice = {a.indice: a for a in agentes}
        self.casos = casos
        self.iteraciones = iteraciones
        self.lote = lote
        self.concurrencia = concurrencia
        self.letras = letras
        self.consumo = Consumo()
        self.inicio = time.time()
        self.eventos: list[tuple[str, dict]] = []
        self.terminada = False
        self.cancelada = False
        self._condicion = threading.Condition()
        self._grupo: ThreadPoolExecutor | None = None
        self._voces: list = []
        self._voces_pedidas: dict[int, int] = {}
        self._cerrojo = threading.Lock()

    # Eventos ------------------------------------------------------------------------------

    def publicar(self, tipo: str, datos: dict) -> None:
        with self._condicion:
            self.eventos.append((tipo, datos))
            self._condicion.notify_all()

    def esperar(self, desde: int, espera: float = 15.0) -> list[tuple[str, dict]]:
        with self._condicion:
            if len(self.eventos) <= desde and not self.terminada:
                self._condicion.wait(espera)
            return self.eventos[desde:]

    def metricas(self) -> dict:
        return {
            "llamadas": self.consumo.llamadas,
            "costo_usd": round(self.consumo.costo_usd, 4),
            "tokens": self.consumo.tokens_entrada + self.consumo.tokens_salida,
            "segundos": round(time.time() - self.inicio, 1),
        }

    # Trabajo ------------------------------------------------------------------------------

    def _lote(self, numero: int, caso: Caso, huella: str, agentes: list[Agente], urgente: bool = False) -> None:
        if self.cancelada:
            return
        PRIORIDAD.baja = not urgente
        respuestas: list[Respuesta] = []
        for intento in range(3):
            try:
                resultado = self.motor.responder(caso.politica(), agentes)
                respuestas = resultado.respuestas
                with self._cerrojo:
                    self.consumo.sumar(resultado.consumo)
                faltan = [a for a in agentes if a.indice not in {r.agente for r in respuestas}]
                if not faltan or intento == 2:
                    break
                # Si el modelo se saltó a alguien, se le vuelve a preguntar solo a esas personas.
                previas = respuestas
                resultado = self.motor.responder(caso.politica(), faltan)
                respuestas = previas + resultado.respuestas
                with self._cerrojo:
                    self.consumo.sumar(resultado.consumo)
                break
            except Exception as error:  # se reintenta; la corrida sigue con el resto
                if intento == 2:
                    self.publicar("aviso", {"mensaje": f"Un lote de {len(agentes)} agentes falló: {error}"[:300]})
        self._entregar(numero, caso, huella, respuestas, desde_cache=False)

    def _entregar(self, numero: int, caso: Caso, huella: str, respuestas: list[Respuesta], desde_cache: bool) -> None:
        if not respuestas:
            return
        with self._cerrojo:
            for r in respuestas:
                caso.respuestas[r.agente] = r
        if not desde_cache:
            self.cache.guardar(huella, self.clave, self.por_indice, respuestas)
        self.publicar("respuestas", {
            "caso": numero,
            "cache": desde_cache,
            "r": [[r.agente, r.acuerdo, r.frase, r.respuestas] for r in respuestas],
            "metricas": self.metricas(),
        })
        if not desde_cache and not self.cancelada:
            self._pedir_voces(numero, caso, huella, respuestas)

    def _pedir_voces(self, numero: int, caso: Caso, huella: str, respuestas: list[Respuesta]) -> None:
        """Aparte de la encuesta: a unas pocas personas de cada lote se les pide una frase sobre lo que ya respondieron."""
        favor = [r for r in respuestas if r.acuerdo >= 5][:1]
        resto = [r for r in respuestas if r.acuerdo <= 4][:VOCES_POR_LOTE - len(favor)]
        elegidas = favor + resto
        if not elegidas or self._grupo is None:
            return
        with self._cerrojo:
            pedidas = self._voces_pedidas.get(numero, 0)
            if pedidas >= MAXIMO_LLAMADAS_VOCES:
                return
            self._voces_pedidas[numero] = pedidas + 1
        self._voces.append(self._grupo.submit(self._voces_de, numero, caso, huella, elegidas))

    def _voces_de(self, numero: int, caso: Caso, huella: str, elegidas: list[Respuesta]) -> None:
        PRIORIDAD.baja = True
        try:
            pares = [(self.por_indice[r.agente], r) for r in elegidas]
            frases, consumo = self.motor.comentar(caso.politica(), pares)
        except Exception:
            return  # las frases son un adorno: si fallan, la encuesta sigue igual
        if not frases:
            return
        with self._cerrojo:
            self.consumo.sumar(consumo)
            for agente, frase in frases:
                if agente in caso.respuestas:
                    caso.respuestas[agente].frase = frase
        self.cache.guardar(huella, self.clave, self.por_indice, [caso.respuestas[a] for a, _ in frases if a in caso.respuestas])
        self.publicar("voces", {"caso": numero, "r": [[agente, frase] for agente, frase in frases], "metricas": self.metricas()})

    def _esperar_voces(self) -> None:
        pendientes, self._voces = self._voces, []
        for tarea in pendientes:
            tarea.result()

    def _preguntar(self, grupo: ThreadPoolExecutor, numero: int) -> list:
        caso = self.casos[numero]
        huella = Cache.huella(caso.politica())
        pendientes = []
        guardadas = []
        for agente in self.agentes:
            previa = self.cache.buscar(huella, self.clave, agente)
            if previa:
                guardadas.append(Respuesta(agente.indice, previa[0], previa[1]))
            else:
                pendientes.append(agente)
        tareas = []
        # Lo que ya estaba en caché llega de a poco, para que el mapa igual se vea encender.
        if guardadas:
            tareas.append(grupo.submit(self._reproducir, numero, caso, huella, guardadas))
        # Una avanzada de lotes chicos responde antes: el mapa empieza a encenderse y llegan las primeras frases.
        avanzada = pendientes[:AVANZADA] if len(pendientes) > AVANZADA * 2 else []
        desde = 0
        for personas, tamano in ESCALERA if avanzada else []:
            tramo = avanzada[desde:desde + personas]
            desde += personas
            for k in range(0, len(tramo), tamano):
                tareas.append(grupo.submit(self._lote, numero, caso, huella, tramo[k:k + tamano], True))
        resto = pendientes[len(avanzada):]
        for k in range(0, len(resto), self.lote):
            tareas.append(grupo.submit(self._lote, numero, caso, huella, resto[k:k + self.lote]))
        return tareas

    def _reproducir(self, numero, caso, huella, respuestas):
        """Un solo hilo entrega lo guardado en tandas, sin ocupar a los que llaman al modelo."""
        partes = [respuestas[k:k + self.lote] for k in range(0, len(respuestas), self.lote)]
        for parte in partes:
            if self.cancelada:
                return
            time.sleep(REPRODUCCION / len(partes))
            self._entregar(numero, caso, huella, parte, desde_cache=True)

    def _cerrar_caso(self, numero: int) -> None:
        caso = self.casos[numero]
        self.publicar("caso_listo", {"caso": numero, "apoyo": round(caso.apoyo(), 4), "respondidas": len(caso.respuestas), "metricas": self.metricas()})

    def _iterar(self, numero: int) -> Caso:
        """Redacta una versión nueva a partir de la variante con más apoyo y sus objeciones."""
        base = max(self.casos, key=lambda c: c.apoyo())
        objeciones = [r for r in base.respuestas.values() if r.acuerdo <= 4 and r.frase]
        objeciones.sort(key=lambda r: r.acuerdo)
        muestra = objeciones[:: max(1, len(objeciones) // 45)][:45]
        apoyos = [r for r in base.respuestas.values() if r.acuerdo >= 5 and r.frase]
        valoradas = apoyos[:: max(1, len(apoyos) // 15)][:15]
        lineas = []
        for r in muestra:
            a = self.por_indice[r.agente]
            lineas.append(f"- ({a.atributos.get('Edad')}, {a.comuna}, {a.atributos.get('Tramo socioeconómico', '')[:9]}; acuerdo {r.acuerdo}/7) {r.frase}")
        todas = list(base.respuestas.values())
        medias = "\n".join(
            f"- {texto} (1 = {minimo}, 7 = {maximo}) Media {sum(r.respuestas[k] for r in todas) / len(todas):.1f} de 7."
            for k, (texto, (minimo, maximo)) in enumerate(zip(self.preguntas, metodo.ESCALAS))
        )
        prompt = (
            f"# Propuesta actual (variante {base.letra}, {round(base.apoyo() * 100)} % a favor)\n\n{base.politica()}\n\n"
            f"# Cómo respondieron la encuesta\n\n{medias}\n\n"
            f"# Lo que dijeron quienes no la apoyan\n\n" + "\n".join(lineas) + "\n\n"
            f"# Lo que valoran quienes sí la apoyan (no lo pierdas)\n\n" + "\n".join(f"- {r.frase}" for r in valoradas) + "\n\n"
            "Escribe una versión mejorada de la propuesta que mantenga su objetivo y todo lo que valoran "
            "quienes la apoyan, y que responda a las objeciones más repetidas sin agregar costos ni "
            "condiciones que la hagan más difícil de aceptar. Cambia lo mínimo necesario. Devuelve `titulo` (la propuesta nueva en una sola oración de máximo "
            "16 palabras, como un titular), `texto` (la propuesta nueva completa, máximo 110 palabras, "
            "lenguaje simple, sin viñetas) y `cambio` (una frase de máximo 14 palabras que diga qué cambiaste)."
        )
        datos, consumo = self.motor.redactar(SISTEMA_ITERACION, prompt, ESQUEMA_ITERACION)
        with self._cerrojo:
            self.consumo.sumar(consumo)
        return Caso(
            id=f"iteracion-{numero}",
            letra=self.letras[len(self.casos)],
            texto=datos["texto"].strip(),
            titulo=datos["titulo"].strip(),
            iteracion={"de": base.letra, "numero": numero, "cambio": datos["cambio"].strip()},
        )

    def correr(self) -> None:
        try:
            self.publicar("inicio", {
                "motor": self.motor.describir(),
                "agentes": len(self.agentes),
                "casos": [self._caso_publico(c) for c in self.casos],
                "iteraciones": self.iteraciones,
                "preguntas": self.preguntas,
            })
            with ThreadPoolExecutor(max_workers=self.concurrencia) as grupo:
                self._grupo = grupo
                # Las variantes escritas van todas juntas; la A primero en la cola.
                por_caso = [self._preguntar(grupo, k) for k in range(len(self.casos))]
                for k, tareas in enumerate(por_caso):
                    for tarea in tareas:
                        tarea.result()
                    self._cerrar_caso(k)
                for n in range(1, self.iteraciones + 1):
                    if self.cancelada or len(self.casos) >= len(self.letras):
                        break
                    self.publicar("redactando", {"numero": n, "metricas": self.metricas()})
                    # El agente que reescribe lee las frases: se espera a que lleguen.
                    self._esperar_voces()
                    nuevo = self._iterar(n)
                    self.casos.append(nuevo)
                    k = len(self.casos) - 1
                    self.publicar("caso", {"caso": k, **self._caso_publico(nuevo), "metricas": self.metricas()})
                    for tarea in self._preguntar(grupo, k):
                        tarea.result()
                    self._cerrar_caso(k)
                self._esperar_voces()
            self.publicar("fin", {"metricas": self.metricas(), "apoyos": [round(c.apoyo(), 4) for c in self.casos]})
        except Exception as error:
            self.publicar("falla", {"mensaje": str(error)[:400]})
        finally:
            with self._condicion:
                self.terminada = True
                self._condicion.notify_all()

    def _caso_publico(self, caso: Caso) -> dict:
        return {
            "id": caso.id,
            "letra": caso.letra,
            "texto": caso.texto,
            "titulo": caso.titulo or (caso.documento.get("titulo", "") if caso.documento else ""),
            "documento": {"nombre": caso.documento["nombre"], "titulo": caso.documento.get("titulo", "")} if caso.documento else None,
            "iteracion": caso.iteracion,
            # Los temas que el filtro del perfil detectó en el texto: deciden qué datos de cada persona lee el modelo.
            "temas": temas_de(caso.politica()),
        }


def resumir_documento(motor: Motor, nombre: str, texto: str) -> tuple[dict, Consumo]:
    """Deja el documento en un largo que los agentes puedan leer en cada lote."""
    if len(texto) <= LARGO_RESUMIR:
        return {"nombre": nombre, "titulo": nombre, "texto": texto[:LARGO_RESUMIR * 3]}, Consumo()
    prompt = (
        f"# Documento: {nombre}\n\n{texto[:400_000]}\n\n"
        "Devuelve `titulo` (nombre corto de la propuesta, máximo 8 palabras) y `resumen` (máximo 220 "
        "palabras, texto corrido sin markdown ni viñetas: qué propone, a quién afecta, quién paga, qué gana cada parte y desde cuándo)."
    )
    datos, consumo = motor.redactar(SISTEMA_RESUMEN, prompt, ESQUEMA_RESUMEN)
    return {"nombre": nombre, "titulo": datos["titulo"].strip(), "texto": datos["resumen"].strip(), "largo_original": len(texto)}, consumo
