"""El historial de simulaciones: qué se preguntó, cuándo y qué respondieron los agentes.

Cada corrida que termina con al menos una respuesta deja una línea en
`data/historial/corridas.jsonl` con su resumen: la propuesta de cada variante y cuántos quedaron
a favor, en contra y sin decidir en la primera pregunta.

Aparte, en `data/historial/vistas/<id>.json.gz` queda todo lo que hace falta para volver a ver
la corrida en el mapa: la muestra con que se hizo, los filtros de la interfaz y los eventos que
publicó (las respuestas de cada agente, las frases, las variantes que escribió el agente). Se
guarda la muestra entera y no solo sus filtros porque la tabla de agentes cambia y el mismo
sorteo dejaría de dar a las mismas personas. Solo se conservan las vistas de las últimas
corridas. Nada de esto se versiona.
"""

import gzip
import json
import re
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
#: Las corridas que se pueden volver a ver: cada vista pesa entre 100 KB y 1 MB comprimida.
VISTAS_GUARDADAS = 200
#: Los identificadores de corrida (`uuid4().hex[:12]`): lo único que se acepta como nombre de archivo.
IDENTIFICADOR = re.compile(r"[0-9a-f]{12}")
#: Los filtros de la interfaz se guardan tal cual llegan; más largos que esto no son filtros.
LARGO_FILTROS = 4000


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


def vista_de(corrida, muestra, filtros=None) -> bytes:
    """Lo que la interfaz necesita para volver a mostrar una corrida, ya escrito en JSON:
    la muestra como la entrega `/api/muestra`, los agentes de ella que se consultaron, los
    filtros con que la interfaz la pidió y los eventos en el orden en que salieron."""
    if not isinstance(filtros, dict) or len(json.dumps(filtros)) > LARGO_FILTROS:
        filtros = None
    resto = json.dumps({
        "agentes": [a.indice for a in corrida.agentes],
        "filtros": filtros,
        "eventos": [[tipo, datos] for tipo, datos in list(corrida.eventos)],
    }, ensure_ascii=False).encode()
    # La muestra ya está escrita (`Muestra.cuerpo`): se pega tal cual en vez de volver a armarla.
    return b'{"muestra": ' + muestra.cuerpo() + b", " + resto[1:]


class Historial:
    """Las corridas terminadas, en un archivo al que solo se le agregan líneas."""

    def __init__(self, carpeta: Path = CARPETA):
        self._archivo = carpeta / "corridas.jsonl"
        self._vistas = carpeta / "vistas"
        self._entradas: list[dict] = []
        self._cerrojo = threading.Lock()
        #: Las corridas que tienen vista guardada, de la más antigua a la más nueva.
        self._con_vista: list[str] = []
        if self._vistas.is_dir():
            archivos = sorted(self._vistas.glob("*.json.gz"), key=lambda a: a.stat().st_mtime)
            self._con_vista = [a.name.removesuffix(".json.gz") for a in archivos]
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
        """De la más nueva a la más antigua. `vista` dice si la corrida se puede volver a ver."""
        with self._cerrojo:
            con_vista = set(self._con_vista)
            return [{**entrada, "vista": entrada.get("id") in con_vista} for entrada in self._entradas[-cuantas:][::-1]]

    def guardar_vista(self, identificador: str, vista: bytes) -> None:
        """Deja la vista comprimida y bota las más antiguas que ya no caben."""
        if not IDENTIFICADOR.fullmatch(identificador):
            raise ValueError(f"Identificador de corrida inesperado: {identificador!r}")
        self._vistas.mkdir(parents=True, exist_ok=True)
        (self._vistas / f"{identificador}.json.gz").write_bytes(gzip.compress(vista, compresslevel=6))
        with self._cerrojo:
            self._con_vista = [i for i in self._con_vista if i != identificador] + [identificador]
            sobran, self._con_vista = self._con_vista[:-VISTAS_GUARDADAS], self._con_vista[-VISTAS_GUARDADAS:]
        for viejo in sobran:
            (self._vistas / f"{viejo}.json.gz").unlink(missing_ok=True)

    def vista(self, identificador: str) -> bytes | None:
        """La vista guardada de una corrida, comprimida con gzip. None si no hay."""
        if not IDENTIFICADOR.fullmatch(identificador):
            return None
        try:
            return (self._vistas / f"{identificador}.json.gz").read_bytes()
        except OSError:
            return None

    def guardar_al_terminar(self, corrida, muestra=None, filtros=None) -> None:
        """Corre la simulación y deja su resumen y, si se sabe con qué muestra se hizo, su vista.
        Un problema al guardar no debe botar el hilo de la corrida."""
        try:
            corrida.correr()
        finally:
            try:
                entrada = resumen_de(corrida)
                # Una corrida detenida a medio camino no se vuelve a abrir: solo queda su resumen.
                if entrada and muestra is not None and not corrida.cancelada:
                    try:
                        self.guardar_vista(corrida.id, vista_de(corrida, muestra, filtros))
                    except Exception as error:
                        print(f"No se pudo guardar la vista de la corrida {corrida.id}: {error}", flush=True)
                self.agregar(entrada)
            except Exception as error:
                print(f"No se pudo guardar la corrida {corrida.id} en el historial: {error}", flush=True)
