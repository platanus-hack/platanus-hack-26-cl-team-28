#!/usr/bin/env python3
"""Reduce la población completa a una tabla de agentes: cada fila representa a un grupo de personas parecidas.

Uso:
    uv run python -I scripts/reducir_poblacion.py data/chile data/agentes contexto/chile

Toma data/chile/chile.parquet (15,5 M de personas de 14 años o más) y deja 1 de cada 10 en
data/agentes/, un archivo por región. Esa carpeta sí se versiona: es la tabla que usa el
motor del sitio (servidor/poblacion.py) para filtrar y sacar la muestra.

Cada fila conserva todas las columnas de la persona elegida y agrega su tipo político
(`tipo_politico`) y a cuántas personas representa, en cuatro niveles de reducción anidados:
    representa         todas las filas: 1 agente por cada 10 personas
    representa_100     1 de cada 10 filas: 1 agente por cada 100 personas
    representa_1000    1 de cada 100 filas: 1 agente por cada 1.000 personas
    representa_10000   1 de cada 1.000 filas: 1 agente por cada 10.000 personas
Quien representa a 1.000 es uno de los que representan a 100, y este uno de los de 10. En
cada nivel, la suma de la columna en una región es su población de 14 años o más. El sitio
deja elegir el nivel; para usar uno basta quedarse con las filas donde su columna no es nula.

Cómo se agrupa
--------------
Lo que más pesa en una opinión es la política (voto, aprobación de los gobiernos, posición,
confianza en el gobierno); la demografía pesa poco (contexto/metodo/influencia.md). Por eso:

1. Tipos políticos. Todas las opiniones de una persona vienen de un mismo entrevistado de la
   Encuesta CEP, y hay 1.466. `tipos_politicos()` los agrupa en TIPOS tipos según los datos de
   POLITICA, y cada persona hereda el tipo de su entrevistado. Los menores de 18, que no tienen
   opiniones, quedan sin tipo.
2. Grupos de 10. En cada nivel, los integrantes (personas en el primero, representantes del
   nivel anterior en los demás) se ordenan según ORDENES y se cortan de a 10. Mientras hay
   gente suficiente, cada grupo es de una comuna y de un tipo político; en los niveles más
   reducidos no alcanza para ambas cosas y se prefiere el tipo político.
3. Representante por equilibrio. `elegir()` recorre los grupos llevando la cuenta de qué
   categorías de EQUILIBRAR van quedando con menos peso del que les corresponde en la región,
   y de cada grupo toma al integrante que mejor lo compensa. Así las distribuciones calzan
   aunque el grupo no sea parejo. No se usa el integrante más típico (el medoide): elige
   siempre a la mayoría de cada grupo y hace desaparecer a las minorías.

El resultado es reproducible: depende solo de los datos y de SEMILLA. Escribe además
contexto/chile/agentes.md, que describe los tipos y compara la tabla con la población completa.
"""

import sys
import time
from pathlib import Path

import duckdb
import numpy as np

SEMILLA = 2024
# De cuántos en cuántos se agrupa en cada paso, y los niveles que resultan: (personas por agente, columna).
RAZON = 10
NIVELES = [(10, "representa"), (100, "representa_100"), (1000, "representa_1000"), (10000, "representa_10000")]

# Los datos con que se arman los tipos políticos y cuánto explica cada uno de las opiniones de la
# CEP (eta² medio, en contexto/metodo/influencia.md): es su peso al medir el parecido.
POLITICA = [
    ("voto_segunda_vuelta_2025", 9.4),
    ("aprueba_gobierno", 8.6),
    ("posicion_politica", 8.0),
    ("confianza_gobierno", 7.5),
    ("aprueba_gobierno_anterior", 7.1),
    ("reducir_gasto_publico", 6.7),
    ("partido", 6.2),
]
TIPOS = 8
EJES = 4
INTENTOS = 12

