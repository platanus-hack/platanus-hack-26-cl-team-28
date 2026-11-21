#!/usr/bin/env python3
"""Polígonos de comunas y regiones para el mapa del sitio, desde la cartografía del Censo 2024.

Uso:
    uv run python -I scripts/construir_comunas.py data/censo2024/cartografia ../frontend/src/datos

Lee las capas comunal y de límite urbano de cada región (las baja `descargar_censo.py
--cartografia`), simplifica los polígonos y escribe dos archivos en la carpeta de destino:

- `comunas.json`: {"comunas": {"<código>": {"region", "anillos", "interior", "urbano"}}}.
  `region` es el índice en REGIONES (de norte a sur, como en frontend/src/dominio/catalogos.ts),
  `anillos` son los anillos del polígono en [lon, lat] e `interior` es un punto que con certeza
  cae dentro de la comuna: el respaldo para ubicar a alguien cuando el sorteo de un lugar falla.
  `urbano` son sus zonas urbanas (ciudades y pueblos dentro del límite urbano), cada una con las
  personas que viven en ella: quien vive en zona urbana se dibuja dentro de una de ellas.
- `geografia.json`: reemplaza solo `regions` por la unión de las comunas de cada región, para
  que los límites regionales y comunales calcen. `land` (los países vecinos) no se toca.

Quedan fuera los anillos que el mapa no dibuja: islas oceánicas (al oeste de LON_MINIMA, como
Rapa Nui y Juan Fernández) y el Territorio Chileno Antártico (al sur de LAT_MINIMA). Si una
comuna no tiene ningún anillo dibujable, queda sin anillos y con su `interior`.

Termina con error si no salen todas las comunas de contexto/geo/comunas_centroides.csv o si el
centroide de alguna de ellas queda a más de TOLERANCIA_CENTROIDE de su polígono.

Fuente: INE, Censo de Población y Vivienda 2024, cartografía (capas comunal y de límite
urbano, EPSG:4674, que en la escala del mapa coincide con lon/lat WGS84). Se simplificó la
geometría.
"""

import csv
import json
import sys
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_CENTROIDES = RAIZ / "contexto" / "geo" / "comunas_centroides.csv"

# Mismo orden que REGIONES en servidor/agentes.py y en el frontend (códigos INE, de norte a sur).
CODIGOS_REGION = [15, 1, 2, 3, 4, 5, 13, 6, 7, 16, 8, 9, 14, 10, 11, 12]

#: Tolerancia de la simplificación, en grados (0,012° son algo más de 1 km: unos 2 píxeles con el
#: mapa acercado al máximo). Con 0,004 el archivo de comunas pesa 1 MB; con esta, 375 KB.
TOLERANCIA = 0.012
#: Islas e islotes más chicos que esto (grados², unos 40 km²) no se dibujan, salvo que sean todo lo
#: que tiene la comuna. Son casi todos fiordos de Aysén y Magallanes.
AREA_MINIMA = 0.004
DECIMALES = 3
#: Las zonas urbanas son mucho más chicas que las comunas: se simplifican menos (unos 200 m) y se
#: guardan con un decimal más, para que un pueblo no quede reducido a un triángulo.
TOLERANCIA_URBANA = 0.002
DECIMALES_URBANOS = 4
#: Lo mismo que LON_MINIMA en EscenaEnjambre.ts: al oeste no se dibuja.
LON_MINIMA = -76.5
LAT_MINIMA = -56.5
#: Cuánto puede quedar el centroide del CSV fuera de su polígono (grados, unos 5 km): el CSV es
#: aproximado y algunos centroides caen a 2 o 3 km de su comuna.
TOLERANCIA_CENTROIDE = 0.05


