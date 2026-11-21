#!/usr/bin/env python3
"""Descarga el Censo de Población y Vivienda 2024 (INE, Chile).

Uso:
    uv run python -I scripts/descargar_censo.py data/censo2024 [--cartografia]

Baja microdatos (Parquet), datos agregados, tabulados y documentación desde las
fuentes oficiales del INE, verifica cada archivo y escribe MANIFEST.json.
Con --cartografia baja además la cartografía en GeoParquet de las 16 regiones (unos
800 MB) y deja solo las capas comunal y de límite urbano, que usa scripts/construir_comunas.py.
Es reejecutable: lo ya descargado y verificado no se vuelve a bajar.
Solo usa la biblioteca estándar.
"""

import base64
import hashlib
import json
import shutil
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

NOMBRE_BUCKET = "bktdescargascenso2024"
URL_BUCKET = f"https://storage.googleapis.com/{NOMBRE_BUCKET}/"
URL_LISTADO = (
    f"https://storage.googleapis.com/storage/v1/b/{NOMBRE_BUCKET}/o"
    "?fields=items(name,size,md5Hash,updated),nextPageToken&maxResults=1000"
)
URL_WP = "https://censo2024.ine.gob.cl/wp-content/uploads/"
CABECERAS = {"User-Agent": "Mozilla/5.0 (descarga-censo2024)"}

# (objeto en el bucket, subcarpeta de destino, extraer zip)
DEL_BUCKET = [
    ("viv_hog_per_censo2024.zip", "microdatos", True),
    ("Datos_agregados/Base_manzana_entidad_CPV24.zip", "agregados", True),
    ("Datos_agregados/Base_zona_localidad_CPV24.zip", "agregados", True),
    ("Datos_agregados/Base_urbanos_CPV24.zip", "agregados", True),
    ("Datos_agregados/Base_aldeas_CPV24.zip", "agregados", True),
    ("Datos_agregados/diccionario_variables_glosas_censo2024.xlsx", "docs", False),
    ("Datos_agregados/Manual_uso_cartografia_CPV2024.pdf", "docs", False),
    ("Datos_agregados/N4_Nota_Tecnica_Ajuste direcciones_CPV2024.pdf", "docs", False),
    ("Datos_agregados/N5_Nota Tecnica_indeterminacion_geografica_CPV2024.pdf", "docs", False),
    ("Datos_agregados/N6_Nota_tecnica_Tratamiento_no_respuesta_al_item.pdf", "docs", False),
    ("Datos_agregados/Presentacion_cartografia_base manzana_entidad_CPV2024.pdf", "docs", False),
    ("Datos_agregados/Presentacion_microdatos_CPV2024.pdf", "docs", False),
    ("Datos_agregados/Cs_Pb_Al_Cs_CPV2024.html", "docs", False),
    ("Conmutacion_Laboral_cpv2024.pdf", "docs", False),
    ("261026_doc_conmutacion_laboral_cpv.pdf", "docs", False),
    ("Resultados_CPV2024_Aplicación_DEGURBA.pdf", "docs", False),
    ("Glosario_CPV2024_Dashboard_DEGURBA.pdf", "docs", False),
]

# Cartografía por región: de cada zip se guardan solo las comunas y sus zonas urbanas.
CODIGOS_REGION = range(1, 17)
CARTOGRAFIA = [(f"Cartografia/GEOPARQUET/Cartografía_censo2024_R{r:02d}.zip", "cartografia", True) for r in CODIGOS_REGION]
SOLO_CARTOGRAFIA = ("_Comunal.parquet", "_Limite_Urbano.parquet")

