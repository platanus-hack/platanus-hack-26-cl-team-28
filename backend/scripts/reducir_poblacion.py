#!/usr/bin/env python3
"""Reduce la población completa a una tabla de agentes: cada fila representa a varias personas.

Uso:
    uv run python -I scripts/reducir_poblacion.py data/chile data/agentes contexto/chile

Toma data/chile/chile.parquet (15,5 M de personas de 14 años o más) y deja 1 de cada 10 en
data/agentes/, un archivo por región. Esa carpeta sí se versiona: es la tabla que usa el
motor del sitio (servidor/poblacion.py) para filtrar y sacar la muestra.

Cada fila conserva todas las columnas de la persona elegida y agrega a cuántas personas
representa, en tres niveles de reducción anidados:
    representa        todas las filas: 1 agente por cada 10 personas
    representa_100    solo 1 de cada 10 filas: 1 agente por cada 100 personas
    representa_1000   solo 1 de cada 100 filas: 1 agente por cada 1.000 personas
Quien representa a 1.000 es uno de los que representan a 100, y este uno de los de 10. En
cada nivel, la suma de la columna en una región es su población de 14 años o más. El sitio
deja elegir el nivel; para usar uno basta quedarse con las filas donde su columna no es nula.

Cómo se elige hoy, y qué va a cambiar
-------------------------------------
El destino es que cada agente sea el arquetipo de un grupo de personas parecidas, obtenido
por clusterización. Ese proceso todavía no existe. Mientras tanto, `grupos()` arma grupos
de 10 vecinos en un orden simple (comuna, zona, sexo y tramo de edad) y `representantes()`
elige a uno al azar de cada grupo. Cada nivel agrupa a los representantes del anterior.

Cuando exista la clusterización, basta reemplazar `grupos()` por una consulta que devuelva
el mismo par (persona, grupo) con los clusters, y si se quiere `representantes()` por la
elección del arquetipo. Lo demás no cambia: las columnas pasan a traer el tamaño de cada
cluster, y el motor ya sortea la muestra en proporción a ellas.

El resultado es reproducible: depende solo de los datos y de SEMILLA. Escribe además
contexto/chile/agentes.md, que compara la tabla reducida con la población completa.
"""

import sys
import time
from pathlib import Path

import duckdb

SEMILLA = 2024
# De cuántos en cuántos se agrupa en cada paso, y los niveles que resultan: (personas por agente, columna).
RAZON = 10
NIVELES = [(10, "representa"), (100, "representa_100"), (1000, "representa_1000")]
# Lo que se compara entre la tabla reducida y la población completa: (título, columna, condición).
COMPARAR = [
    ("Sexo", "sexo", "true"),
    ("Edad en tramos de cinco años", "edad_quinquenal", "true"),
    ("Zona urbana o rural", "area", "true"),
    ("Nivel educativo", "cine11", "cine11 > 0"),
    ("Situación en la fuerza de trabajo", "sit_fuerza_trabajo", "sit_fuerza_trabajo > 0"),
    ("Decil de ingreso del hogar", "decil_ingreso", "decil_ingreso is not null"),
    ("Previsión de salud", "prevision_salud", "prevision_salud is not null"),
    ("Tipo de colegio de los menores", "dependencia_colegio", "dependencia_colegio is not null"),
    ("Posición política", "posicion_politica", "posicion_politica is not null"),
    ("Evaluación del gobierno", "aprueba_gobierno", "aprueba_gobierno is not null"),
    ("Confianza en el gobierno", "confianza_gobierno", "confianza_gobierno is not null"),
]


def grupos(miembros, paso):
    """Consulta que asigna cada miembro a un grupo: (id, peso, grupo).

    `miembros` entrega (id, comuna, area, sexo, edad_quinquenal, peso): personas en el primer
    paso, y los representantes del nivel anterior en los siguientes.

    Provisorio: grupos de RAZON vecinos en el orden comuna, zona, sexo y tramo de edad. Aquí va
    la clusterización cuando exista."""
    return f"""
        select id, peso,
               (row_number() over (order by comuna, area, sexo, edad_quinquenal, hash(id, {SEMILLA + 10 * paso})) - 1) // {RAZON} as grupo
        from ({miembros})"""