def anillos_de(geojson: dict, decimales: int = DECIMALES) -> list[list[list[float]]]:
    """Los anillos dibujables de un (multi)polígono GeoJSON, redondeados y sin repetir puntos."""
    poligonos = geojson["coordinates"] if geojson["type"] == "MultiPolygon" else [geojson["coordinates"]]
    salida = []
    for poligono in poligonos:
        for anillo in poligono:
            puntos = []
            for lon, lat in anillo:
                punto = [round(lon, decimales), round(lat, decimales)]
                if not puntos or punto != puntos[-1]:
                    puntos.append(punto)
            if len(puntos) > 1 and puntos[0] == puntos[-1]:
                puntos.pop()
            if len(puntos) < 3:
                continue
            if max(p[0] for p in puntos) < LON_MINIMA or max(p[1] for p in puntos) < LAT_MINIMA:
                continue
            salida.append(puntos)
    return salida


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    carpeta, destino = Path(sys.argv[1]), Path(sys.argv[2])
    archivos = sorted(carpeta.glob("*_Comunal.parquet"))
    urbanos = sorted(carpeta.glob("*_Limite_Urbano.parquet"))
    if len(archivos) != len(CODIGOS_REGION) or len(urbanos) != len(CODIGOS_REGION):
        sys.exit(f"ERROR: hay {len(archivos)} capas comunales y {len(urbanos)} de límite urbano en {carpeta}; "
                 f"se esperan {len(CODIGOS_REGION)} de cada una (descargar_censo.py --cartografia)")
    con = duckdb.connect()
    con.execute("install spatial; load spatial")
    origen = f"read_parquet([{', '.join(repr(a.as_posix()) for a in archivos)}])"
    # Los islotes chicos se botan antes de simplificar: así no quedan como triángulos sueltos.
    con.execute(f"""
        create table comunas as
        with partes as (
            select CUT as codigo, COD_REGION as region, unnest(st_dump(SHAPE)).geom as parte from {origen}
        ),
        rankeadas as (
            select *, st_area(parte) as area, row_number() over (partition by codigo order by st_area(parte) desc) as puesto from partes
        )
        select codigo, any_value(region) as region,
               st_union_agg(parte) filter (where area >= {AREA_MINIMA} or puesto = 1) as forma
        from rankeadas group by codigo
    """)
    filas = con.execute(f"""
        select codigo, region,
               st_asgeojson(st_simplifypreservetopology(forma, {TOLERANCIA})),
               st_x(st_pointonsurface(forma)), st_y(st_pointonsurface(forma))
        from comunas order by codigo
    """).fetchall()
    indice_region = {codigo: i for i, codigo in enumerate(CODIGOS_REGION)}
    comunas = {}
    for codigo, region, forma, lon, lat in filas:
        comunas[str(codigo)] = {
            "region": indice_region[region],
            "anillos": anillos_de(json.loads(forma)),
            "interior": [round(lon, 4), round(lat, 4)],
        }

    # Las zonas urbanas de cada comuna, con su población. Las que no tienen a nadie no se guardan.
    origen_urbano = f"read_parquet([{', '.join(repr(a.as_posix()) for a in urbanos)}])"
    personas_urbanas = 0
    for codigo, personas, forma in con.execute(f"""
        select CUT, n_per, st_asgeojson(st_simplifypreservetopology(SHAPE, {TOLERANCIA_URBANA}))
        from {origen_urbano} where n_per > 0 order by CUT, n_per desc
    """).fetchall():
        anillos = anillos_de(json.loads(forma), DECIMALES_URBANOS)
        if str(codigo) in comunas and anillos:
            comunas[str(codigo)].setdefault("urbano", []).append({"personas": int(personas), "anillos": anillos})
            personas_urbanas += int(personas)

    # Las regiones: la unión de sus comunas, simplificada igual.
    regiones: list[list] = [[] for _ in CODIGOS_REGION]
    for region, forma in con.execute(
        f"select region, st_asgeojson(st_simplifypreservetopology(st_union_agg(forma), {TOLERANCIA})) from comunas group by region"
    ).fetchall():
        regiones[indice_region[region]] = anillos_de(json.loads(forma))

    # Validación: están todas las comunas del CSV y su centroide cae en su polígono.
    with open(ARCHIVO_CENTROIDES, encoding="utf-8") as f:
        centroides = list(csv.DictReader(f))
    faltan = [c["comuna"] for c in centroides if c["comuna"] not in comunas]
    if faltan:
        sys.exit(f"ERROR: la cartografía no trae las comunas {', '.join(faltan)}")
    con.execute("create table centroides (codigo integer, lon double, lat double)")
    con.executemany("insert into centroides values (?, ?, ?)", [(int(c["comuna"]), float(c["lon"]), float(c["lat"])) for c in centroides])
    lejos = con.execute(f"""
        select codigo, st_distance(forma, st_point(lon, lat)) as d from centroides join comunas using (codigo)
        where d > {TOLERANCIA_CENTROIDE} order by d desc
    """).fetchall()
    if lejos:
        sys.exit("ERROR: centroides fuera de su comuna: " + ", ".join(f"{c} ({d:.3f}°)" for c, d in lejos))
    sin_anillos = [c for c, v in comunas.items() if not v["anillos"]]

    destino.mkdir(parents=True, exist_ok=True)
    salida = destino / "comunas.json"
    salida.write_text(json.dumps({"comunas": comunas}, separators=(",", ":")) + "\n", encoding="utf-8")
    ruta_geografia = destino / "geografia.json"
    geografia = json.loads(ruta_geografia.read_text(encoding="utf-8"))
    geografia["regions"] = regiones
    ruta_geografia.write_text(json.dumps(geografia, separators=(",", ":")), encoding="utf-8")

    puntos = sum(len(a) for v in comunas.values() for a in v["anillos"])
    zonas = sum(len(v.get("urbano", [])) for v in comunas.values())
    print(f"{len(comunas)} comunas, {puntos:,} vértices, {salida.stat().st_size / 1e3:.0f} KB en {salida}")
    print(f"Zonas urbanas: {zonas:,}, con {personas_urbanas:,} personas")
    print(f"Regiones: {sum(len(a) for r in regiones for a in r):,} vértices, {ruta_geografia.stat().st_size / 1e3:.0f} KB en {ruta_geografia}")
    if sin_anillos:
        print(f"Comunas sin anillos dibujables (se ubican en su punto interior): {', '.join(sin_anillos)}")


if __name__ == "__main__":
    main()
