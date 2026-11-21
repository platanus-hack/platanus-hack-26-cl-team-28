#!/usr/bin/env python3
"""Descarga la Encuesta CEP N° 96, abril-mayo 2026 (Centro de Estudios Públicos, Chile).

Uso:
    uv run python -I scripts/descargar_cep.py data/cep96

Baja la base de datos, la convierte a Parquet y baja el diccionario de variables, el
manual de usuario y el cuestionario. Es reejecutable: no repite lo ya descargado.

La CEP mide lo que ni el censo ni Casen traen: posición política, identificación con
partidos, evaluación del gobierno y confianza en las instituciones. Son 1.466 entrevistas
presenciales a mayores de 18 años, representativas del país.
"""

import hashlib
import json
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

BASE = "https://static.cepchile.cl/uploads/cepchile/2026/06/"
PAGINA = "https://www.cepchile.cl/encuesta/encuesta-cep-n-96-abril-mayo-2026/"
CABECERAS = {"User-Agent": "Mozilla/5.0 (descarga-cep96)"}

ARCHIVOS = [
    (BASE + "17-215609_gn0q_bases-96-2026.zip", "bases-96-2026.zip"),
    (BASE + "17-215424_04t2_diccionario_base_96.xlsx", "docs/diccionario_base_96.xlsx"),
    (BASE + "17-215501_52rp_Manual-de-usuario-CEP-96.pdf", "docs/Manual-de-usuario-CEP-96.pdf"),
    (BASE + "17-215342_pbk7_Cuestionario-CEP96.pdf", "docs/Cuestionario-CEP96.pdf"),
]
# Formatos que pandas lee sin dependencias nuevas, en orden de preferencia.
LECTORES = {".dta": lambda ruta: pd.read_stata(ruta, convert_categoricals=False), ".csv": pd.read_csv}


def descargar(url, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_name(destino.name + ".parcial")
    h, total = hashlib.md5(), 0
    pedido = urllib.request.Request(url, headers=CABECERAS)
    with urllib.request.urlopen(pedido, timeout=600) as r, open(parcial, "wb") as f:
        esperado = r.headers.get("Content-Length")
        for bloque in iter(lambda: r.read(1 << 20), b""):
            f.write(bloque)
            h.update(bloque)
            total += len(bloque)
    if esperado is not None and int(esperado) != total:
        parcial.unlink()
        raise RuntimeError(f"descarga incompleta de {url}: {total} de {esperado} bytes")
    parcial.replace(destino)
    return total, h.hexdigest()


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    raiz = Path(sys.argv[1])
    raiz.mkdir(parents=True, exist_ok=True)
    ruta_manifiesto = raiz / "MANIFEST.json"
    previos = {e["url"]: e for e in json.loads(ruta_manifiesto.read_text())["archivos"]} if ruta_manifiesto.exists() else {}
    parquet = raiz / "cep96.parquet"

    entradas = []
    for url, nombre in ARCHIVOS:
        destino = raiz / nombre
        previo = previos.get(url)
        if previo and destino.is_file() and destino.stat().st_size == previo["bytes"]:
            print(f"ok       {nombre}")
            entradas.append(previo)
            continue
        print(f"bajando  {nombre} ...", flush=True)
        tam, md5 = descargar(url, destino)
        entradas.append(
            {"url": url, "archivo": nombre, "bytes": tam, "md5": md5,
             "descargado_en": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        )

    if not parquet.exists():
        print("convirtiendo a Parquet ...", flush=True)
        with tempfile.TemporaryDirectory(dir=raiz, prefix=".extraccion-") as tmp:
            with zipfile.ZipFile(raiz / "bases-96-2026.zip") as z:
                print("  el zip trae: " + ", ".join(z.namelist()))
                z.extractall(tmp)
            for extension, leer in LECTORES.items():
                candidatos = sorted(Path(tmp).rglob(f"*{extension}"))
                if candidatos:
                    base = leer(candidatos[0])
                    break
            else:
                sys.exit("ERROR: el zip no trae la base en Stata (.dta) ni en CSV")
        base.columns = [c.lower() for c in base.columns]
        base.to_parquet(parquet, index=False)
        print(f"  {len(base):,} entrevistas, {base.shape[1]} variables, desde {candidatos[0].name}")

    ruta_manifiesto.write_text(
        json.dumps(
            {
                "fuente": "Centro de Estudios Públicos, Encuesta CEP N° 96, abril-mayo 2026",
                "pagina": PAGINA,
                "nota": "La base se convirtió a cep96.parquet con los nombres de variable en minúsculas; el zip original se conserva.",
                "archivos": entradas,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(f"Listo. Manifiesto: {ruta_manifiesto}")


if __name__ == "__main__":
    main()