# Lo que se lee de cada persona para agrupar y equilibrar: nombre y expresión (p es la persona, t su tipo).
DATOS = {
    "comuna": "p.comuna",
    "zona": "p.area",
    "sexo": "p.sexo",
    "edad": "case when p.edad < 18 then 0 when p.edad < 30 then 1 when p.edad < 45 then 2 when p.edad < 60 then 3 else 4 end",
    "tipo": "coalesce(t.tipo, 0)",
    "eje": "coalesce(t.eje, 0)",
    "laboral": "case when p.sit_fuerza_trabajo in (1, 2, 3) then p.sit_fuerza_trabajo else 0 end",
    "educacion": "case when p.cine11 between 8 and 11 then 2 when p.cine11 in (6, 7) then 1 else 0 end",
    "menores": "case when p.menores_de_14 > 0 then 1 else 0 end",
    "quintil": "coalesce(p.quintil_ingreso, 0)",
    "voto": "coalesce(p.voto_segunda_vuelta_2025, -99)",
    "aprueba": "coalesce(p.aprueba_gobierno, -99)",
    "posicion": "case when p.posicion_politica > 0 then (p.posicion_politica - 1) // 2 else 5 end",
    "confianza": "coalesce(p.confianza_gobierno, -99)",
    "quinquenio": "p.edad_quinquenal",
    "colegio": "coalesce(p.dependencia_colegio, -99)",
}
# Cómo se llama cada dato en el informe.
NOMBRES = {
    "comuna": "comuna", "zona": "zona", "sexo": "sexo", "edad": "tramo de edad", "tipo": "tipo político", "eje": "eje político",
    "laboral": "situación laboral", "educacion": "educación", "menores": "niños en el hogar", "quintil": "quintil de ingreso",
    "voto": "voto en 2025", "aprueba": "evaluación del gobierno", "posicion": "posición política", "confianza": "confianza en el gobierno",
    "quinquenio": "edad en tramos de cinco años", "colegio": "tipo de colegio de los menores",
}
# El orden con que se forman los grupos en cada nivel, de lo que más separa a lo que menos. Va uno por nivel.
ORDENES = [
    ("comuna", "zona", "tipo", "sexo", "edad", "eje", "laboral"),
    ("comuna", "zona", "tipo", "sexo", "edad", "eje", "laboral"),
    ("zona", "tipo", "sexo", "edad", "eje", "laboral", "comuna"),
    ("tipo", "edad", "sexo", "eje", "zona", "laboral"),
]
# Lo que el representante de cada grupo ayuda a equilibrar en su región. Un par es el cruce de dos datos.
EQUILIBRAR = (
    "tipo", "voto", "aprueba", "posicion", "confianza", "sexo", "edad", "laboral", "educacion", "menores",
    "quintil", "zona", "comuna", "quinquenio", "colegio", ("sexo", "edad"), ("tipo", "edad"),
)
# En qué se mide cuánto se parece cada persona a quien la representa: (dato, cómo se llama en el informe).
PARECIDO = [
    ("tipo", "Tipo político"),
    ("aprueba", "Evaluación del gobierno"),
    ("voto", "Voto en 2025"),
    ("laboral", "Situación laboral"),
    ("edad", "Tramo de edad"),
    ("sexo", "Sexo"),
    ("comuna", "Comuna"),
]

# Lo que se compara entre la tabla reducida y la población completa: (título, columna, condición, se equilibra).
COMPARAR = [
    ("Sexo", "sexo", "true", True),
    ("Edad en tramos de cinco años", "edad_quinquenal", "true", True),
    ("Zona urbana o rural", "area", "true", True),
    ("Situación en la fuerza de trabajo", "sit_fuerza_trabajo", "sit_fuerza_trabajo > 0", True),
    ("Tipo político", "tipo_politico", "tipo_politico is not null", True),
    ("Voto en la segunda vuelta de 2025", "voto_segunda_vuelta_2025", "voto_segunda_vuelta_2025 is not null", True),
    ("Posición política", "posicion_politica", "posicion_politica is not null", True),
    ("Evaluación del gobierno", "aprueba_gobierno", "aprueba_gobierno is not null", True),
    ("Confianza en el gobierno", "confianza_gobierno", "confianza_gobierno is not null", True),
    ("Nivel educativo", "cine11", "cine11 > 0", False),
    ("Decil de ingreso del hogar", "decil_ingreso", "decil_ingreso is not null", False),
    ("Previsión de salud", "prevision_salud", "prevision_salud is not null", False),
    ("Tipo de colegio de los menores", "dependencia_colegio", "dependencia_colegio is not null", True),
    ("Apertura a la inmigración", "apertura_inmigracion", "apertura_inmigracion is not null", False),
    ("Justifica las marchas", "justifica_marchas", "justifica_marchas is not null", False),
    ("Confianza en Carabineros", "confianza_carabineros", "confianza_carabineros is not null", False),
]
# Los subgrupos que se pueden filtrar en el sitio, y las opiniones que se miran dentro de cada uno.
SUBGRUPOS = [
    ("Región", "region"),
    ("Sexo y edad", "sexo * 10 + case when edad < 18 then 0 when edad < 30 then 1 when edad < 45 then 2 when edad < 60 then 3 else 4 end"),
    ("Quintil de ingreso", "quintil_ingreso"),
    ("Educación", "case when cine11 between 8 and 11 then 2 when cine11 in (6, 7) then 1 else 0 end"),
    ("Posición política", "case when posicion_politica > 0 then (posicion_politica - 1) // 2 else 5 end"),
]
OPINIONES_SUBGRUPO = ["aprueba_gobierno", "voto_segunda_vuelta_2025", "apertura_inmigracion", "justifica_marchas", "confianza_carabineros"]
# Un subgrupo con menos de esta parte de la población no se mide: casi no tiene agentes en ningún nivel.
SUBGRUPO_MINIMO = 0.005


