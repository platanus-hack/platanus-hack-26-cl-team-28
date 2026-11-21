#!/usr/bin/env python3
"""Ejecuta SQL de DuckDB sobre el Censo 2024, con los datos ya expuestos como vistas.

Uso:
    uv run python -I scripts/consulta.py "select region, count(*) from personas group by 1 order by 1"
    uv run python -I scripts/consulta.py --csv "select * from comunas" > comunas.csv
    uv run python -I scripts/consulta.py --todo < consulta.sql

Vistas:
    personas, hogares, viviendas      microdatos (Parquet)
    etiquetas                         tabla, variable, valor, etiqueta, casos
    comunas                           comuna con nombres de provincia y región, población, viviendas, hogares
    territorios                       codigo, nivel (region, provincia, comuna), nombre
    territorios_especificos           códigos de las variables *_esp
    manzana_entidad, zona_localidad,
    urbanos, aldeas                   datos agregados; las celdas suprimidas (*) quedan como NULL
    muestra                           muestra del 1 % en una sola tabla: una fila por persona con los datos de su hogar
    muestra_personas, muestra_hogares la misma muestra separada en personas y hogares (ver contexto/muestra/)
    etiquetas_casen                   columna, variable_casen, valor, etiqueta de las columnas imputadas
    casen                             Encuesta Casen 2024 completa (881 variables; ponderar con expr)
    muestra_actitudes                 actitudes políticas imputadas a los adultos de la muestra (ver contexto/muestra/actitudes.md)
    etiquetas_cep                     columna, variable_cep, valor, etiqueta de las actitudes imputadas
    cep                               Encuesta CEP N° 96, abril-mayo 2026 (1.466 entrevistas; ponderar con pond)
    chile                             población completa en una sola tabla: 18,5 M de personas con su hogar, su vivienda,
                                      lo imputado desde Casen y, los adultos, sus opiniones de la CEP (ver contexto/chile/)
    chile_personas, chile_hogares,
    chile_actitudes                   la misma población separada en personas, hogares y opiniones

Sin --todo se muestran como máximo 200 filas. Con --csv la salida es CSV completo.
"""

import csv
import sys
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data" / "censo2024"
CONTEXTO = RAIZ / "contexto" / "censo2024"


def conectar():
    con = duckdb.connect()
    for t in ("personas", "hogares", "viviendas"):
        ruta = (DATOS / "microdatos" / f"{t}_censo2024.parquet").as_posix()
        con.execute(f"create view {t} as select * from read_parquet('{ruta}')")
    for t in ("personas", "hogares"):
        ruta = RAIZ / "data" / "muestra" / f"{t}.parquet"
        if ruta.exists():
            con.execute(f"create view muestra_{t} as select * from read_parquet('{ruta.as_posix()}')")
    ruta = RAIZ / "data" / "muestra" / "muestra.parquet"
    if ruta.exists():
        con.execute(f"create view muestra as select * from read_parquet('{ruta.as_posix()}')")
    ruta = RAIZ / "contexto" / "muestra" / "etiquetas_casen.csv"
    if ruta.exists():
        con.execute(f"create view etiquetas_casen as select * from read_csv('{ruta.as_posix()}')")
    ruta = RAIZ / "data" / "casen2024" / "casen_2024.parquet"
    if ruta.exists():
        con.execute(f"create view casen as select * from read_parquet('{ruta.as_posix()}')")
    ruta = RAIZ / "data" / "muestra" / "actitudes.parquet"
    if ruta.exists():
        con.execute(f"create view muestra_actitudes as select * from read_parquet('{ruta.as_posix()}')")
    ruta = RAIZ / "contexto" / "muestra" / "etiquetas_cep.csv"
    if ruta.exists():
        con.execute(f"create view etiquetas_cep as select * from read_csv('{ruta.as_posix()}')")
    for vista, archivo in (("chile", "chile"), ("chile_personas", "personas"), ("chile_hogares", "hogares"), ("chile_actitudes", "actitudes")):
        ruta = RAIZ / "data" / "chile" / f"{archivo}.parquet"
        if ruta.exists():
            con.execute(f"create view {vista} as select * from read_parquet('{ruta.as_posix()}')")
    ruta = RAIZ / "data" / "cep96" / "cep96.parquet"
    if ruta.exists():
        con.execute(f"create view cep as select * from read_parquet('{ruta.as_posix()}')")
    for t in ("etiquetas", "comunas", "territorios", "territorios_especificos"):
        con.execute(f"create view {t} as select * from read_csv('{(CONTEXTO / f'{t}.csv').as_posix()}')")
    for t in ("manzana_entidad", "zona_localidad", "urbanos", "aldeas"):
        # Las celdas suprimidas traen '*' y los promedios usan coma decimal: se lee como texto
        # y se convierten los conteos (n_*) y promedios (prom_*); los códigos quedan como texto.
        origen = f"read_csv('{(DATOS / 'agregados' / f'Base_{t}_CPV24.csv').as_posix()}', all_varchar = true)"
        columnas = [c[0] for c in con.execute(f"describe select * from {origen}").fetchall()]
        exprs = []
        for c in columnas:
            if c.startswith("n_") or c in ("CONTENEDOR_COMUNAL", "COD_REGION", "CUT", "AREA_C"):
                exprs.append(f'try_cast("{c}" as bigint) as "{c}"')
            elif c.startswith("prom_"):
                exprs.append(f"""try_cast(replace("{c}", ',', '.') as double) as "{c}\"""")
            else:
                exprs.append(f'"{c}"')
        con.execute(f"create view {t} as select {', '.join(exprs)} from {origen}")
    return con


def main():
    args = sys.argv[1:]
    como_csv = "--csv" in args
    todo = "--todo" in args or como_csv
    sql = " ".join(a for a in args if a not in ("--csv", "--todo")) or sys.stdin.read()
    if not sql.strip() or sql.strip() in ("-h", "--help"):
        sys.exit(__doc__)
    cur = conectar().execute(sql)
    if cur.description is None:
        return
    columnas = [d[0] for d in cur.description]
    filas = cur.fetchall()
    if como_csv:
        w = csv.writer(sys.stdout)
        w.writerow(columnas)
        w.writerows(filas)
        return
    mostradas = filas if todo else filas[:200]
    texto = [["" if v is None else str(v) for v in f] for f in mostradas]
    anchos = [max(len(c), *(len(f[i]) for f in texto)) if texto else len(c) for i, c in enumerate(columnas)]
    print("  ".join(c.ljust(a) for c, a in zip(columnas, anchos)))
    print("  ".join("-" * a for a in anchos))
    for f in texto:
        print("  ".join(v.ljust(a) for v, a in zip(f, anchos)))
    if len(filas) > len(mostradas):
        print(f"... {len(filas) - len(mostradas)} filas más (usa --todo o --csv)")


if __name__ == "__main__":
    main()
