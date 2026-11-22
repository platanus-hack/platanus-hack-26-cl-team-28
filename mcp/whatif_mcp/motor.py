"""Recibe resultados calculados por los agentes del cliente, con un plazo para cada corrida."""

from collections import OrderedDict
from dataclasses import dataclass
import json
import threading
import time
from uuid import uuid4

from jsonschema import ValidationError, validate

from servidor import metodo
from servidor.corridas import Cache, ESQUEMA_ITERACION
from servidor.motor import ESQUEMA_LOTE, ESQUEMA_VOCES, Consumo, Motor, ResultadoLote, leer_lote, leer_voces

MODELO = "IA del cliente MCP · resultados declarados"
INACTIVIDAD = 180
PLAZO_CORRIDA = 1800
LOTES_POR_ENTREGA = 6
CARACTERES_POR_ENTREGA = 28_000


class SinCache(Cache):
    """Las respuestas que devuelve un cliente no alimentan la caché del motor web."""

    def __init__(self):
        pass

    def buscar(self, huella, modelo, agente):
        return None

    def guardar(self, huella, modelo, agentes, respuestas):
        pass


@dataclass
class Lote:
    pedido: dict
    esquema: dict
    respuesta: dict | None = None


class MotorCliente(Motor):
    nombre = "MCP"
    modelo = MODELO

    def __init__(self):
        self._condicion = threading.Condition()
        self._lotes: OrderedDict[str, Lote] = OrderedDict()
        self._entregados: set[str] = set()
        self._ultimo_contacto = self._inicio = time.monotonic()
        self._cerrado = False
        self.vencido = False

    def describir(self):
        return {"nombre": self.nombre, "modelo": self.modelo}

    def cerrar(self):
        with self._condicion:
            self._cerrado = True
            self._lotes.clear()
            self._entregados.clear()
            self._condicion.notify_all()

    def _en_plazo(self):
        ahora = time.monotonic()
        if ahora - self._ultimo_contacto >= INACTIVIDAD or ahora - self._inicio >= PLAZO_CORRIDA:
            self.vencido = True
        return not self._cerrado and not self.vencido

    def _solicitar(self, tipo, entrada, esquema):
        id_lote = uuid4().hex
        lote = Lote({"lote": id_lote, "tipo": tipo, "entrada": entrada, "salida": esquema}, esquema)
        with self._condicion:
            if not self._en_plazo():
                raise RuntimeError("La sesión del cliente terminó.")
            self._lotes[id_lote] = lote
            self._condicion.notify_all()
            try:
                while lote.respuesta is None and self._en_plazo():
                    self._condicion.wait(1)
                if lote.respuesta is None:
                    raise RuntimeError("El cliente no entregó este lote.")
                return lote.respuesta, Consumo(llamadas=1)
            finally:
                self._lotes.pop(id_lote, None)

    def trabajo(self, entregas):
        with self._condicion:
            if not self._en_plazo():
                return {"lotes": [], "recibidos": []}
            self._ultimo_contacto = time.monotonic()
            nuevos = {}
            for id_lote, salida in entregas:
                if id_lote in nuevos:
                    raise ValueError("Cada lote puede aparecer una sola vez por entrega.")
                if id_lote in self._entregados:
                    continue
                lote = self._lotes.get(id_lote)
                if lote is None:
                    raise ValueError("Uno de los lotes no pertenece a esta corrida.")
                try:
                    validate(salida, lote.esquema)
                    validar_salida(lote.pedido, salida)
                except (ValidationError, ValueError):
                    raise ValueError(f"La salida del lote {id_lote} no cumple el esquema de trabajo.") from None
                nuevos[id_lote] = salida
            for id_lote, salida in nuevos.items():
                self._lotes[id_lote].respuesta = salida
                self._entregados.add(id_lote)
            self._condicion.notify_all()
            self._condicion.wait_for(
                lambda: self._cerrado or any(l.respuesta is None for l in self._lotes.values()),
                timeout=1.5,
            )
            pendientes = []
            caracteres = 0
            for lote in self._lotes.values():
                if lote.respuesta is not None:
                    continue
                caracteres += len(json.dumps(lote.pedido, ensure_ascii=False))
                if pendientes and (caracteres > CARACTERES_POR_ENTREGA or len(pendientes) == LOTES_POR_ENTREGA):
                    break
                pendientes.append(lote.pedido)
            return {
                "lotes": pendientes,
                "recibidos": [id_lote for id_lote, _ in entregas],
            }

    @staticmethod
    def _personas(agentes):
        # Se usa el resumen que la web ya muestra. Los IDs, pesos y coordenadas quedan fuera del lote.
        return [{"i": k, "rasgos": agente.atributos} for k, agente in enumerate(agentes)]

    def responder(self, politica, agentes):
        entrada = {
            "propuesta": politica,
            "personas": self._personas(agentes),
            "encuesta": [
                {"pregunta": pregunta, "nota_1": escala[0], "nota_7": escala[1]}
                for pregunta, escala in zip(metodo.PREGUNTAS, metodo.ESCALAS)
            ],
        }
        datos, consumo = self._solicitar("encuesta", entrada, ESQUEMA_LOTE)
        return ResultadoLote(leer_lote(datos, agentes), consumo)

    def comentar(self, politica, pares):
        personas = self._personas([agente for agente, _ in pares])
        for persona, (_, respuesta) in zip(personas, pares):
            persona["notas"] = respuesta.respuestas
        entrada = {"propuesta": politica, "pregunta": metodo.PREGUNTAS[0], "personas": personas}
        datos, consumo = self._solicitar("voces", entrada, ESQUEMA_VOCES)
        return leer_voces(datos, pares), consumo

    def redactar(self, sistema, prompt, esquema):
        # Corrida prepara las objeciones y el resumen. Las instrucciones de la web se quedan en el servidor.
        datos, separador, _ = prompt.rpartition("\n\nEscribe una versión mejorada")
        if not separador or esquema != ESQUEMA_ITERACION:
            raise RuntimeError("La versión instalada del redactor no admite este lote.")
        return self._solicitar("redaccion", {"propuesta_y_evidencia": datos}, ESQUEMA_ITERACION)


def validar_salida(pedido, salida):
    tipo = pedido["tipo"]
    if tipo == "redaccion":
        if any(not salida[k].strip() or len(salida[k]) > maximo
               for k, maximo in {"titulo": 200, "texto": 8000, "cambio": 240}.items()):
            raise ValueError("Redacción fuera de los límites.")
        return
    personas = pedido["entrada"]["personas"]
    ids = [fila["i"] for fila in salida["r"]]
    if sorted(ids) != list(range(len(personas))):
        raise ValueError("Se espera una respuesta por persona del lote.")
    if tipo == "encuesta":
        if any(not all(type(n) is int and 1 <= n <= 7 for n in fila["p"])
               or len(fila["p"]) != len(metodo.PREGUNTAS) for fila in salida["r"]):
            raise ValueError("Notas fuera de los límites.")
    elif any(not fila["f"].strip() or len(fila["f"]) > 160 for fila in salida["r"]):
        raise ValueError("Voces fuera de los límites.")
