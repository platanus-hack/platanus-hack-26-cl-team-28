"""El historial de simulaciones: qué se preguntó, cuándo y qué respondieron los agentes.

Cada corrida que termina con al menos una respuesta deja una línea en
`data/historial/corridas.jsonl`. Solo guarda el resumen (la propuesta de cada variante y cuántos
quedaron a favor, en contra y sin decidir en la primera pregunta), no las respuestas de cada
agente: esas están en la caché. El archivo no se versiona.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

CARPETA = Path(__file__).resolve().parents[1] / "data" / "historial"
#: Cuánto texto de cada propuesta se guarda: alcanza para leerla y volver a preguntarla.
LARGO_TEXTO = 4000
#: Las que se entregan de una vez, de la más nueva a la más antigua.
ULTIMAS = 100
#: Las que se guardan en memoria.
RECORDADAS = 2000


def resumen_de(corrida) -> dict | None:
    """Lo que queda de una corrida en el historial. None si nadie alcanzó a responder."""
    casos = []
    for caso in corrida.casos:
        notas = [r.acuerdo for r in list(caso.respuestas.values())]
        if not notas:
            continue
        casos.append({
            "letra": caso.letra,
            "texto": caso.texto.strip()[:LARGO_TEXTO],
            "titulo": caso.titulo or (caso.documento.get("titulo", "") if caso.documento else ""),
            "documento": caso.documento["nombre"] if caso.documento else None,
            # Una variante que escribió el agente a partir de otra, no la persona.
            "iteracion": bool(caso.iteracion),
            "respondidas": len(notas),
            "favor": sum(1 for n in notas if n >= 5),
            "contra": sum(1 for n in notas if n <= 3),
            "indecisa": sum(1 for n in notas if n == 4),
        })
    if not casos:
        return None
    metricas = corrida.metricas()
    return {
        "id": corrida.id,
        "hora": datetime.fromtimestamp(corrida.inicio, timezone.utc).isoformat(timespec="seconds"),
        "agentes": len(corrida.agentes),
        "modelo": corrida.motor.describir().get("modelo", ""),
        "segundos": metricas["segundos"],
        "costo_usd": metricas["costo_usd"],
        # Detenida a medio camino: los porcentajes son de quienes alcanzaron a responder.
        "completa": not corrida.cancelada and all(c["respondidas"] >= len(corrida.agentes) for c in casos),
        "casos": casos,
    }


class Historial:
    """Las corridas terminadas, en un archivo al que solo se le agregan líneas."""

    def __init__(self, carpeta: Path = CARPETA):
        self._archivo = carpeta / "corridas.jsonl"
        self._entradas: list[dict] = []
        self._cerrojo = threading.Lock()
        if self._archivo.exists():
            with open(self._archivo, encoding="utf-8") as f:
                for linea in f:
                    try:
                        entrada = json.loads(linea)
                    except ValueError:
                        continue
                    if isinstance(entrada, dict) and isinstance(entrada.get("casos"), list):
                        self._entradas.append(entrada)
            self._entradas = self._entradas[-RECORDADAS:]

    def agregar(self, entrada: dict | None) -> None:
        if not entrada:
            return
        with self._cerrojo:
            self._entradas.append(entrada)
            del self._entradas[:-RECORDADAS]
            self._archivo.parent.mkdir(parents=True, exist_ok=True)
            with open(self._archivo, "a", encoding="utf-8") as f:
                f.write(json.dumps(entrada, ensure_ascii=False) + "\n")

    def ultimas(self, cuantas: int = ULTIMAS) -> list[dict]:
        """De la más nueva a la más antigua."""
        with self._cerrojo:
            return self._entradas[-cuantas:][::-1]

    def guardar_al_terminar(self, corrida) -> None:
        """Corre la simulación y deja su resumen. Un problema al guardar no debe botar el hilo de la corrida."""
        try:
            corrida.correr()
        finally:
            try:
                self.agregar(resumen_de(corrida))
            except Exception as error:
                print(f"No se pudo guardar la corrida {corrida.id} en el historial: {error}", flush=True)