def codigos(valores):
    """Los mismos valores como enteros seguidos desde 0."""
    return np.unique(valores, return_inverse=True)[1].astype(np.int32)


def tipos_politicos(respuestas, usos, k=TIPOS, semilla=SEMILLA):
    """Agrupa a los entrevistados en tipos políticos: (tipo de 1 a k, lugar en el eje principal).

    `respuestas` trae, por cada dato de POLITICA, la respuesta de cada entrevistado; `usos`, cuántas
    personas tienen sus opiniones. Cada respuesta posible es una columna de unos y ceros con el peso
    de su dato; de ahí salen los ejes principales, y sobre ellos un k-medias ponderado por los usos.
    Los tipos quedan numerados a lo largo del eje principal, de un extremo político al otro."""
    usos = np.asarray(usos, dtype=float)
    columnas = []
    for dato, peso in POLITICA:
        valores = codigos(respuestas[dato])
        columnas.append(np.eye(valores.max() + 1)[valores] * np.sqrt(peso))
    x = np.hstack(columnas)
    x = x - (x * usos[:, None]).sum(axis=0) / usos.sum()
    direcciones = np.linalg.svd(x * np.sqrt(usos)[:, None], full_matrices=False)[2][:EJES]
    # El signo de cada eje es arbitrario: se fija para que el resultado no dependa de la máquina.
    direcciones = direcciones * np.sign(direcciones[np.arange(len(direcciones)), np.abs(direcciones).argmax(axis=1)])[:, None]
    puntos = x @ direcciones.T
    k = min(k, len(np.unique(puntos.round(9), axis=0)))
    mejor, menor = None, np.inf
    for intento in range(INTENTOS):
        rng = np.random.default_rng(semilla + intento)
        centros = puntos[rng.choice(len(puntos), k, replace=False, p=usos / usos.sum())]
        for _ in range(200):
            distancias = ((puntos[:, None, :] - centros[None]) ** 2).sum(axis=2)
            tipo = distancias.argmin(axis=1)
            nuevos = centros.copy()
            for i in range(k):
                suyos = tipo == i
                if suyos.any():
                    nuevos[i] = (puntos[suyos] * usos[suyos, None]).sum(axis=0) / usos[suyos].sum()
            if np.allclose(nuevos, centros):
                break
            centros = nuevos
        dispersion = float((distancias[np.arange(len(puntos)), tipo] * usos).sum())
        if dispersion < menor:
            mejor, menor = tipo, dispersion
    medias = [(puntos[mejor == i, 0] * usos[mejor == i]).sum() / max(usos[mejor == i].sum(), 1) for i in range(k)]
    numero_de = np.empty(k, dtype=np.int32)
    numero_de[np.argsort(medias, kind="stable")] = np.arange(1, k + 1)
    eje = np.argsort(np.argsort(puntos[:, 0], kind="stable"), kind="stable").astype(np.int32)
    return numero_de[mejor], eje