# (ruta bajo wp-content/uploads, subcarpeta de destino)
DEL_PORTAL = [
    ("2025/12/diccionario_variables_censo2024.xlsx", "docs"),
    ("2025/12/manual_uso_microdatos_censo2024.pdf", "docs"),
    ("2025/12/sintesis_resultados_censo2024.pdf", "docs"),
    ("2025/03/Ficha_metodologica_CPV2024.pdf", "docs"),
    ("2025/03/N1_Nota_tecnica_desempenio_operativo_CPV2024.pdf", "docs"),
    ("2025/03/N2_Nota_tecnica_respuesta_modalidades_recoleccion_CPV2024.pdf", "docs"),
    ("2025/04/N3_Nota_Tecnica_Comparacion_Poblacion_CPV2024.pdf", "docs"),
    ("2025/03/Glosario_CPV2024-1.pdf", "docs"),
    ("2025/04/Glosario_fecundidad_migracion_CPV2024.pdf", "docs"),
    ("2025/05/Glosario_viviendas_y_servicios-basicos_CPV2024.pdf", "docs"),
    ("2025/06/Glosario-Caracteristicas-de-la-poblacion_final.pdf", "docs"),
    ("2025/03/Cuestionario-Viviendas-Particulares_CPV2024.pdf", "docs"),
    ("2025/03/Cuestionario-Viviendas-Colectivas-y-Personas-en-Situacion-de-Calle_CPV2024.pdf", "docs"),
    ("2025/03/Manual_Censal_CPV2024.pdf", "docs"),
    ("2025/03/D1_Poblacion-censada-por-sexo-y-edad-en-grupos-quinquenales.xlsx", "tabulados"),
    ("2025/03/D2_Indice-de-envejecimiento-por-sexo.xlsx", "tabulados"),
    ("2025/03/D3_Poblacion-censada-por-tipo-de-operativo.xlsx", "tabulados"),
    ("2025/04/D4_Inmigracion-Internacional.xlsx", "tabulados"),
    ("2025/04/D5_Migracion-interna.xlsx", "tabulados"),
    ("2025/04/D6_Fecundidad.xlsx", "tabulados"),
    ("2025/03/V1_Viviendas-y-hogares-censados.xlsx", "tabulados"),
    ("2025/05/V2_Caracteristicas-vivienda-y-viv-irrecuperables.xlsx", "tabulados"),
    ("2025/05/V3_N-de-dormitorios-hacinamiento-y-viv-con-mas-de-un-hogar.xlsx", "tabulados"),
    ("2025/05/V4_Servicios_basicos_de_la_vivienda.xlsx", "tabulados"),
    ("2025/05/V5_Tipologias-de-viviendas-censadas.xlsx", "tabulados"),
    ("2025/05/H1_Servicios-basicos-hogar-y-tenencia-vivienda.xlsx", "tabulados"),
    ("2025/06/P1-Discapacidad.xlsx", "tabulados"),
    ("2025/06/P2-Pueblos-indigenas.xlsx", "tabulados"),
    ("2025/06/P3_Lenguas-indigenas.xlsx", "tabulados"),
    ("2025/06/P4-Afrodescendencia.xlsx", "tabulados"),
    ("2025/06/P5_Genero.xlsx", "tabulados"),
    ("2025/06/P6_Religion-o-credo.xlsx", "tabulados"),
    ("2025/06/P7_Educacion.xlsx", "tabulados"),
    ("2025/06/P8-Escolaridad-poblacion-inmigrante-internacional.xlsx", "tabulados"),
]


def nfc(texto):
    return unicodedata.normalize("NFC", texto)


def nombre_local(nombre):
    return nfc(nombre.rsplit("/", 1)[-1]).replace(" ", "_")


def abrir(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=CABECERAS), timeout=300)


def listar_bucket():
    """Devuelve {nombre NFC: metadatos} de todos los objetos del bucket."""
    objetos, token = {}, None
    while True:
        url = URL_LISTADO + (f"&pageToken={urllib.parse.quote(token)}" if token else "")
        with abrir(url) as r:
            pagina = json.load(r)
        for item in pagina.get("items", []):
            objetos[nfc(item["name"])] = item
        token = pagina.get("nextPageToken")
        if not token:
            return objetos