def representantes(consulta_grupos, paso):
    """Consulta que elige a un miembro por grupo: (id, representa), con el peso de todo el grupo.

    Provisorio: uno al azar. Con clusters, aquí se elige el arquetipo (por ejemplo, la persona
    más cercana al centro de su grupo)."""
    return f"""
        select id, representa from (
            select id, sum(peso) over (partition by grupo) as representa,
                   row_number() over (partition by grupo order by hash(id, {SEMILLA + 10 * paso + 1})) as lugar
            from ({consulta_grupos}))
        where lugar = 1"""


def reducir(con, origen, region):
    """Deja en tablas temporales nivel_0, nivel_1 y nivel_2 a los representantes de cada nivel de la región."""
    llaves = f"select id_persona_muestra as id, comuna, area, sexo, edad_quinquenal from {origen} where region = {region}"
    con.execute(f"create or replace temp table llaves as {llaves}")
    miembros = "select *, 1 as peso from llaves"
    for paso in range(len(NIVELES)):
        con.execute(f"create or replace temp table nivel_{paso} as {representantes(grupos(miembros, paso), paso)}")
        miembros = f"select l.*, n.representa as peso from llaves l join nivel_{paso} n using (id)"


def miles(n):
    return f"{int(n):,}".replace(",", ".")


