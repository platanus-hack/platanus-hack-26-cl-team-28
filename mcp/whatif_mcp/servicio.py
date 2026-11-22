"""Admisión y consulta de corridas MCP."""

import gzip
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

from servidor import limites, metodo
from servidor.corridas import Caso, Corrida
from servidor.documentos import nombre_limpio
from servidor.historial import RECORDADAS
from servidor.limites import Cola, Cupo, Ocupado, Reparto, Tasa, entero

from .motor import MotorCliente, SinCache
from .runtime import LETRAS, MAXIMO_RESPUESTAS

ID = re.compile(r"[a-f0-9]{12}")
LIMITE_RECIBOS = 2048
VIDA_RECIBOS = 3600
MAXIMO_ACTIVAS_MCP = max(1, entero("WHATIF_MCP_CORRIDAS", 4))
MAXIMO_MCP_POR_DIRECCION = max(1, entero("WHATIF_MCP_CORRIDAS_POR_IP", 2))
REPARTO_MCP = Reparto(entero("WHATIF_MCP_LOTES_SIMULTANEOS", 32))


class CorridaMCP(Corrida):
    def __init__(self, runtime, motor, agentes, casos, iteraciones):
        self.runtime = runtime
        super().__init__(motor, SinCache(), agentes, casos, iteraciones, self.runtime.LOTE, self.runtime.CONCURRENCIA, LETRAS)
        self.guardada = threading.Event()

    def _preguntar(self, grupo, numero):
        # Los lotes que esperan al cliente tienen su propia capacidad. La web conserva sus hilos.
        self._grupo = Cola(REPARTO_MCP, self.id)
        return super()._preguntar(self._grupo, numero)

    def correr(self):
        try:
            super().correr()
        finally:
            if self.motor.vencido:
                self.cancelada = True
            REPARTO_MCP.descartar(self.id)
            self.motor.cerrar()

    def ejecutar(self, muestra, filtros):
        try:
            self.runtime.HISTORIAL.guardar_al_terminar(self, muestra, filtros)
        finally:
            self.guardada.set()
            self.escuchar(False)


@dataclass
class Recibo:
    solicitud: str
    hora: float
    resultado: dict | None = None


