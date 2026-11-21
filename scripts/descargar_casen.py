#!/usr/bin/env python3
"""Descarga la Encuesta Casen 2024 (Ministerio de Desarrollo Social y Familia, Chile).

Uso:
    uv run python -I scripts/descargar_casen.py data/casen2024

Baja la base de datos (Stata) desde el portal de datos del ministerio, la convierte
a Parquet junto con la identificación de provincia y comuna, y baja el libro de
códigos y la documentación. Es reejecutable: no repite lo ya descargado.
"""

import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

CKAN = "https://bid-ckan.ministeriodesarrollosocial.gob.cl/dataset/105286d9-10a8-410a-b060-a335f3168a46/resource/"
DOCS = "https://observatorio.ministeriodesarrollosocial.gob.cl/storage/docs/casen/2024/"
CABECERAS = {"User-Agent": "Mozilla/5.0 (descarga-casen2024)"}

ARCHIVOS = [
    (CKAN + "eb715dc7-76ee-4857-af52-8b2e24991013/download/casen_2024stata.zip", "casen_2024stata.zip"),
    (CKAN + "8a8136a7-a842-47fc-8c2f-50806131645a/download/casen_2024_provincia_comuna.dta", "casen_2024_provincia_comuna.dta"),
    (DOCS + "Libro_de_codigos_Casen_2024.xlsx", "docs/Libro_de_codigos_Casen_2024.xlsx"),
    (DOCS + "Cuestionario_Casen_2024.pdf", "docs/Cuestionario_Casen_2024.pdf"),
    (DOCS + "Nota_uso_bases_de_datos_Casen_2024.pdf", "docs/Nota_uso_bases_de_datos_Casen_2024.pdf"),
    (DOCS + "Ficha_tecnica_Casen_2024.pdf", "docs/Ficha_tecnica_Casen_2024.pdf"),
    (DOCS + "Manual_para_la_Investigacion_Casen_2024.pdf", "docs/Manual_para_la_Investigacion_Casen_2024.pdf"),
    (DOCS + "Diseno_Muestral_Casen_2024.pdf", "docs/Diseno_Muestral_Casen_2024.pdf"),
]


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
    parquet = raiz / "casen_2024.parquet"

    entradas = []
    for url, nombre in ARCHIVOS:
        destino = raiz / nombre
        es_base = not nombre.startswith("docs/")
        previo = previos.get(url)
        # Los archivos de la base se borran tras convertirlos: basta con que exista el Parquet.
        if previo and (parquet.exists() if es_base else destino.is_file() and destino.stat().st_size == previo["bytes"]):
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
            with zipfile.ZipFile(raiz / "casen_2024stata.zip") as z:
                z.extractall(tmp)
            dta = sorted(Path(tmp).rglob("*.dta"))
            if len(dta) != 1:
                sys.exit(f"ERROR: se esperaba un .dta en el zip y hay {len(dta)}")
            base = pd.read_stata(dta[0], convert_categoricals=False)
        geo = pd.read_stata(raiz / "casen_2024_provincia_comuna.dta", convert_categoricals=False)
        llaves = [c for c in ("folio", "id_persona") if c in geo.columns]
        nuevas = llaves + [c for c in geo.columns if c not in base.columns]
        union = base.merge(geo[nuevas], on=llaves, how="left", validate="one_to_one")
        union.to_parquet(parquet, index=False)
        (raiz / "casen_2024stata.zip").unlink()
        (raiz / "casen_2024_provincia_comuna.dta").unlink()
        print(f"  {len(union):,} personas, {union.shape[1]} variables; columnas territoriales añadidas: {nuevas[len(llaves):]}")

    ruta_manifiesto.write_text(
        json.dumps(
            {
                "fuente": "Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024",
                "nota": "La base Stata y la identificación comunal se unieron en casen_2024.parquet; los originales no se conservan.",
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