def numero(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def distribucion(con, tabla, columna, condicion, peso):
    filas = con.execute(f"select {columna}, sum({peso}) from {tabla} where {condicion} group by 1").fetchall()
    total = sum(float(n) for _, n in filas)
    return {valor: 100 * float(n) / total for valor, n in filas}


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    chile, salida, contexto = (Path(a) for a in sys.argv[1:4])
    salida.mkdir(parents=True, exist_ok=True)
    for viejo in salida.glob("region_*.parquet"):
        viejo.unlink()
    con = duckdb.connect()
    inicio = time.perf_counter()
    origen = f"read_parquet('{(chile / 'chile.parquet').as_posix()}')"
    regiones = [r for (r,) in con.execute(f"select distinct region from {origen} order by 1").fetchall()]

    print(f"Dejando 1 de cada {RAZON} personas, región por región, con sus niveles de {', '.join(str(n) for n, _ in NIVELES)} ...", flush=True)
    for region in regiones:
        destino = salida / f"region_{region:02d}.parquet"
        reducir(con, origen, region)
        con.execute(
            f"""copy (
                  select p.*, a.representa::integer as representa, b.representa::integer as representa_100, c.representa::integer as representa_1000
                  from {origen} p join nivel_0 a on p.id_persona_muestra = a.id
                  left join nivel_1 b on p.id_persona_muestra = b.id
                  left join nivel_2 c on p.id_persona_muestra = c.id
                  where p.region = {region}
                  order by p.id_persona_muestra
                ) to '{destino.as_posix()}' (format parquet, compression zstd, compression_level 19, row_group_size 100000)"""
        )
        filas, personas, cien, mil = con.execute(f"select count(*), sum(representa), count(representa_100), count(representa_1000) from '{destino.as_posix()}'").fetchall()[0]
        print(f"   región {region:>2}: {filas:>8,} agentes por {personas:>9,} personas; {cien:>7,} de a 100 y {mil:>6,} de a 1.000  ({destino.stat().st_size / 1e6:5.1f} MB)", flush=True)

    agentes = f"read_parquet('{(salida / 'region_*.parquet').as_posix()}')"
    n_agentes, representadas = con.execute(f"select count(*), sum(representa) from {agentes}").fetchall()[0]
    n_personas = con.execute(f"select count(*) from {origen}").fetchall()[0][0]
    peso_total = sum(p.stat().st_size for p in salida.glob("region_*.parquet"))
    assert representadas == n_personas, (representadas, n_personas)
    cuantos = {}
    for personas_por_agente, columna in NIVELES:
        cuantos[columna] = con.execute(f"select count({columna}) from {agentes}").fetchall()[0][0]
        por_region = con.execute(
            f"""select count(*) from (select region, sum({columna}) n from {agentes} group by 1) a
                join (select region, count(*) n from {origen} group by 1) b using (region) where a.n <> b.n"""
        ).fetchall()[0][0]
        assert por_region == 0, f"la suma de `{columna}` no coincide con la población de alguna región"

    filas, peores = [], {columna: 0.0 for _, columna in NIVELES}
    for titulo, columna, condicion in COMPARAR:
        completa = distribucion(con, origen, columna, condicion, "1")
        celdas = []
        for _, peso in NIVELES:
            reducida = distribucion(con, agentes, columna, f"({condicion}) and {peso} is not null", peso)
            dif = max(abs(reducida.get(v, 0) - completa.get(v, 0)) for v in set(completa) | set(reducida))
            peores[peso] = max(peores[peso], dif)
            celdas.append(numero(dif))
        filas.append(f"| {titulo} | {len(completa)} | {' | '.join(celdas)} |")
    peor = peores["representa"]
    comuna = con.execute(
        f"""select max(abs(a.n - b.n)), max(abs(a.n - b.n) / b.n) filter (where b.n >= 5000)
            from (select comuna, sum(representa) n from {agentes} group by 1) a
            join (select comuna, count(*) n from {origen} group by 1) b using (comuna)"""
    ).fetchall()[0]
    sin_agentes = con.execute(f"select count(*) from (select distinct comuna from {origen} except select distinct comuna from {agentes})").fetchall()[0][0]

    contexto.mkdir(parents=True, exist_ok=True)
    (contexto / "agentes.md").write_text(
        "\n".join([
            "# Tabla de agentes",
            "",
            f"`data/agentes/` tiene {miles(n_agentes)} agentes que representan a las {miles(n_personas)} personas de 14 años o más de `data/chile/`: "
            f"1 de cada {RAZON}. Es la tabla que usa el motor del sitio para filtrar y sacar la muestra, y por eso se versiona "
            f"({numero(peso_total / 1e6, 0)} MB, un archivo por región). La escribe `scripts/reducir_poblacion.py`.",
            "",
            "Cada fila es una persona real del censo, con todas sus columnas (las mismas de `data/chile/chile.parquet`), más a cuántas personas "
            "representa en cada nivel de reducción. Los niveles son anidados: quien representa a 1.000 es uno de los que representan a 100.",
            "",
            "| Nivel | Columna | Agentes | Cómo se usa |",
            "|---|---|---|---|",
            *[f"| 1 agente por cada {miles(n)} personas | `{columna}` | {miles(cuantos[columna])} | "
              + ("Todas las filas." if columna == "representa" else f"Las filas donde `{columna}` no es nula.") + " |" for n, columna in NIVELES],
            "",
            "Para una cifra de la población, cada fila se pondera por la columna de su nivel. En el sitio, el nivel se elige en el cajón de filtros («Clusterización»).",
            "",
            "## Cómo se elige a cada agente",
            "",
            f"Hoy es provisorio: dentro de cada región las personas se ordenan por comuna, zona, sexo y tramo de edad, se agrupan de a {RAZON}, "
            "y de cada grupo se elige una al azar; el nivel siguiente hace lo mismo con los elegidos. El destino es que cada agente sea el arquetipo "
            "de un grupo de personas parecidas obtenido por clusterización; cuando ese proceso exista reemplaza a `grupos()` en el script, y las "
            "columnas pasan a traer el tamaño de cada cluster. El motor ya sortea la muestra en proporción a esas columnas, así que no hay que tocarlo.",
            "",
            "## Comparación con la población completa",
            "",
            f"La suma de `representa` es exactamente la población en cada región. Por comuna, la mayor diferencia es de {miles(comuna[0])} personas "
            f"({numero(100 * (comuna[1] or 0), 1)} % en las comunas de 5.000 personas o más); {sin_agentes} comunas quedaron sin ningún agente.",
            "",
            "Diferencia máxima, en puntos porcentuales, entre la población completa y los agentes de cada nivel, ponderados:",
            "",
            "| Dato | Categorías | " + " | ".join(f"1 por cada {miles(n)}" for n, _ in NIVELES) + " |",
            "|---|---|" + "---|" * len(NIVELES),
            *filas,
            "",
            "Lo que entra en el orden de los grupos (comuna, zona, sexo, edad) calza casi exacto; lo demás difiere por el azar de elegir a uno por grupo, "
            "que crece al reducir más: con menos agentes hay menos casos de cada tipo.",
            "",
            "Fuentes: INE, Censo de Población y Vivienda 2024; Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024; Centro de Estudios Públicos, Encuesta CEP N° 96.",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Listo en {time.perf_counter() - inicio:.0f} s: {n_agentes:,} agentes representan a {n_personas:,} personas; {peso_total / 1e6:.0f} MB en {salida}")
    print("Diferencia máxima con la población completa: " + ", ".join(f"{peores[c]:.2f} puntos de a {miles(n)}" for n, c in NIVELES) + f". Informe en {contexto / 'agentes.md'}")


if __name__ == "__main__":
    main()