def md5_archivo(ruta):
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def descargar(url, destino):
    """Descarga a un temporal y lo mueve al final. Devuelve (bytes, md5)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_name(destino.name + ".parcial")
    h, total = hashlib.md5(), 0
    with abrir(url) as r, open(parcial, "wb") as f:
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


def extraer(ruta_zip, carpeta, solo=None):
    """Extrae en un directorio nuevo y vacío y mueve los archivos a la carpeta.

    Con `solo` (una terminación o una tupla de ellas), guarda únicamente esos archivos."""
    extraidos = []
    with tempfile.TemporaryDirectory(dir=carpeta, prefix=".extraccion-") as tmp:
        with zipfile.ZipFile(ruta_zip) as z:
            z.extractall(tmp)
        for origen in sorted(Path(tmp).rglob("*")):
            if not origen.is_file() or origen.is_symlink():
                continue
            if solo and not nfc(origen.name).endswith(solo):
                continue
            destino = carpeta / nombre_local(origen.name)
            shutil.move(origen, destino)
            extraidos.append(
                {"archivo": destino.name, "bytes": destino.stat().st_size, "md5": md5_archivo(destino)}
            )
    return extraidos


def vigente(previo, carpeta, md5_publicado, solo=None):
    """True si la entrada del manifiesto sigue respaldada por los archivos en disco.

    Con `solo`, además debe haber un archivo extraído con cada terminación: si se pide una capa
    nueva de un zip ya bajado, se vuelve a bajar."""
    if not previo or previo.get("md5_publicado") != md5_publicado:
        return False
    if solo:
        terminaciones = (solo,) if isinstance(solo, str) else solo
        nombres = [a["archivo"] for a in previo.get("extraidos", [])]
        if not all(any(n.endswith(t) for n in nombres) for t in terminaciones):
            return False
    archivos = previo.get("extraidos") or [{"archivo": previo["archivo"], "bytes": previo["bytes"]}]
    return all(
        (carpeta / a["archivo"]).is_file() and (carpeta / a["archivo"]).stat().st_size == a["bytes"]
        for a in archivos
    )


def main():
    argumentos = sys.argv[1:]
    con_cartografia = "--cartografia" in argumentos
    argumentos = [a for a in argumentos if a != "--cartografia"]
    if len(argumentos) != 1:
        sys.exit(__doc__)
    raiz = Path(argumentos[0])
    raiz.mkdir(parents=True, exist_ok=True)
    ruta_manifiesto = raiz / "MANIFEST.json"
    manifiesto = json.loads(ruta_manifiesto.read_text()) if ruta_manifiesto.exists() else {}
    previos = {e["url"]: e for e in manifiesto.get("archivos", [])}

    bucket = listar_bucket()
    tareas = []
    for objeto, sub, extraer_zip in DEL_BUCKET + (CARTOGRAFIA if con_cartografia else []):
        meta = bucket.get(nfc(objeto))
        if meta is None:
            sys.exit(f"ERROR: {objeto} ya no está en el bucket; revisa la lista DEL_BUCKET")
        tareas.append(
            {
                "url": URL_BUCKET + urllib.parse.quote(meta["name"]),
                "archivo": nombre_local(objeto),
                "sub": sub,
                "extraer": extraer_zip,
                "solo": SOLO_CARTOGRAFIA if sub == "cartografia" else None,
                "md5_publicado": base64.b64decode(meta["md5Hash"]).hex(),
                "actualizado_en_origen": meta["updated"],
            }
        )
    for ruta, sub in DEL_PORTAL:
        tareas.append(
            {
                "url": URL_WP + ruta,
                "archivo": nombre_local(ruta),
                "sub": sub,
                "extraer": False,
                "solo": None,
                "md5_publicado": None,
                "actualizado_en_origen": None,
            }
        )

    entradas = []
    for t in tareas:
        carpeta = raiz / t["sub"]
        carpeta.mkdir(parents=True, exist_ok=True)
        previo = previos.get(t["url"])
        if vigente(previo, carpeta, t["md5_publicado"], t["solo"]):
            print(f"ok       {t['sub']}/{t['archivo']}")
            entradas.append(previo)
            continue
        print(f"bajando  {t['sub']}/{t['archivo']} ...", flush=True)
        destino = carpeta / t["archivo"]
        tam, md5 = descargar(t["url"], destino)
        if t["md5_publicado"] and md5 != t["md5_publicado"]:
            destino.unlink()
            sys.exit(f"ERROR: md5 de {t['archivo']} no coincide con el publicado")
        entrada = {
            "url": t["url"],
            "carpeta": t["sub"],
            "archivo": t["archivo"],
            "bytes": tam,
            "md5": md5,
            "md5_publicado": t["md5_publicado"],
            "actualizado_en_origen": t["actualizado_en_origen"],
            "descargado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        if t["extraer"]:
            entrada["extraidos"] = extraer(destino, carpeta, t["solo"])
            destino.unlink()
        entradas.append(entrada)
        # Se guarda tras cada archivo para poder retomar una descarga interrumpida.
        ruta_manifiesto.write_text(
            json.dumps(_manifiesto(entradas), ensure_ascii=False, indent=2) + "\n"
        )

    ruta_manifiesto.write_text(json.dumps(_manifiesto(entradas), ensure_ascii=False, indent=2) + "\n")
    total = sum(sum(x["bytes"] for x in e.get("extraidos", [e])) for e in entradas)
    print(f"\n{len(entradas)} fuentes, {total / 1e6:.0f} MB en disco. Manifiesto: {ruta_manifiesto}")


def _manifiesto(entradas):
    return {
        "fuente": "Instituto Nacional de Estadísticas (INE), Censo de Población y Vivienda 2024",
        "licencia": "https://www.ine.gob.cl/terminos-de-uso-y-licencia-de-datos-abiertos",
        "nota": "md5_publicado es el hash que informa el bucket del INE; los archivos del portal no publican hash.",
        "archivos": entradas,
    }


if __name__ == "__main__":
    main()
