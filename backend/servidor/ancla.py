"""El ancla nacional: un pronóstico directo del total, que los agentes reparten entre personas.

Medido contra 120 preguntas de encuestas reales (data/pruebas/realidad_1000/INFORME.md): los
agentes de Haiku ordenan bien a las personas y a los grupos, pero el porcentaje nacional que
suman queda a unos 15 puntos de la encuesta, lo mismo que responder siempre 60 %. Un modelo
grande, preguntado una sola vez como analista, queda a unos 8 o 9. Aquí se juntan las dos cosas:

1. `pronosticar` pide ese total una vez por propuesta (una llamada, en paralelo con los lotes).
2. `Reparto` decide la postura de cada agente para que el total de la corrida siga al pronóstico
   sin cambiar el orden entre personas: quedan a favor quienes más alto puntuaron, en contra
   quienes más bajo, y al medio lo que el pronóstico deja sin postura.

Las respuestas llegan por lotes y se muestran apenas llegan, así que los cortes se recalculan
con todo lo recibido hasta ese momento y se aplican solo a quienes llegan: nadie cambia de
postura después de aparecer en pantalla. Cada lote corrige además una parte de lo que el total
lleva desviado (`CORRECCION`), y el total final queda a menos de 1 punto del pronóstico.

`ANCLA` en el entorno elige el modelo del pronóstico (`opus` por defecto; `haiku` o `sonnet`
sirven; vacío, `no` o `0` lo apaga y el sitio vuelve a contar las notas tal como salen).
"""

import bisect
import hashlib
import json
import os
import threading
from pathlib import Path

SISTEMA = (
    "Eres analista de opinión pública en Chile. Te entregan una pregunta de encuesta a población adulta "
    "general. Estima qué porcentaje respondería «de acuerdo» y qué porcentaje «en desacuerdo» (el resto no "
    "sabe o no responde). Entrega dos enteros de 0 a 100."
)
ESQUEMA = {"type": "object", "properties": {"acuerdo": {"type": "integer"}, "desacuerdo": {"type": "integer"}},
           "required": ["acuerdo", "desacuerdo"], "additionalProperties": False}
# Lo que se le entrega de la propuesta a quien pronostica: un documento ya viene resumido.
LARGO = 6000
# Cuánto se espera el pronóstico antes de mostrar las primeras respuestas sin él.
ESPERA = 12.0


def modelo() -> str:
    """El modelo del pronóstico, o vacío si el ancla está apagada."""
    valor = os.environ.get("ANCLA", "opus").strip().lower()
    return "" if valor in ("", "no", "0", "off") else valor


def limpiar(datos: dict) -> tuple[float, float] | None:
    """(% de acuerdo, % en desacuerdo) de lo que devolvió el modelo, o None si no sirve."""
    try:
        a, d = float(datos["acuerdo"]), float(datos["desacuerdo"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (0 <= a <= 100 and 0 <= d <= 100) or a + d <= 0:
        return None
    if a + d > 100:
        a, d = 100 * a / (a + d), 100 * d / (a + d)
    return a, d


class Pronosticos:
    """Los pronósticos ya pedidos, por propuesta y modelo: repetir una pregunta da el mismo total."""

    def __init__(self, carpeta: Path):
        self._archivo = carpeta / "anclas.jsonl"
        self._datos: dict[tuple[str, str], tuple[float, float]] = {}
        self._cerrojo = threading.Lock()
        if self._archivo.exists():
            for linea in self._archivo.read_text(encoding="utf-8").splitlines():
                try:
                    f = json.loads(linea)
                    self._datos[(f["p"], f["m"])] = (float(f["a"]), float(f["d"]))
                except (ValueError, KeyError, TypeError):
                    continue

    def buscar(self, huella: str, modelo: str) -> tuple[float, float] | None:
        return self._datos.get((huella, modelo))

    def guardar(self, huella: str, modelo: str, valor: tuple[float, float]) -> None:
        with self._cerrojo:
            self._datos[(huella, modelo)] = valor
            try:
                with open(self._archivo, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"p": huella, "m": modelo, "a": valor[0], "d": valor[1]}) + "\n")
            except OSError:
                pass  # es un ahorro, no un requisito


def puntaje(agente_id: str, notas: list[int]) -> float:
    """Qué tan a favor está la persona, para ordenarla entre las demás: manda la primera nota
    (apoyo); justicia y efectividad, que la acompañan, desempatan; y un sorteo fijo por persona
    decide entre quienes respondieron exactamente lo mismo."""
    extra = sum(notas[k] for k in (1, 3) if k < len(notas))
    azar = int(hashlib.sha256(agente_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return notas[0] + 0.02 * extra + 0.001 * azar


# Cuánto de lo que falta o sobra para calzar con el pronóstico se corrige en cada lote. Con 0 los cortes
# salen solo de lo visto y el total se desvía (1 punto con 1.000 agentes, 2,3 con 200); con 1 cada lote
# recibe su cuota exacta y se pierden las diferencias entre lotes, que van por región. Con 0,2 el total
# queda a 0,2 puntos del pronóstico con 1.000 agentes y a 1 con 200, y 94 % de las personas quedan donde
# las dejaría el reparto hecho con todas las respuestas a la vista.
CORRECCION = 0.2


class Reparto:
    """Reparte el total pronosticado entre los agentes de un caso, a medida que responden."""

    def __init__(self, acuerdo: float, desacuerdo: float):
        self.acuerdo, self.desacuerdo = acuerdo, desacuerdo
        self._puntajes: list[float] = []
        self._favor = self._contra = 0
        self._cerrojo = threading.Lock()

    def repartir(self, lote: list[tuple[str, list[int]]]) -> list[int]:
        """Las notas de apoyo (1 a 7) de un lote recién llegado, en su orden.

        Suma sus puntajes a lo visto, saca los cortes que dejan a favor y en contra los porcentajes
        del pronóstico entre todos los vistos, y cuenta cuántos del lote pasan cada corte. A esa
        cuenta le corrige una parte de lo que el total acumulado se ha desviado. Quedan a favor los
        que más alto puntúan del lote y en contra los que más bajo; el resto, sin postura. A quien ya
        estaba del lado que le toca no se le cambia la nota; a los demás se les mueve lo mínimo."""
        if not lote:
            return []
        propios = [puntaje(agente_id, notas) for agente_id, notas in lote]
        with self._cerrojo:
            for p in propios:
                bisect.insort(self._puntajes, p)
            n = len(self._puntajes)
            favor_total, contra_total = round(n * self.acuerdo / 100), round(n * self.desacuerdo / 100)
            corte_favor = self._puntajes[n - favor_total] if favor_total > 0 else float("inf")
            corte_contra = self._puntajes[contra_total - 1] if contra_total > 0 else float("-inf")
            sobre = sum(p >= corte_favor for p in propios)
            favor = max(0, min(len(lote), round(sobre + CORRECCION * (favor_total - self._favor - sobre))))
            bajo = sum(p <= corte_contra for p in propios)
            contra = max(0, min(len(lote) - favor, round(bajo + CORRECCION * (contra_total - self._contra - bajo))))
            self._favor += favor
            self._contra += contra
        de_mayor_a_menor = sorted(range(len(lote)), key=lambda k: -propios[k])
        finales = [4] * len(lote)
        for k in de_mayor_a_menor[:favor]:
            finales[k] = max(5, lote[k][1][0])
        for k in de_mayor_a_menor[len(lote) - contra:] if contra else []:
            finales[k] = min(3, lote[k][1][0])
        return finales
