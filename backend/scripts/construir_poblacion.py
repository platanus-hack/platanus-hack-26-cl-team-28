#!/usr/bin/env python3
"""Construye la población de Chile de 14 años o más: todas las personas del Censo 2024, con Casen y CEP.

Uso:
    uv run python -I scripts/construir_poblacion.py data/censo2024 data/casen2024 data/cep96 data/chile

Hace lo mismo que scripts/construir_muestra.py y scripts/imputar_cep.py, pero con todos los
registros del censo en vez de 1 de cada 100:

1. Toma las 18,5 millones de personas y los 6,6 millones de hogares del censo, completa la
   edad donde viene suprimida y deriva los datos de familia que se ven dentro del hogar.
2. Imputa desde Casen 2024, por emparejamiento estadístico, lo que el censo no pregunta
   (ingresos, previsión, contrato, redes, discriminación, tipo de colegio de los menores...).
3. Imputa a los adultos, desde la Encuesta CEP N° 96, sus opiniones políticas y sociales.
4. Deja fuera a los menores de 14 años. No quedan como personas, pero siguen contando en su
   hogar: cada hogar guarda las edades de sus menores, su tamaño y cuántos tiene bajo 14.

Trabaja región por región para que quepa en memoria. Escribe en la carpeta de salida:
    personas.parquet   una fila por persona de 14 años o más, con lo del censo y lo imputado desde Casen
    hogares.parquet    una fila por hogar (todos), con su vivienda, su composición y lo imputado desde Casen
    actitudes.parquet  una fila por adulto, con lo imputado desde la CEP
    chile.parquet      todo junto: una fila por persona de 14 o más con su hogar, su vivienda y sus opiniones

El identificador de persona se asigna sobre todas las personas del censo, así que no es
correlativo entre las de 14 o más, y no cambia si se mueve la edad mínima.

Las columnas y sus límites son los de la muestra: están en contexto/muestra/README.md y
contexto/muestra/actitudes.md. Las llaves se llaman igual (id_persona_muestra,
id_hogar_muestra) para que los mismos scripts sirvan con la muestra y con la población.
El resultado es reproducible: depende solo de los datos y de la semilla.

Diferencia con la muestra: el ingreso del hogar se empareja por posición relativa dentro de
cada región, y aquí "los hogares de la región" son todos, no 1 de cada 100.

La validación contra el censo, Casen y la CEP la hace scripts/validar_poblacion.py.
"""

import shutil
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imputar_cep as cep_  # noqa: E402
from construir_muestra import SEMILLA, completar_edad, derivar_familia, emparejar, imputar_casen, leer_casen  # noqa: E402

# Edad desde la cual una persona es una fila de la población.
EDAD_MINIMA = 14


def leer_region(con, censo, region):
    """Todas las personas de una región y todos sus hogares, con las columnas de la vivienda."""
    P, H, V = (f"'{(censo / 'microdatos' / f'{t}_censo2024.parquet').as_posix()}'" for t in ("personas", "hogares", "viviendas"))
    hogares = con.execute(
        f"""select h.*, v.* exclude (id_vivienda, region, provincia, comuna, comuna_bajo_umbral, area, tipo_operativo)
            from {H} h join {V} v using (id_vivienda)
            where h.tipo_operativo = 2 and h.region = {region}
            order by h.comuna, h.id_vivienda, h.id_hogar"""
    ).df()
    personas = con.execute(
        f"select * from {P} where region = {region} order by comuna, id_vivienda, id_hogar, id_persona"
    ).df()
    return personas, hogares