class Servicio:
    def __init__(self, runtime):
        self.runtime = runtime
        secreto = os.environ.get("WHATIF_MCP_SECRET")
        if secreto is not None and len(secreto) < 32:
            raise ValueError("WHATIF_MCP_SECRET debe tener al menos 32 caracteres.")
        self.secreto = secreto.encode() if secreto else secrets.token_bytes(32)
        self.recibos: OrderedDict[str, Recibo] = OrderedDict()
        self.cerrojo = threading.Lock()
        self.preparacion = Cupo(8)
        self.tasa = Tasa(12)

    def _firma(self, texto: str) -> str:
        return hmac.digest(self.secreto, texto.encode("utf-8"), "sha256").hex()

    def iniciar(self, origen: str, solicitud: str, pedido: dict) -> dict:
        # El UUID es generado por el cliente con entropía aleatoria. No contiene credenciales de IA.
        recibo_id = self._firma(f"recibo:{solicitud}")
        huella = hashlib.sha256(json.dumps(pedido, sort_keys=True).encode()).hexdigest()
        with self.cerrojo:
            ahora = time.monotonic()
            while self.recibos:
                primero = next(iter(self.recibos.values()))
                if ahora - primero.hora < VIDA_RECIBOS:
                    break
                self.recibos.popitem(last=False)
            previo = self.recibos.get(recibo_id)
            if previo:
                if previo.solicitud != huella:
                    raise ValueError("Esta solicitud ya se usó con otros parámetros.")
                return previo.resultado or {"estado": "preparando", "solicitud": solicitud}
            if len(self.recibos) >= LIMITE_RECIBOS or not self.tasa.permite(origen) or not self.preparacion.tomar():
                raise Ocupado("Hay muchas solicitudes. Intenta de nuevo en unos segundos.")
            recibo = self.recibos[recibo_id] = Recibo(huella, ahora)
        try:
            resultado = self._lanzar(origen, pedido)
            with self.cerrojo:
                recibo.resultado = resultado
            return resultado
        finally:
            with self.cerrojo:
                if recibo.resultado is None:
                    self.recibos.pop(recibo_id, None)
            self.preparacion.soltar()

    def _lanzar(self, origen, pedido):
        filtros = pedido["filtros"]
        tamano = filtros["tamano"]
        crudo = {**filtros["elegidos"], **{k: filtros[k] for k in ("edadMin", "edadMax", "reduccion")}}
        muestra = self.runtime.sacar_muestra(crudo, tamano)
        casos = []
        for k, propuesta in enumerate(pedido["propuestas"]):
            documento = propuesta["documento"]
            if documento:
                documento["nombre"] = nombre_limpio(documento["nombre"])
            casos.append(Caso(str(k), LETRAS[k], propuesta["texto"], documento))
        iteraciones = pedido["iteraciones"]
        pedidas = len(muestra.agentes) * (len(casos) + iteraciones)
        if not muestra.agentes:
            raise ValueError("La muestra quedó vacía.")
        if pedidas > MAXIMO_RESPUESTAS:
            raise ValueError("Reduce el número de agentes o de variantes.")
        motor = MotorCliente()
        registrada = False
        try:
            corrida = CorridaMCP(self.runtime, motor, muestra.agentes, casos, iteraciones)
            self.runtime.olvidar_corridas()
            with self.runtime.CERROJO_CORRIDAS:
                activas = [i for i, c in self.runtime.CORRIDAS.items() if not c.terminada]
                if (self.runtime.respuestas_pendientes() + pedidas > limites.RESPUESTAS_EN_COLA
                        or len(activas) >= limites.CORRIDAS_A_LA_VEZ
                        or sum(isinstance(self.runtime.CORRIDAS[i], CorridaMCP) for i in activas) >= MAXIMO_ACTIVAS_MCP
                        or sum(self.runtime.ORIGEN.get(i) == origen for i in activas)
                        >= min(limites.CORRIDAS_POR_DIRECCION, MAXIMO_MCP_POR_DIRECCION)):
                    raise Ocupado("Hay muchas simulaciones en curso. Intenta de nuevo en un minuto.")
                self.runtime.CORRIDAS[corrida.id] = corrida
                self.runtime.ORIGEN[corrida.id] = origen
                # El agente consulta el progreso con llamadas breves, sin mantener un SSE de la web abierto.
                corrida.escuchar(True)
                hilo = threading.Thread(target=corrida.ejecutar, args=(muestra, filtros), daemon=True)
                try:
                    hilo.start()
                except RuntimeError:
                    self.runtime.CORRIDAS.pop(corrida.id)
                    self.runtime.ORIGEN.pop(corrida.id)
                    raise
                registrada = True
            return {
                "id": corrida.id,
                "acceso": self._firma(f"corrida:{corrida.id}"),
                "estado": "en_curso",
                "agentes": len(muestra.agentes),
                "variantes": len(pedido["propuestas"]),
                "iteraciones": iteraciones,
            }
        finally:
            if not registrada:
                motor.cerrar()

    def _autorizar(self, id: str, acceso: str) -> None:
        if not ID.fullmatch(id) or not hmac.compare_digest(self._firma(f"corrida:{id}").encode(), acceso.encode()):
            raise ValueError("El identificador o el acceso de la corrida no es válido.")

    def estado_corrida(self, id: str, acceso: str) -> dict:
        self._autorizar(id, acceso)
        with self.runtime.CERROJO_CORRIDAS:
            corrida = self.runtime.CORRIDAS.get(id)
        if isinstance(corrida, CorridaMCP) and not corrida.guardada.is_set():
            eventos = corrida.esperar(0, espera=0)
            avance = {}
            for tipo, datos in eventos:
                if tipo == "respuestas":
                    avance.setdefault(datos["caso"], set()).update(fila[0] for fila in datos["r"])
            return {"id": id, "estado": "guardando" if corrida.terminada else "en_curso",
                    "agentes": len(corrida.agentes), "respondidas_por_variante": {k: len(v) for k, v in avance.items()}}
        entrada = next((e for e in self.runtime.HISTORIAL.ultimas(RECORDADAS) if e["id"] == id), None)
        if entrada:
            vista = self.runtime.HISTORIAL.vista(id) if entrada["vista"] else None
            eventos = json.loads(gzip.decompress(vista))["eventos"] if vista else []
            if not eventos and corrida:
                eventos = corrida.esperar(0, espera=0)
            resultado = resultados(entrada, eventos, self.runtime.HISTORIAL_OCULTO)
            if corrida and corrida.cancelada:
                resultado["estado"] = "cancelada"
            return resultado
        if isinstance(corrida, CorridaMCP):
            estado = "cancelada" if corrida.cancelada else "sin_resultados"
            if any(c.respuestas for c in corrida.casos):
                estado = "historial_no_disponible"
            return {"id": id, "estado": estado, "en_historial": False}
        return {"id": id, "estado": "no_disponible", "en_historial": False}

    def cancelar(self, id: str, acceso: str) -> dict:
        self._autorizar(id, acceso)
        with self.runtime.CERROJO_CORRIDAS:
            corrida = self.runtime.CORRIDAS.get(id)
            if isinstance(corrida, CorridaMCP) and not corrida.terminada:
                corrida.cancelada = True
                corrida.motor.cerrar()
                REPARTO_MCP.descartar(id)
                return {"id": id, "estado": "cancelando"}
        return self.estado_corrida(id, acceso)

    def trabajo(self, id: str, acceso: str, entregas: list) -> dict:
        self._autorizar(id, acceso)
        with self.runtime.CERROJO_CORRIDAS:
            corrida = self.runtime.CORRIDAS.get(id)
        if not isinstance(corrida, CorridaMCP) or corrida.terminada:
            return {**self.estado_corrida(id, acceso), "lotes": []}
        trabajo = corrida.motor.trabajo(entregas)
        if corrida.terminada:
            return {**self.estado_corrida(id, acceso), **trabajo}
        return {"id": id, "estado": "en_curso", **trabajo}


