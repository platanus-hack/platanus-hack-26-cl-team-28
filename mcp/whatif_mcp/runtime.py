"""Configuración del servicio aislado y puntos de integración con una web local."""

import os
import threading
import time
from pathlib import Path

from servidor import limites
from servidor.historial import Historial
from servidor.poblacion import elegir_poblacion

LETRAS = "ABCDEFGH"
MAXIMO_PEDIDO = 768 * 1024
LARGO_PROPUESTA = 8000
LARGO_DOCUMENTO = 10_500
MAXIMO_ITERACIONES = 3
MAXIMO_MUESTRA = min(limites.entero("MAXIMO_MUESTRA", 10000), max(1, limites.entero("WHATIF_MCP_MAX_MUESTRA", 300)))
MAXIMO_RESPUESTAS = min(limites.RESPUESTAS_POR_CORRIDA, MAXIMO_MUESTRA * 3)


class RuntimeAislado:
    """Solo el MCP lee este historial. La web tiene su propio proceso y sus propios archivos."""

    HISTORIAL_OCULTO = True

    def __init__(self, carpeta: Path):
        self.LOTE = max(1, min(10, limites.entero("WHATIF_MCP_LOTE", 10)))
        self.CONCURRENCIA = 1
        self.POBLACION = elegir_poblacion()
        self.HISTORIAL = Historial(carpeta)
        self.CORRIDAS = {}
        self.ORIGEN = {}
        self.CERROJO_CORRIDAS = threading.Lock()

    @classmethod
    def desde_entorno(cls):
        carpeta = Path(os.environ.get("WHATIF_MCP_DATA", "~/.local/state/whatif-mcp")).expanduser().resolve()
        carpeta.mkdir(mode=0o700, parents=True, exist_ok=True)
        return cls(carpeta)

    def sacar_muestra(self, filtros, tamano):
        return self.POBLACION.muestra(filtros, tamano)

    def olvidar_corridas(self):
        with self.CERROJO_CORRIDAS:
            terminadas = sorted((c for c in self.CORRIDAS.values() if c.guardada.is_set()), key=lambda c: c.fin)
            ahora = time.time()
            for k, corrida in enumerate(terminadas):
                if ahora - corrida.fin > 180 or k < len(terminadas) - limites.CORRIDAS_RECORDADAS:
                    self.CORRIDAS.pop(corrida.id)
                    self.ORIGEN.pop(corrida.id, None)

    def respuestas_pendientes(self):
        activas = [c for c in self.CORRIDAS.values() if not c.terminada and not c.cancelada]
        return sum(len(c.agentes) * (len(c.casos) + c.iteraciones) for c in activas)