def a_enteras(df, excepto=()):
    """Las columnas con decimales que solo traen enteros y nulos pasan a entero con nulos."""
    enteras = [c for c in df.columns if c not in excepto and df[c].dtype.kind == "f" and (df[c].dropna() % 1 == 0).all()]
    df[enteras] = df[enteras].astype("Int64")
    return df


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    censo, casen_dir, cep_dir, salida = (Path(a) for a in sys.argv[1:])
    partes = salida / ".partes"
    if partes.exists():
        shutil.rmtree(partes)
    partes.mkdir(parents=True)
    con = duckdb.connect()
    inicio = time.perf_counter()
    callar = lambda texto: None

    P = f"'{(censo / 'microdatos' / 'personas_censo2024.parquet').as_posix()}'"
    edades = con.execute(f"select region, sexo, edad_quinquenal, edad, count(*) as n from {P} where edad >= 0 group by all order by all").df()
    regiones = [r for (r,) in con.execute(f"select distinct region from {P} order by 1").fetchall()]
    print("1. Leyendo Casen ...", flush=True)
    casen, cp, ch = leer_casen(con, casen_dir)

    print("2. Censo y Casen, región por región ...", flush=True)
    n_per = n_hog = 0
    for region in regiones:
        t = time.perf_counter()
        rng = np.random.default_rng([SEMILLA, region])
        per, hog = leer_region(con, censo, region)
        per = completar_edad(per, edades, rng)
        per = derivar_familia(per)
        hog["hk"] = hog["id_vivienda"] * 100 + hog["id_hogar"]
        per, hog, info = imputar_casen(per, hog, casen, cp, ch, rng, avisar=callar)

        hog.insert(0, "id_hogar_muestra", np.arange(n_hog + 1, n_hog + len(hog) + 1))
        per.insert(0, "id_persona_muestra", np.arange(n_per + 1, n_per + len(per) + 1))
        per.insert(1, "id_hogar_muestra", per["hk"].map(hog.set_index("hk")["id_hogar_muestra"]).astype("Int64"))
        n_per, n_hog = n_per + len(per), n_hog + len(hog)
        per = a_enteras(per, excepto=("hijos_origen", "cod_caenes")).drop(columns=["hk"])
        hog = a_enteras(hog).drop(columns=["hk"])
        per.to_parquet(partes / f"personas_{region:02d}.parquet", index=False)
        hog.to_parquet(partes / f"hogares_{region:02d}.parquet", index=False)
        niveles = np.bincount(info["nivel_h"], minlength=5)[1:].tolist()
        print(f"   región {region:>2}: {len(per):>9,} personas, {len(hog):>9,} hogares, R2 {info['r2']:.3f}, niveles de hogar {niveles}, {time.perf_counter() - t:.0f} s", flush=True)
        del per, hog

    print("3. Opiniones de la CEP para los adultos ...", flush=True)
    cep = pd.read_parquet(cep_dir / "cep96.parquet")
    don = cep_.estandarizar_cep(cep)
    todas = f"read_parquet('{(partes / 'personas_*.parquet').as_posix()}', union_by_name = true)"
    conteos = con.execute(f"select decil_ingreso, count(*) from {todas} where edad >= 18 and decil_ingreso is not null group by 1 order by 1").df()
    cortes = cep_.cortes_desde_conteos(don, conteos.set_index("decil_ingreso").iloc[:, 0])
    print(f"   nivel socioeconómico: deciles 1 a {cortes[0]}, {cortes[0] + 1} a {cortes[1]} y {cortes[1] + 1} a 10", flush=True)
    columnas = "id_persona_muestra, sexo, edad, region, cine11, decil_ingreso, sit_fuerza_trabajo, p31_religion"
    n_adultos = 0
    for region in regiones:
        rng = np.random.default_rng([cep_.SEMILLA, region])
        adultos = con.execute(f"select {columnas} from '{(partes / f'personas_{region:02d}.parquet').as_posix()}' where edad >= 18 order by 1").df()
        rec = cep_.estandarizar_muestra(adultos, cortes)
        elegido, nivel = emparejar(rec, don, cep_.NIVELES, "pond", rng)
        imput = pd.DataFrame({"id_persona_muestra": adultos["id_persona_muestra"].to_numpy()})
        for var, col in cep_.DE_LA_CEP.items():
            imput[col] = pd.array(cep[var].to_numpy()[elegido], dtype="Int64")
        imput["nivel_match_cep"] = nivel
        imput["cep_id_donante"] = cep["id_bu"].to_numpy()[elegido]
        imput.to_parquet(partes / f"actitudes_{region:02d}.parquet", index=False)
        n_adultos += len(imput)
    print(f"   {n_adultos:,} adultos", flush=True)

    print("4. Escribiendo los archivos finales ...", flush=True)
    con.execute("set preserve_insertion_order = true")
    opciones = "(format parquet, compression zstd, row_group_size 500000)"
    parte = lambda tabla: f"read_parquet('{(partes / f'{tabla}_*.parquet').as_posix()}', union_by_name = true)"
    destino = lambda tabla: f"'{(salida / f'{tabla}.parquet').as_posix()}'"
    # Composición de cada hogar, contando a todos sus integrantes, también los menores que no quedan como filas.
    composicion = f"""select id_hogar_muestra,
                             list(edad order by edad) filter (where edad < 18) as edades_menores,
                             list(edad order by edad) filter (where edad < 18 and parentesco in (5, 6)) as edades_hijos_jefatura,
                             count(*) filter (where edad < {EDAD_MINIMA}) as menores_de_{EDAD_MINIMA},
                             count(*) filter (where edad >= 65) as mayores_65,
                             count(*) filter (where dependencia_grado in (1, 2, 3)) as dependientes
                      from {parte('personas')} where id_hogar_muestra is not null group by 1"""
    con.execute(f"copy (select h.*, c.* exclude (id_hogar_muestra) from {parte('hogares')} h left join ({composicion}) c using (id_hogar_muestra) order by 1) to {destino('hogares')} {opciones}")
    n_menores = con.execute(f"select count(*) from {parte('personas')} where edad < {EDAD_MINIMA}").fetchall()[0][0]
    con.execute(f"copy (select * from {parte('personas')} where edad >= {EDAD_MINIMA} order by id_persona_muestra) to {destino('personas')} {opciones}")
    con.execute(f"copy (select * from {parte('actitudes')} order by id_persona_muestra) to {destino('actitudes')} {opciones}")
    personas, hogares, actitudes = (f"'{(salida / f'{t}.parquet').as_posix()}'" for t in ("personas", "hogares", "actitudes"))
    # Tabla única: las columnas del hogar que no están ya en la persona, y las opiniones.
    de_persona = {c for (c, *_) in con.execute(f"describe select * from {personas}").fetchall()}
    de_hogar = [c for (c, *_) in con.execute(f"describe select * from {hogares}").fetchall() if c not in de_persona]
    con.execute(
        f"""copy (
              select p.*, h.casen_folio_donante as casen_folio_donante_hogar, {', '.join('h.' + c for c in de_hogar)},
                     a.* exclude (id_persona_muestra)
              from {personas} p
              left join {hogares} h using (id_hogar_muestra)
              left join {actitudes} a using (id_persona_muestra)
              order by p.id_persona_muestra
            ) to '{(salida / 'chile.parquet').as_posix()}' {opciones}"""
    )
    shutil.rmtree(partes)
    for archivo in ("personas", "hogares", "actitudes", "chile"):
        ruta = salida / f"{archivo}.parquet"
        filas, columnas_ = con.execute(f"select count(*) from '{ruta.as_posix()}'").fetchall()[0][0], len(con.execute(f"describe select * from '{ruta.as_posix()}'").fetchall())
        print(f"   {archivo + '.parquet':<18} {filas:>10,} filas  {columnas_:>3} columnas  {ruta.stat().st_size / 1e9:.2f} GB")
    print(f"Listo en {(time.perf_counter() - inicio) / 60:.1f} minutos: {n_per - n_menores:,} personas de {EDAD_MINIMA} años o más y {n_hog:,} hogares en {salida}")
    print(f"Quedaron fuera {n_menores:,} menores de {EDAD_MINIMA} años, que siguen contados en sus hogares.")


if __name__ == "__main__":
    main()