def categorias_de(datos):
    """Matriz (personas × datos de EQUILIBRAR): en cada celda, el número de la categoría entre todas las de todos los datos."""
    n = len(next(iter(datos.values())))
    matriz = np.empty((n, len(EQUILIBRAR)), dtype=np.int32)
    base = 0
    for columna, dato in enumerate(EQUILIBRAR):
        if isinstance(dato, tuple):
            a, b = dato
            valores = codigos(datos[a].astype(np.int64) * (int(datos[b].max()) + 1) + datos[b])
        else:
            valores = datos[dato]
        matriz[:, columna] = valores + base
        base += int(valores.max()) + 1
    return matriz.astype(np.int16) if base < 32000 else matriz


def formar_grupos(claves, azar):
    """Ordena a los integrantes por `claves` (la primera manda; `azar` desempata) y los corta de a RAZON.

    Devuelve el orden y, para cada lugar de ese orden, el número de su grupo."""
    orden = np.lexsort([azar, *reversed(claves)])
    return orden, np.arange(len(orden)) // RAZON


def elegir(categorias, pesos, grupo):
    """El lugar del representante de cada grupo, eligiendo al que mejor equilibra lo que va faltando.

    Los integrantes vienen ordenados por grupo. `deficit` lleva, por categoría, las personas que ya
    pasaron menos las que representan los elegidos hasta ahora: de cada grupo se toma al integrante
    cuyas categorías están más atrasadas, y se le descuenta el peso de todo el grupo."""
    cortes = np.r_[0, np.flatnonzero(np.diff(grupo)) + 1, len(grupo)]
    deficit = np.zeros(int(categorias.max()) + 1)
    elegidos = np.empty(len(cortes) - 1, dtype=np.int64)
    for i, (a, b) in enumerate(zip(cortes[:-1].tolist(), cortes[1:].tolist())):
        suyas, suyos = categorias[a:b], pesos[a:b]
        np.add.at(deficit, suyas, suyos[:, None])
        mejor = int(deficit[suyas].sum(axis=1).argmax())
        deficit[suyas[mejor]] -= suyos.sum()
        elegidos[i] = a + mejor
    return elegidos


def reducir(datos, semilla=SEMILLA, ordenes=ORDENES):
    """Reduce a las personas de una región, nivel por nivel.

    `datos` trae un arreglo de enteros por cada nombre de DATOS. Devuelve una lista con un par por
    nivel, (personas elegidas, a cuántas representa cada una), y otra con cuántas personas coinciden
    con quien las representa en cada dato de PARECIDO."""
    datos = {nombre: codigos(valores) for nombre, valores in datos.items()}
    n = len(datos["tipo"])
    categorias = categorias_de(datos)
    rng = np.random.default_rng(semilla)
    miembros, pesos, representante = np.arange(n), np.ones(n, dtype=np.int64), np.arange(n)
    niveles, parecido = [], []
    for claves in ordenes:
        orden, grupo = formar_grupos([datos[c][miembros] for c in claves], rng.permutation(len(miembros)))
        ordenados, sus_pesos = miembros[orden], pesos[orden]
        elegidos = ordenados[elegir(categorias[ordenados], sus_pesos, grupo)]
        de_cada_miembro = np.zeros(n, dtype=np.int64)
        de_cada_miembro[ordenados] = elegidos[grupo]
        representante = de_cada_miembro[representante]
        miembros, pesos = elegidos, np.bincount(grupo, weights=sus_pesos).astype(np.int64)
        niveles.append((miembros, pesos))
        parecido.append({dato: int((datos[dato] == datos[dato][representante]).sum()) for dato, _ in PARECIDO})
    return niveles, parecido


def guardar_tipos(con, origen):
    """Deja la tabla temporal `tipos` (cep_id_donante, tipo, eje) con el tipo político de cada entrevistado."""
    columnas = ", ".join(f"any_value(coalesce({dato}, -99))::integer as {dato}" for dato, _ in POLITICA)
    entrevistados = con.execute(
        f"select cep_id_donante, count(*) as usos, {columnas} from {origen} where cep_id_donante is not null group by 1 order by 1"
    ).fetchnumpy()
    tipo, eje = tipos_politicos(entrevistados, entrevistados["usos"])
    con.execute("create or replace temp table tipos (cep_id_donante varchar, tipo integer, eje integer)")
    con.executemany("insert into tipos values (?, ?, ?)", [[str(d), int(t), int(e)] for d, t, e in zip(entrevistados["cep_id_donante"], tipo, eje)])
    return len(tipo)