def resultados(entrada, eventos, oculto):
    """Resume las mismas notas guardadas en la vista, sin enviar los perfiles ni los mensajes al modelo."""
    preguntas = metodo.PREGUNTAS
    variantes = {}
    notas = {}
    metricas = None
    fallida = False
    for tipo, datos in eventos:
        if tipo == "inicio":
            preguntas = datos["preguntas"]
            variantes.update(enumerate(datos["casos"]))
        elif tipo == "caso":
            variantes[datos["caso"]] = datos
        elif tipo == "respuestas":
            notas.setdefault(datos["caso"], {}).update((fila[0], fila[3]) for fila in datos["r"])
        elif tipo == "fin":
            metricas = datos["metricas"]
        elif tipo == "falla":
            fallida = True
    por_letra = {c["letra"]: dict(c) for c in entrada["casos"]}
    for numero, caso in variantes.items():
        if caso["letra"] not in por_letra:
            continue
        conteos = [[0] * 7 for _ in preguntas]
        for fila in notas.get(numero, {}).values():
            for k, nota in enumerate(fila):
                conteos[k][nota - 1] += 1
        por_letra[caso["letra"]].update(
            texto=caso["texto"], resultados_encuesta=[
                {"pregunta": pregunta, "conteos_notas_1_a_7": conteo}
                for pregunta, conteo in zip(preguntas, conteos)
            ],
        )
    completa = entrada["completa"] and not fallida and (not variantes or len(por_letra) == len(variantes))
    return {
        **entrada,
        "estado": "completa" if completa else "parcial",
        "completa": completa,
        "en_historial": True,
        "visible_en_web": not oculto,
        "metricas": metricas,
        "casos": list(por_letra.values()),
    }