def leer_region(con, origen, region):
    """Los identificadores y los datos de DATOS de las personas de una región, en un orden fijo."""
    columnas = ", ".join(f"({expresion})::integer as {nombre}" for nombre, expresion in DATOS.items())
    filas = con.execute(
        f"""select p.id_persona_muestra as id, {columnas}
            from {origen} p left join tipos t on p.cep_id_donante = t.cep_id_donante
            where p.region = {region} order by p.id_persona_muestra"""
    ).fetchnumpy()
    return filas.pop("id"), filas


def miles(n):
    return f"{int(n):,}".replace(",", ".")


def numero(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def distribucion(con, tabla, columna, condicion, peso):
    filas = con.execute(f"select {columna}, sum({peso}) from {tabla} where {condicion} group by 1").fetchall()
    total = sum(float(n) for _, n in filas)
    return {valor: 100 * float(n) / total for valor, n in filas}


def por_subgrupo(con, tabla, subgrupo, columna, pesos):
    """{valor del subgrupo: [por cada peso, {respuesta: cuánto suma}]}, entre quienes tienen esa opinión."""
    sumas = ", ".join(f"coalesce(sum({peso}), 0)" for peso in pesos)
    resultado = {}
    for valor, respuesta, *cuanto in con.execute(
        f"select ({subgrupo}) as subgrupo, {columna}, {sumas} from {tabla} where {columna} is not null and ({subgrupo}) is not null group by 1, 2"
    ).fetchall():
        for i, n in enumerate(cuanto):
            resultado.setdefault(valor, [{} for _ in pesos])[i][respuesta] = float(n)
    return resultado


def desvio_en_subgrupos(con, poblacion, agentes):
    """Por nivel, la diferencia media (en puntos) de una opinión dentro de un subgrupo, y cuántos subgrupos quedaron sin agentes."""
    pesos = [columna for _, columna in NIVELES]
    diferencias, vacios = [[] for _ in pesos], [0 for _ in pesos]
    for _, subgrupo in SUBGRUPOS:
        for columna in OPINIONES_SUBGRUPO:
            real = por_subgrupo(con, poblacion, subgrupo, columna, ["1"])
            reducida = por_subgrupo(con, agentes, subgrupo, columna, pesos)
            todas = sum(sum(r[0].values()) for r in real.values())
            for valor, (respuestas,) in real.items():
                total = sum(respuestas.values())
                if total < SUBGRUPO_MINIMO * todas:
                    continue
                for i in range(len(pesos)):
                    suyas = reducida.get(valor, [{} for _ in pesos])[i]
                    suma = sum(suyas.values())
                    if not suma:
                        vacios[i] += 1
                        continue
                    diferencias[i].append(max(abs(100 * suyas.get(r, 0) / suma - 100 * n / total) for r, n in respuestas.items()))
    return [sum(d) / len(d) if d else float("nan") for d in diferencias], vacios


def describir_tipos(con, poblacion):
    """Una fila del informe por tipo político: cuánta gente es y cómo responde lo principal."""
    filas = con.execute(
        f"""select tipo_politico, count(*),
                   100.0 * count(*) filter (where voto_segunda_vuelta_2025 = 1) / count(*),
                   100.0 * count(*) filter (where voto_segunda_vuelta_2025 = 2) / count(*),
                   100.0 * count(*) filter (where aprueba_gobierno = 1) / count(*),
                   100.0 * count(*) filter (where aprueba_gobierno_anterior = 1) / count(*),
                   avg(posicion_politica) filter (where posicion_politica > 0),
                   100.0 * count(*) filter (where posicion_politica < 0) / count(*),
                   100.0 * count(*) filter (where confianza_gobierno in (1, 2)) / count(*)
            from {poblacion} where tipo_politico is not null group by 1 order by 1"""
    ).fetchall()
    adultos = sum(f[1] for f in filas)
    return [
        f"| {tipo} | {numero(100 * n / adultos, 1)} | {numero(jara, 0)} | {numero(kast, 0)} | {numero(aprueba, 0)} | {numero(anterior, 0)} | "
        f"{numero(posicion, 1) if posicion is not None else 'sin dato'} | {numero(sin_posicion, 0)} | {numero(confia, 0)} |"
        for tipo, n, jara, kast, aprueba, anterior, posicion, sin_posicion, confia in filas
    ]


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    chile, salida, contexto = (Path(a) for a in sys.argv[1:4])
    salida.mkdir(parents=True, exist_ok=True)
    for viejo in salida.glob("region_*.parquet"):
        viejo.unlink()
    con = duckdb.connect(config={"memory_limit": "6GB"})
    inicio = time.perf_counter()
    origen = f"read_parquet('{(chile / 'chile.parquet').as_posix()}')"
    regiones = [r for (r,) in con.execute(f"select distinct region from {origen} order by 1").fetchall()]

    entrevistados = guardar_tipos(con, origen)
    print(f"{entrevistados:,} entrevistados de la CEP agrupados en {TIPOS} tipos políticos.".replace(",", "."), flush=True)
    poblacion = f"(select p.*, t.tipo as tipo_politico from {origen} p left join tipos t on p.cep_id_donante = t.cep_id_donante)"

    print(f"Reduciendo región por región, con niveles de {', '.join(miles(n) for n, _ in NIVELES)} ...", flush=True)
    coincidencias = [{dato: 0 for dato, _ in PARECIDO} for _ in NIVELES]
    for region in regiones:
        destino = salida / f"region_{region:02d}.parquet"
        ids, datos = leer_region(con, origen, region)
        niveles, parecido = reducir(datos, SEMILLA + region)
        for i, cuenta in enumerate(parecido):
            for dato, n in cuenta.items():
                coincidencias[i][dato] += n
        for i, (elegidos, pesos) in enumerate(niveles):
            con.register(f"nivel_{i}", {"id": ids[elegidos], "representa": pesos})
        del datos
        uniones = " ".join(f"left join nivel_{i} n{i} on p.id_persona_muestra = n{i}.id" for i in range(1, len(NIVELES)))
        columnas = ", ".join(f"n{i}.representa::integer as {columna}" for i, (_, columna) in enumerate(NIVELES))
        con.execute(
            f"""copy (
                  select p.*, {columnas}
                  from {poblacion} p join nivel_0 n0 on p.id_persona_muestra = n0.id {uniones}
                  where p.region = {region}
                  order by p.id_persona_muestra
                ) to '{destino.as_posix()}' (format parquet, compression zstd, compression_level 19, row_group_size 100000)"""
        )
        for i in range(len(NIVELES)):
            con.unregister(f"nivel_{i}")
        cuentas = con.execute(
            f"select count(*), sum(representa), {', '.join(f'count({c})' for _, c in NIVELES[1:])} from '{destino.as_posix()}'"
        ).fetchall()[0]
        print(f"   región {region:>2}: {cuentas[0]:>8,} agentes por {cuentas[1]:>9,} personas; "
              + ", ".join(f"{n:>7,} de a {miles(p)}" for n, (p, _) in zip(cuentas[2:], NIVELES[1:]))
              + f"  ({destino.stat().st_size / 1e6:5.1f} MB)", flush=True)

    agentes = f"read_parquet('{(salida / 'region_*.parquet').as_posix()}')"
    n_agentes, representadas = con.execute(f"select count(*), sum(representa) from {agentes}").fetchall()[0]
    n_personas = con.execute(f"select count(*) from {origen}").fetchall()[0][0]
    peso_total = sum(p.stat().st_size for p in salida.glob("region_*.parquet"))
    assert representadas == n_personas, (representadas, n_personas)
    cuantos, anterior = {}, None
    for _, columna in NIVELES:
        cuantos[columna] = con.execute(f"select count({columna}) from {agentes}").fetchall()[0][0]
        por_region = con.execute(
            f"""select count(*) from (select region, sum({columna}) n from {agentes} group by 1) a
                join (select region, count(*) n from {origen} group by 1) b using (region) where a.n <> b.n"""
        ).fetchall()[0][0]
        assert por_region == 0, f"la suma de `{columna}` no coincide con la población de alguna región"
        if anterior:
            fuera = con.execute(f"select count(*) from {agentes} where {columna} is not null and {anterior} is null").fetchall()[0][0]
            assert fuera == 0, f"`{columna}` no está contenida en `{anterior}`"
        anterior = columna

    print("Comparando con la población completa ...", flush=True)
    filas, peores = [], {(columna, equilibrado): 0.0 for _, columna in NIVELES for equilibrado in (True, False)}
    for titulo, columna, condicion, equilibrado in COMPARAR:
        completa = distribucion(con, poblacion, columna, condicion, "1")
        celdas = []
        for _, peso in NIVELES:
            reducida = distribucion(con, agentes, columna, f"({condicion}) and {peso} is not null", peso)
            dif = max(abs(reducida.get(v, 0) - completa.get(v, 0)) for v in set(completa) | set(reducida))
            peores[peso, equilibrado] = max(peores[peso, equilibrado], dif)
            celdas.append(numero(dif))
        filas.append(f"| {titulo} | {'sí' if equilibrado else 'no'} | {len(completa)} | {' | '.join(celdas)} |")
    comunas = []
    for _, peso in NIVELES:
        comunas.append(con.execute(
            f"""select count(*) filter (where a.n is null),
                       100 * avg(abs(coalesce(a.n, 0) - b.n) / b.n) filter (where b.n >= 5000)
                from (select comuna, count(*) n from {origen} group by 1) b
                left join (select comuna, sum({peso}) n from {agentes} where {peso} is not null group by 1) a using (comuna)"""
        ).fetchall()[0])
    desvios, vacios = desvio_en_subgrupos(con, poblacion, agentes)
    encabezado = " | ".join(f"1 por cada {miles(n)}" for n, _ in NIVELES)
    rayas = "---|" * len(NIVELES)

    contexto.mkdir(parents=True, exist_ok=True)
    (contexto / "agentes.md").write_text(
        "\n".join([
            "# Tabla de agentes",
            "",
            f"`data/agentes/` tiene {miles(n_agentes)} agentes que representan a las {miles(n_personas)} personas de 14 años o más de `data/chile/`: "
            f"1 de cada {RAZON}. Es la tabla que usa el motor del sitio para filtrar y sacar la muestra, y por eso se versiona "
            f"({numero(peso_total / 1e6, 0)} MB, un archivo por región). La escribe `scripts/reducir_poblacion.py`; este informe también, no lo edites a mano.",
            "",
            "Cada fila es una persona real del censo, con todas sus columnas (las mismas de `data/chile/chile.parquet`), más su tipo político "
            "(`tipo_politico`) y a cuántas personas representa en cada nivel de reducción. Los niveles son anidados: quien representa a 1.000 es uno de los que representan a 100.",
            "",
            "| Nivel | Columna | Agentes | Cómo se usa |",
            "|---|---|---|---|",
            *[f"| 1 agente por cada {miles(n)} personas | `{columna}` | {miles(cuantos[columna])} | "
              + ("Todas las filas." if columna == "representa" else f"Las filas donde `{columna}` no es nula.") + " |" for n, columna in NIVELES],
            "",
            "Para una cifra de la población, cada fila se pondera por la columna de su nivel. En el sitio, el nivel se elige en el cajón de filtros («Clusterización»).",
            "",
            "## Cómo se agrupa",
            "",
            "Lo que más pesa en una opinión es la política; la demografía pesa poco (`contexto/metodo/influencia.md`). La reducción agrupa primero por eso:",
            "",
            f"1. **Tipos políticos.** Todas las opiniones de una persona vienen de un mismo entrevistado de la Encuesta CEP, y hay {miles(entrevistados)}. "
            f"Se agrupan en {TIPOS} tipos según su voto, su evaluación de los dos gobiernos, su posición política, su confianza en el gobierno, "
            "su opinión sobre reducir el gasto público y su partido, cada dato con el peso que tiene para predecir las demás opiniones. "
            "Cada persona hereda el tipo de su entrevistado. Los menores de 18 años no tienen opiniones y quedan sin tipo.",
            f"2. **Grupos de {RAZON}.** En cada nivel, los integrantes se ordenan y se cortan de a {RAZON}; el nivel siguiente agrupa a los representantes del anterior. "
            "El orden cambia con el nivel (el eje político es el lugar del entrevistado entre un extremo político y el otro):",
            "",
            "   | Nivel | Orden |",
            "   |---|---|",
            *[f"   | 1 por cada {miles(n)} | región, {', '.join(NOMBRES[d] for d in orden)} |" for (n, _), orden in zip(NIVELES, ORDENES)],
            "",
            "   Mientras hay gente suficiente, cada grupo es de una sola comuna y de un solo tipo político. En los niveles más reducidos no alcanza para ambas cosas y se prefiere el tipo político.",
            "3. **Representante por equilibrio.** Los grupos se recorren llevando la cuenta de qué categorías van quedando con menos peso del que les corresponde en la región, "
            "y de cada grupo se toma al integrante que mejor lo compensa. Se equilibran: "
            + ", ".join(" con ".join(NOMBRES[x] for x in d) if isinstance(d, tuple) else NOMBRES[d] for d in EQUILIBRAR)
            + ". No se usa el integrante más típico del grupo (el medoide), porque elige siempre a la mayoría y hace desaparecer a las minorías.",
            "",
            "## Los tipos políticos",
            "",
            "Numerados a lo largo del eje que más separa a los entrevistados. Porcentajes sobre las personas de 18 años o más de cada tipo.",
            "",
            "| Tipo | % de los adultos | Votó por Jara | Votó por Kast | Aprueba al gobierno | Aprueba al gobierno anterior | Posición media (1 izquierda, 10 derecha) | Sin posición | Confía en el gobierno |",
            "|---|---|---|---|---|---|---|---|---|",
            *describir_tipos(con, poblacion),
            "",
            "## Cuánto se parece cada persona a quien la representa",
            "",
            "Porcentaje de las personas que coinciden con su representante en cada dato.",
            "",
            f"| Dato | {encabezado} |",
            f"|---|{rayas}",
            *[f"| {titulo} | " + " | ".join(numero(100 * coincidencias[i][dato] / n_personas, 1) for i in range(len(NIVELES))) + " |" for dato, titulo in PARECIDO],
            "",
            "## Comparación con la población completa",
            "",
            "La suma de cada columna es exactamente la población en cada región. Diferencia máxima, en puntos porcentuales, "
            "entre la población completa y los agentes de cada nivel, ponderados. «Se equilibra» dice si el dato entra en la elección del representante.",
            "",
            f"| Dato | Se equilibra | Categorías | {encabezado} |",
            f"|---|---|---|{rayas}",
            *filas,
            "",
            "Por comuna y por subgrupo. El desvío en subgrupos es la diferencia media de una opinión "
            f"({', '.join(f'`{c}`' for c in OPINIONES_SUBGRUPO)}) dentro de cada subgrupo que se puede filtrar en el sitio "
            f"({', '.join(titulo.lower() for titulo, _ in SUBGRUPOS)}).",
            "",
            f"| Medida | {encabezado} |",
            f"|---|{rayas}",
            "| Comunas sin ningún agente | " + " | ".join(miles(sin) for sin, _ in comunas) + " |",
            "| Error medio de la población por comuna (comunas de 5.000 personas o más), % | " + " | ".join(numero(error, 1) for _, error in comunas) + " |",
            "| Desvío medio de una opinión dentro de un subgrupo, puntos | " + " | ".join(numero(d) for d in desvios) + " |",
            "| Subgrupos sin ningún agente | " + " | ".join(miles(v) for v in vacios) + " |",
            "",
            "Lo que se equilibra calza casi exacto mientras hay agentes suficientes; lo demás difiere por lo que no explica el grupo, y más cuanto más se reduce: "
            "con menos agentes hay menos casos de cada tipo. Lo que aplica a pocas personas, como el tipo de colegio de los menores, es lo que más se desvía en los niveles más reducidos. "
            f"Con 1 agente por cada {miles(NIVELES[-1][0])} personas no hay agentes para todas las comunas: en ese nivel el mapa vale por región, y un filtro deja pocos agentes.",
            "",
            "Fuentes: INE, Censo de Población y Vivienda 2024; Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024; Centro de Estudios Públicos, Encuesta CEP N° 96.",
            "",
        ]),
        encoding="utf-8",
    )
    print(f"Listo en {time.perf_counter() - inicio:.0f} s: {n_agentes:,} agentes representan a {n_personas:,} personas; {peso_total / 1e6:.0f} MB en {salida}")
    print("Diferencia máxima con la población completa, en lo que se equilibra y en lo demás: "
          + "; ".join(f"de a {miles(n)}, {numero(peores[c, True])} y {numero(peores[c, False])} puntos" for n, c in NIVELES)
          + f". Informe en {contexto / 'agentes.md'}")


if __name__ == "__main__":
    main()
