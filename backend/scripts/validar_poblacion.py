#!/usr/bin/env python3
"""Revisa que la población construida calce con Chile: con el censo, con Casen y con la CEP.

Uso:
    uv run python -I scripts/validar_poblacion.py data/chile data/censo2024 data/casen2024 data/cep96 contexto/chile

Compara data/chile (lo que escribe scripts/construir_poblacion.py) con sus tres fuentes y
escribe contexto/chile/validacion.md. Revisa tres cosas:

1. Contra el censo: que estén todas las personas de 14 años o más y todos los hogares, comuna
   por comuna, que nada observado haya cambiado y que los menores de 14 sigan contados en su hogar.
2. Contra Casen: que cada dato imputado tenga la misma distribución que en Casen (ponderada),
   en el país y por región, y que se relacione con los demás como en Casen (correlaciones).
3. Contra la CEP: lo mismo para las opiniones imputadas a los adultos.

Termina con código de salida 1 si alguna comprobación falla.

La población conserva la composición del censo, que no es idéntica a la de las encuestas: el
censo registra menos empleo y más trabajo independiente que Casen, y más católicos que la CEP.
Como esas son llaves del emparejamiento, lo imputado hereda la diferencia. Por eso cada
distribución se compara dos veces: tal cual, y con la encuesta reponderada para que tenga la
composición de la población en las llaves ("a igual composición"). La segunda es la que dice
si la imputación está bien hecha.

Las correlaciones se calculan con las mismas definiciones en ambos lados y solo con los
casos que tienen ambos datos. Entre un dato de Casen y uno de la CEP no hay fuente con qué
comparar: esa relación existe en la población solo a través de las llaves del emparejamiento.
"""

import csv
import sys
from itertools import combinations
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import imputar_cep as cep_  # noqa: E402
from construir_muestra import DE_LA_PERSONA, DEL_HOGAR  # noqa: E402

# Tolerancias: puntos porcentuales en las distribuciones y diferencia de correlación.
MAX_DISTRIBUCION = 2.0
# La CEP tiene 1.466 casos y su manual declara un margen de error de 2,8 puntos (95 % de confianza):
# una diferencia menor que eso no se distingue del error de la propia encuesta.
MAX_DISTRIBUCION_CEP = 2.8
MAX_CORRELACION = 0.05

# Datos del censo (observados) y de Casen (imputados), con la misma definición en ambas fuentes.
OBSERVADAS = {
    "edad": "edad",
    "mujer": "(sexo = 2)::int",
    # Casen calcula la escolaridad desde los 15 años; el censo, desde los 5.
    "escolaridad (15+)": "case when edad >= 15 and escolaridad >= 0 then escolaridad end",
    "ocupado (15+)": "case when edad >= 15 and sit_fuerza_trabajo in (1, 2, 3) then (sit_fuerza_trabajo = 1)::int end",
    "rural": "(area = 2)::int",
    "indígena": "case when p28_autoid_pueblo in (1, 2) then (p28_autoid_pueblo = 1)::int end",
    "personas en el hogar": "n_personas",
}
IMPUTADAS = {
    "decil de ingreso": "decil_ingreso",
    "ingreso per cápita (log)": "ln(1 + ingreso_total_pc)",
    "pobreza": "case when pobreza_ingresos in (1, 2, 3) then (pobreza_ingresos < 3)::int end",
    "vehículo en el hogar": "case when tiene_vehiculo in (1, 2) then (tiene_vehiculo = 1)::int end",
    "isapre": "case when prevision_salud > 0 then (prevision_salud = 2)::int end",
    "cotiza para pensión": "case when cotiza_pension in (0, 1) then cotiza_pension end",
    "tiene contrato": "case when tiene_contrato in (0, 1) then tiene_contrato end",
    "participa en organizaciones": "case when participa_organizacion between 1 and 15 then (participa_organizacion <> 15)::int end",
    "sin a quién pedir dinero": "case when red_dinero between 1 and 4 then (red_dinero = 4)::int end",
    "inseguridad alimentaria": "case when inseg_alim_preocupacion in (1, 2) then (inseg_alim_preocupacion = 1)::int end",
    "discriminación en el hogar": "case when discrim_ninguna in (0, 1) then 1 - discrim_ninguna end",
    "cuida a un dependiente": "case when es_cuidador in (0, 1) then es_cuidador end",
}
# Distribuciones que se comparan con Casen: (título, tabla, columna, condición).
DISTRIBUCIONES_CASEN = [
    ("Decil de ingreso del hogar", "hogares", "decil_ingreso", "true"),
    ("Pobreza por ingresos del hogar", "hogares", "pobreza_ingresos", "true"),
    ("Vehículo en el hogar", "hogares", "tiene_vehiculo", "true"),
    ("Alguien a quien pedir dinero", "hogares", "red_dinero", "true"),
    ("Sin discriminación en el hogar", "hogares", "discrim_ninguna", "true"),
    ("Previsión de salud", "personas", "prevision_salud", "true"),
    ("Grupo de Fonasa", "personas", "fonasa_grupo", "prevision_salud = 1"),
    ("Categoría ocupacional de los ocupados", "personas", "categoria_ocupacional", "sit_fuerza_trabajo = 1"),
    ("Contrato de los asalariados", "personas", "tiene_contrato", "sit_fuerza_trabajo = 1"),
    ("Cotiza para pensión (15 años o más)", "personas", "cotiza_pension", "edad >= 15"),
    ("Participación en organizaciones", "personas", "participa_organizacion", "edad >= 14"),
    ("Tipo de colegio (14 a 17 años que asisten)", "personas", "dependencia_colegio", "edad between 14 and 17 and dependencia_colegio between 1 and 5"),
]
# Opiniones de la CEP, con el signo ordenado para que más sea más.
OPINIONES = {
    "posición (1 izquierda a 10 derecha)": "case when posicion_politica > 0 then posicion_politica end",
    "aprueba al gobierno": "case when aprueba_gobierno in (1, 2, 3) then (aprueba_gobierno = 1)::int end",
    "aprueba al gobierno anterior": "case when aprueba_gobierno_anterior in (1, 2, 3) then (aprueba_gobierno_anterior = 1)::int end",
    "votó por Kast": "case when voto_segunda_vuelta_2025 in (1, 2) then (voto_segunda_vuelta_2025 = 2)::int end",
    "confianza en el gobierno": "case when confianza_gobierno between 1 and 4 then 5 - confianza_gobierno end",
    "confianza en el Congreso": "case when confianza_congreso between 1 and 4 then 5 - confianza_congreso end",
    "confianza en Carabineros": "case when confianza_carabineros between 1 and 4 then 5 - confianza_carabineros end",
    "confianza en las empresas": "case when confianza_empresas between 1 and 4 then 5 - confianza_empresas end",
    "confianza en los sindicatos": "case when confianza_sindicatos between 1 and 4 then 5 - confianza_sindicatos end",
    "interés en la política": "case when interes_politica between 1 and 5 then 6 - interes_politica end",
    "sustento: responsabilidad personal": "case when responsabilidad_sustento > 0 then responsabilidad_sustento end",
    "menos Estado en la economía": "case when menos_estado_economia between 1 and 5 then 6 - menos_estado_economia end",
    "seguridad sobre libertades": "case when libertades_o_seguridad >= 0 then libertades_o_seguridad end",
    "apertura a la inmigración": "case when apertura_inmigracion > 0 then apertura_inmigracion end",
    "buena situación económica propia": "case when economia_personal between 1 and 5 then economia_personal end",
    "los ingresos no alcanzan": "case when ingresos_alcanzan between 1 and 4 then ingresos_alcanzan end",
}
LLAVES_CEP = {"edad": "edad", "mujer": "(sexo = 2)::int", "educación (1 a 4)": "case when educ4 between 1 and 4 then educ4 end"}
REL4 = "case when p31_religion = 1 then 1 when p31_religion = 2 then 2 when p31_religion = 12 then 3 when p31_religion in (5, 10, 999) then 4 else 9 end"
# Llaves con que se iguala la composición de Casen a la de la población. La relación laboral
# (independiente, dependiente, familiar) es la del censo en la población y la de Casen en Casen.
EDAD10 = "case when edad < 15 then 0 when edad < 25 then 15 when edad < 35 then 25 when edad < 45 then 35 when edad < 55 then 45 when edad < 65 then 55 when edad < 75 then 65 else 75 end"
EDUC3 = "case when edad < 15 then 0 when escolaridad is null or escolaridad < 0 then 9 when escolaridad < 12 then 1 when escolaridad = 12 then 2 else 3 end"
ACTIV = "case when sit_fuerza_trabajo in (1, 2, 3) then sit_fuerza_trabajo::int else 0 end"
RELACION_CENSO = "case when p40_cise_rec in (1, 2, 3) then p40_cise_rec::int else 0 end"
RELACION_CASEN = "case when categoria_ocupacional in (1, 2) then 1 when categoria_ocupacional between 3 and 8 then 2 when categoria_ocupacional = 9 then 3 else 0 end"
CELDA_CASEN = "concat_ws('-', sexo::int, {edad10}, {educ3}, {activ}, {{relacion}})".format(edad10=EDAD10, educ3=EDUC3, activ=ACTIV)
CELDA_CEP = "concat_ws('-', sexo::int, case when edad < 25 then 18 when edad < 35 then 25 when edad < 45 then 35 when edad < 55 then 45 when edad < 65 then 55 when edad < 75 then 65 else 75 end, educ4::int, rel4::int)"
EDUC4 = "case when cine11 in (1, 2, 3, 4, 5, 12) then 1 when cine11 in (6, 7) then 2 when cine11 = 8 then 3 when cine11 in (9, 10, 11) then 4 else 9 end"


def miles(n):
    return f"{int(n):,}".replace(",", ".")


def numero(x, d=1):
    return "—" if x is None or pd.isna(x) else f"{x:.{d}f}".replace(".", ",")


def tabla_md(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    return "\n".join(lineas + ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas])


def correlaciones_ponderadas(df, variables, peso):
    """Correlación de Pearson ponderada de cada par, con los casos que tienen ambos datos."""
    w_todo = df[peso].to_numpy("float64")
    salida = {}
    for a, b in combinations(variables, 2):
        x, y = df[a].to_numpy("float64"), df[b].to_numpy("float64")
        ok = ~(np.isnan(x) | np.isnan(y))
        x, y, w = x[ok], y[ok], w_todo[ok]
        if len(x) < 30 or x.std() == 0 or y.std() == 0:
            salida[(a, b)] = None
            continue
        mx, my = np.average(x, weights=w), np.average(y, weights=w)
        cov = np.average((x - mx) * (y - my), weights=w)
        salida[(a, b)] = cov / np.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w))
    return salida


def correlaciones_poblacion(con, vista, variables):
    """Las mismas correlaciones en la población, donde cada persona vale lo mismo."""
    pares = list(combinations(variables, 2))
    alias = {v: f"v{i}" for i, v in enumerate(variables)}
    columnas = ", ".join(f"{expr} as {alias[v]}" for v, expr in variables.items())
    calculo = ", ".join(f"corr({alias[a]}, {alias[b]})" for a, b in pares)
    fila = con.execute(f"with t as (select {columnas} from {vista}) select {calculo} from t").fetchall()[0]
    return dict(zip(pares, fila))


def distribucion(con, vista, columna, condicion, peso="1"):
    filas = con.execute(
        f"select {columna}, sum({peso}) from {vista} where ({condicion}) and {columna} is not null group by 1 order by 1"
    ).fetchall()
    total = sum(float(n) for _, n in filas)
    return {int(valor): 100 * float(n) / total for valor, n in filas}


def pesos_a_igual_composicion(con, vista_fuente, celda_fuente, peso, vista_poblacion, celda_poblacion):
    """Peso de cada fila de la encuesta para que sus celdas pesen lo mismo que en la población.

    Devuelve (pesos en el orden de la vista, porcentaje de la población en celdas que la encuesta tiene)."""
    pob = dict(con.execute(f"select {celda_poblacion}, count(*) from {vista_poblacion} group by 1").fetchall())
    filas = con.execute(f"select {celda_fuente} as celda, {peso}::double as w from {vista_fuente} order by fila").df()
    total = filas.groupby("celda")["w"].sum()
    factor = filas["celda"].map(lambda c: pob.get(c, 0) / total[c])
    cubierta = 100 * sum(n for c, n in pob.items() if c in total.index) / sum(pob.values())
    return (filas["w"] * factor).to_numpy(), cubierta


class Informe:
    def __init__(self):
        self.partes, self.fallas = [], []

    def titulo(self, texto):
        self.partes += [texto, ""]
        print("\n" + texto.lstrip("# "))

    def texto(self, *lineas):
        self.partes += [*lineas, ""]

    def tabla(self, encabezado, filas):
        self.partes += [tabla_md(encabezado, filas), ""]

    def comprobar(self, nombre, condicion, detalle):
        print(f"   {'OK   ' if condicion else 'FALLA'} {nombre}: {detalle}")
        self.partes.append(f"- {'✔' if condicion else '✘ **FALLA**'} {nombre}: {detalle}")
        if not condicion:
            self.fallas.append(nombre)


def comparar_correlaciones(informe, nombre, poblacion, fuente, grupos, cuantas=12):
    """Tabla de los pares que más difieren y resumen por tipo de par."""
    filas = []
    for par, r_fuente in fuente.items():
        r_pob = poblacion.get(par)
        if r_fuente is None or r_pob is None:
            continue
        filas.append((abs(r_pob - r_fuente), par, r_fuente, r_pob, grupos(par)))
    filas.sort(reverse=True)
    resumen = {}
    for dif, _, r_fuente, _, tipo in filas:
        resumen.setdefault(tipo, []).append((dif, abs(r_fuente)))
    informe.tabla(
        ["Tipo de par", "Pares", "Diferencia media", "Diferencia máxima", f"Correlación media en {nombre} (valor absoluto)"],
        [[tipo, len(v), numero(np.mean([d for d, _ in v]), 3), numero(max(d for d, _ in v), 3), numero(np.mean([r for _, r in v]), 3)]
         for tipo, v in resumen.items()],
    )
    informe.texto(f"Los {cuantas} pares que más difieren:")
    informe.tabla(
        ["Par", "Tipo", nombre, "Población", "Diferencia"],
        [[f"{a} × {b}", tipo, numero(r_fuente, 3), numero(r_pob, 3), numero(r_pob - r_fuente, 3)] for _, (a, b), r_fuente, r_pob, tipo in filas[:cuantas]],
    )
    informe.texto("Las relaciones más fuertes de la fuente, para ver que se conservan:")
    fuertes = sorted(filas, key=lambda f: -abs(f[2]))[:cuantas]
    informe.tabla(
        ["Par", "Tipo", nombre, "Población", "Diferencia"],
        [[f"{a} × {b}", tipo, numero(r_fuente, 3), numero(r_pob, 3), numero(r_pob - r_fuente, 3)] for _, (a, b), r_fuente, r_pob, tipo in fuertes],
    )
    return resumen


def main():
    if len(sys.argv) != 6:
        sys.exit(__doc__)
    chile, censo, casen_dir, cep_dir, contexto = (Path(a) for a in sys.argv[1:])
    contexto.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for tabla in ("personas", "hogares", "actitudes", "chile"):
        con.execute(f"create view {tabla} as select * from '{(chile / f'{tabla}.parquet').as_posix()}'")
    for tabla in ("personas", "hogares"):
        con.execute(f"create view censo_{tabla} as select * from '{(censo / 'microdatos' / f'{tabla}_censo2024.parquet').as_posix()}'")
    raiz = Path(__file__).resolve().parent.parent
    con.execute(f"create view comunas as select * from read_csv('{(raiz / 'contexto' / 'censo2024' / 'comunas.csv').as_posix()}')")
    with open(raiz / "contexto" / "censo2024" / "territorios.csv", encoding="utf-8", newline="") as f:
        regiones = {int(r["codigo"]): r["nombre"] for r in csv.DictReader(f) if r["nivel"] == "region"}
    informe = Informe()
    uno = lambda sql: con.execute(sql).fetchall()[0]

    n_per, n_hog, n_adultos = uno("select (select count(*) from personas), (select count(*) from hogares), (select count(*) from actitudes)")
    edad_minima = uno("select min(edad) from personas")[0]
    informe.partes += [
        "# Validación de la población completa",
        "",
        f"`data/chile/` tiene {miles(n_per)} personas de {edad_minima} años o más y {miles(n_hog)} hogares: todos los registros del Censo 2024 desde esa edad, con datos imputados desde Casen 2024 "
        f"y, para los {miles(n_adultos)} adultos, opiniones imputadas desde la Encuesta CEP N° 96. Los menores de {edad_minima} no son filas, pero siguen contados en su hogar. "
        "Este documento lo escribe `scripts/validar_poblacion.py` y compara esa población con sus tres fuentes.",
        "",
        "En las tablas, la población se cuenta persona por persona (cada fila vale 1) y las encuestas se ponderan con su factor de expansión. "
        f"Una distribución pasa si ninguna categoría difiere en más de {numero(MAX_DISTRIBUCION, 0)} puntos porcentuales "
        f"({numero(MAX_DISTRIBUCION_CEP)} en las opiniones, que es el margen de error que declara la CEP); "
        f"un conjunto de correlaciones pasa si la diferencia media no supera {numero(MAX_CORRELACION, 2)}.",
        "",
    ]

    # ------------------------------------------------------------ 1. Censo
    informe.titulo("## 1. Contra el censo")
    informe.texto("Lo que viene del censo no se imputa: debe estar todo y sin cambios.")
    # El censo publica la edad exacta salvo en las comunas pequeñas, donde solo da el tramo de cinco años.
    # Desde los 15 años el conteo se puede comparar en todas las comunas; el de 14, donde la edad es exacta.
    desde_15, de_14, c_desde_15, c_de_14, c_hog, c_en_hogares, c_fuera = uno(
        """select (select count(*) from personas where edad_quinquenal >= 15),
                  (select count(*) from personas where edad = 14 and edad_imputada = 0),
                  (select count(*) from censo_personas where edad_quinquenal >= 15),
                  (select count(*) from censo_personas where edad = 14),
                  (select count(*) from censo_hogares where tipo_operativo = 2),
                  (select count(*) from censo_personas where tipo_operativo = 2),
                  (select count(*) from censo_personas where tipo_operativo <> 2)"""
    )
    oficial = uno("select sum(poblacion), sum(hogares) from comunas")
    informe.comprobar("nadie bajo la edad mínima", edad_minima == 14, f"la persona más joven tiene {edad_minima} años")
    informe.comprobar("personas de 15 años o más", desde_15 == c_desde_15, f"{miles(desde_15)} en la población y {miles(c_desde_15)} en los microdatos")
    informe.comprobar("personas de 14 años", de_14 == c_de_14, f"{miles(de_14)} en la población y {miles(c_de_14)} en los microdatos, en las comunas donde el censo publica la edad exacta")
    informe.comprobar("hogares", n_hog == c_hog == oficial[1], f"{miles(n_hog)} en la población, {miles(c_hog)} en los microdatos y {miles(oficial[1])} en las cifras oficiales por comuna")
    en_hogares, menores, con_lista = uno("select sum(n_personas), sum(menores_de_14), sum(len(edades_menores)) from hogares")
    informe.comprobar("los hogares conservan a todos sus integrantes", en_hogares == c_en_hogares and en_hogares + c_fuera == oficial[0],
                      f"suman {miles(en_hogares)} personas, igual que el censo; con las {miles(c_fuera)} fuera de hogares son las {miles(oficial[0])} de las cifras oficiales")
    filas_en_hogares = uno("select count(*) from personas where id_hogar_muestra is not null")[0]
    informe.comprobar("menores de 14 contados en su hogar", menores == en_hogares - filas_en_hogares,
                      f"{miles(menores)} menores de 14 que no son filas: es la diferencia entre los integrantes de los hogares y las personas de 14 o más que viven en ellos. "
                      f"Las edades de {miles(con_lista)} menores de 18 quedan guardadas en su hogar")
    malas, total = uno(
        """with p as (select comuna, count(*) n, count(*) filter (where sexo = 1) h from personas where edad_quinquenal >= 15 group by 1),
                c as (select comuna, count(*) n, count(*) filter (where sexo = 1) h from censo_personas where edad_quinquenal >= 15 group by 1),
                h as (select comuna, count(*) n from hogares group by 1)
           select count(*) filter (where p.n is distinct from c.n or p.h is distinct from c.h or coalesce(h.n, 0) is distinct from o.hogares), count(*)
           from comunas o left join p using (comuna) left join c using (comuna) left join h using (comuna)"""
    )
    informe.comprobar("personas de 15 o más, hombres y hogares de cada comuna", malas == 0, f"{total - malas} de {total} comunas coinciden con el censo")
    distintas = uno(
        """with a as (select region, comuna, area, sexo, edad_quinquenal, coalesce(p23_est_civil, 0) ec, coalesce(cine11, 0) ed, coalesce(sit_fuerza_trabajo, 0) act, count(*) n from personas where edad_quinquenal >= 15 group by all),
                b as (select region, comuna, area, sexo, edad_quinquenal, coalesce(p23_est_civil, 0) ec, coalesce(cine11, 0) ed, coalesce(sit_fuerza_trabajo, 0) act, count(*) n from censo_personas where edad_quinquenal >= 15 group by all)
           select count(*) from a full join b using (region, comuna, area, sexo, edad_quinquenal, ec, ed, act)
           where a.n is distinct from b.n"""
    )[0]
    informe.comprobar("cruce de comuna, zona, sexo, edad, estado civil, educación y actividad (15 o más)", distintas == 0, f"{distintas} celdas distintas respecto de los microdatos")
    sin_id, repetidas = uno("select count(*) filter (where id_persona_muestra is null), count(*) - count(distinct id_persona_muestra) from personas")
    informe.comprobar("identificador de persona", sin_id == 0 and repetidas == 0, f"{sin_id} vacíos y {repetidas} repetidos")
    imputadas, negativas = uno("select count(*) filter (where edad_imputada = 1), count(*) filter (where edad < 0) from personas")
    informe.comprobar("edad", negativas == 0, f"ninguna suprimida; en {miles(imputadas)} personas de comunas pequeñas se sorteó dentro de su tramo de cinco años")
    sin_decil, sin_prevision = uno("select (select count(*) from hogares where decil_ingreso is null), (select count(*) from personas where id_hogar_muestra is not null and prevision_salud is null)")
    informe.comprobar("todos los hogares y sus integrantes tienen datos de Casen", sin_decil == 0 and sin_prevision == 0, f"{sin_decil} hogares sin decil y {sin_prevision} personas sin previsión")
    sin_opinion = uno("select count(*) from personas p left join actitudes a using (id_persona_muestra) where p.edad >= 18 and a.posicion_politica is null")[0]
    informe.comprobar("todos los adultos tienen opiniones de la CEP", sin_opinion == 0 and n_adultos == uno("select count(*) from personas where edad >= 18")[0], f"{miles(n_adultos)} adultos, {sin_opinion} sin datos")
    informe.texto("")

    # ------------------------------------------------------------ 2. Casen
    informe.titulo("## 2. Contra Casen")
    cas = con.execute(f"select * from '{(casen_dir / 'casen_2024.parquet').as_posix()}' where dau is not null").df()
    cas = cas.rename(columns={**DEL_HOGAR, **DE_LA_PERSONA, "esc": "escolaridad", "activ": "sit_fuerza_trabajo", "depen": "dependencia_colegio"})
    cas.loc[cas["e3"] != 1, "dependencia_colegio"] = np.nan
    cas["p28_autoid_pueblo"] = cas["pueblos_indigenas"].map({1: 1, 0: 2})
    cas["n_personas"] = cas.groupby("folio")["folio"].transform("size")
    cas["fila"] = np.arange(len(cas))
    con.register("cas_df", cas)
    cas["expr_igual"], cubierta = pesos_a_igual_composicion(
        con, "cas_df", CELDA_CASEN.format(relacion=RELACION_CASEN), "expr",
        "personas where id_hogar_muestra is not null", CELDA_CASEN.format(relacion=RELACION_CENSO))
    con.unregister("cas_df")
    con.register("cas_df", cas)
    con.execute(f"create view casen_personas as select * from cas_df where edad >= {edad_minima}")
    con.execute("create view casen_hogares as select * from cas_df where pco1 = 1")
    informe.texto(
        f"Casen 2024 tiene {miles(len(cas))} personas en {miles(cas['folio'].nunique())} hogares. Se pondera con `expr`. Las personas se comparan desde los {edad_minima} años.",
        "",
        "### Distribuciones",
        "",
        "Diferencia máxima, en puntos porcentuales, entre la población y Casen en cada dato imputado. Los datos del hogar se comparan tal cual. "
        "Los de la persona se comparan además «a igual composición»: con Casen reponderada para que tenga, como la población, la misma mezcla de sexo, edad, "
        f"escolaridad, actividad y relación laboral (independiente o dependiente). Esas celdas cubren el {numero(cubierta, 2)} % de la población.",
        "",
        "El censo registra menos ocupados y más independientes que Casen, y la imputación respeta lo que dice el censo de cada persona. "
        "Por eso, tal cual, la población tiene menos empleados del sector privado y menos cotizantes que Casen; a igual composición la diferencia desaparece.",
    )
    filas, peor = [], 0
    for titulo, tabla, columna, condicion in DISTRIBUCIONES_CASEN:
        de_persona = tabla == "personas"
        pob = distribucion(con, tabla, columna, condicion + (" and id_hogar_muestra is not null" if de_persona else ""))
        diferencias = []
        for peso in ("expr", "expr_igual") if de_persona else ("expr",):
            fuente = distribucion(con, f"casen_{tabla}", columna, condicion, peso)
            dif = {v: pob.get(v, 0) - fuente.get(v, 0) for v in set(pob) | set(fuente)}
            valor = max(dif, key=lambda v: abs(dif[v]))
            diferencias.append((abs(dif[valor]), f"código {valor}: {numero(fuente.get(valor, 0))} % en Casen y {numero(pob.get(valor, 0))} % en la población"))
        peor = max(peor, diferencias[-1][0])
        filas.append([titulo, len(dif), numero(diferencias[0][0], 2), numero(diferencias[1][0], 2) if de_persona else "—", diferencias[-1][1]])
    informe.tabla(["Dato", "Categorías", "Diferencia tal cual", "A igual composición", "Dónde queda la mayor diferencia"], filas)
    informe.comprobar("distribuciones nacionales de lo imputado desde Casen", peor <= MAX_DISTRIBUCION, f"diferencia máxima de {numero(peor, 2)} puntos (hogares tal cual; personas a igual composición)")
    informe.texto("")

    informe.texto("### Por región", "", "Porcentaje de hogares en pobreza por ingresos e ingreso medio per cápita del hogar, en Casen y en la población. Casen es representativa por región.")
    por_region = lambda vista, peso: {
        r: (pobres, ingreso, isapre)
        for r, pobres, ingreso, isapre in con.execute(
            f"""select region, 100 * sum({peso} * (pobreza_ingresos < 3)::int) / sum({peso}), sum({peso} * ingreso_total_pc) / sum({peso}),
                       100 * sum({peso} * (decil_ingreso >= 9)::int) / sum({peso})
                from {vista} group by 1 order by 1"""
        ).fetchall()
    }
    pob, fuente = por_region("hogares", "1"), por_region("casen_hogares", "expr")
    filas = [[regiones[r], numero(fuente[r][0]), numero(pob[r][0]), numero(pob[r][0] - fuente[r][0], 2),
              miles(fuente[r][1]), miles(pob[r][1]), numero(100 * (pob[r][1] / fuente[r][1] - 1)) + " %",
              numero(fuente[r][2]), numero(pob[r][2])] for r in sorted(pob)]
    informe.tabla(["Región", "Pobreza Casen %", "Pobreza población %", "Diferencia", "Ingreso Casen $", "Ingreso población $", "Diferencia", "Deciles 9 y 10 Casen %", "Deciles 9 y 10 población %"], filas)
    peor_region = max(abs(pob[r][0] - fuente[r][0]) for r in pob)
    peor_ingreso = max(abs(pob[r][1] / fuente[r][1] - 1) for r in pob)
    informe.comprobar("pobreza de cada región", peor_region <= MAX_DISTRIBUCION, f"diferencia máxima de {numero(peor_region, 2)} puntos")
    informe.comprobar("ingreso medio de cada región", peor_ingreso <= 0.05, f"diferencia máxima de {numero(100 * peor_ingreso)} %")
    informe.texto("")

    informe.texto(
        "### Por edad",
        "",
        "Porcentaje de personas que viven en hogares en pobreza por ingresos e ingreso medio per cápita de su hogar, según su edad. "
        "El ingreso se imputa al hogar, así que esta relación depende de que el emparejamiento distinga los hogares con niños de los hogares con adultos mayores.",
    )
    tramo = "case when edad < 18 then '14 a 17' when edad < 30 then '18 a 29' when edad < 45 then '30 a 44' when edad < 65 then '45 a 64' else '65 o más' end"
    por_edad = lambda vista, peso: {
        t: (pobres, ingreso)
        for t, pobres, ingreso in con.execute(
            f"select {tramo}, 100 * sum({peso} * (pobreza_ingresos < 3)::int) / sum({peso}), sum({peso} * ingreso_total_pc) / sum({peso}) from {vista} group by 1 order by 1"
        ).fetchall()
    }
    pob, fuente = por_edad("chile where id_hogar_muestra is not null", "1"), por_edad("casen_personas where pobreza_ingresos is not null", "expr")
    informe.tabla(
        ["Edad", "Pobreza Casen %", "Pobreza población %", "Diferencia", "Ingreso Casen $", "Ingreso población $", "Diferencia"],
        [[t, numero(fuente[t][0]), numero(pob[t][0]), numero(pob[t][0] - fuente[t][0], 2), miles(fuente[t][1]), miles(pob[t][1]),
          numero(100 * (pob[t][1] / fuente[t][1] - 1)) + " %"] for t in sorted(pob)],
    )
    peor_edad = max(abs(pob[t][0] - fuente[t][0]) for t in pob)
    informe.comprobar("pobreza de cada tramo de edad", peor_edad <= MAX_DISTRIBUCION, f"diferencia máxima de {numero(peor_edad, 2)} puntos")
    informe.texto("")

    informe.texto(
        "### Tipo de colegio de los menores",
        "",
        "Porcentaje de los menores de 14 a 17 años que asisten a clases según el tipo de colegio, por quintil de ingreso de su hogar. "
        "El censo no pregunta el tipo de colegio: se imputa desde Casen según el decil del hogar, la región y la zona.",
    )
    colegio = lambda vista, peso: {
        (q, d): pct
        for q, d, pct in con.execute(
            f"""with t as (select quintil_ingreso q, case when dependencia_colegio in (1, 5) then 'público' when dependencia_colegio = 2 then 'subvencionado'
                                  when dependencia_colegio = 3 then 'pagado' else 'delegada' end d, sum({peso}) n
                           from {vista} where edad between 14 and 17 and dependencia_colegio between 1 and 5 and quintil_ingreso is not null group by all)
                select q, d, 100.0 * n / sum(n) over (partition by q) from t"""
        ).fetchall()
    }
    pob, fuente = colegio("chile", "1"), colegio("casen_personas", "expr")
    tipos = ("público", "subvencionado", "pagado", "delegada")
    informe.tabla(
        ["Quintil"] + [f"{t.capitalize()} {origen} %" for t in tipos for origen in ("Casen", "población")],
        [[int(q)] + [numero(lado.get((q, t), 0)) for t in tipos for lado in (fuente, pob)] for q in sorted({q for q, _ in pob})],
    )
    peor_colegio = max(abs(pob.get(k, 0) - fuente.get(k, 0)) for k in set(pob) | set(fuente))
    informe.comprobar("tipo de colegio por quintil de ingreso", peor_colegio <= 2 * MAX_DISTRIBUCION, f"diferencia máxima de {numero(peor_colegio, 2)} puntos; cada quintil tiene pocos casos en Casen, por eso la tolerancia es de {numero(2 * MAX_DISTRIBUCION, 0)}")
    informe.texto("")

    informe.texto(
        "### Correlaciones",
        "",
        "Correlación de Pearson entre pares de datos, en Casen y en la población. «Observado» es lo que viene del censo y «imputado», lo que viene de Casen. "
        "Las de dos datos observados no dependen de la imputación: difieren porque el censo y Casen no miden igual la educación ni el empleo.",
    )
    variables = {**OBSERVADAS, **IMPUTADAS}
    columnas = ", ".join(f"{expr} as \"{v}\"" for v, expr in variables.items())
    en_casen = correlaciones_ponderadas(con.execute(f"select {columnas}, expr from casen_personas").df(), list(variables), "expr")
    en_poblacion = correlaciones_poblacion(con, "chile where id_hogar_muestra is not null", variables)
    tipo = lambda par: "observado × observado" if all(v in OBSERVADAS for v in par) else "imputado × imputado" if all(v in IMPUTADAS for v in par) else "imputado × observado"
    resumen = comparar_correlaciones(informe, "Casen", en_poblacion, en_casen, tipo)
    for nombre in ("imputado × imputado", "imputado × observado"):
        media = np.mean([d for d, _ in resumen[nombre]])
        informe.comprobar(f"correlaciones {nombre} (Casen)", media <= MAX_CORRELACION, f"diferencia media de {numero(media, 3)} en {len(resumen[nombre])} pares; máxima de {numero(max(d for d, _ in resumen[nombre]), 3)}")
    informe.texto("")

    # ------------------------------------------------------------ 3. CEP
    informe.titulo("## 3. Contra la CEP")
    cep = pd.read_parquet(cep_dir / "cep96.parquet")
    don = cep_.estandarizar_cep(cep)
    cep_v = cep.rename(columns=cep_.DE_LA_CEP)[list(cep_.DE_LA_CEP.values())].assign(
        sexo=don["sexo"], edad=don["edad"], educ4=don["educ4"], rel4=don["rel4"], pond=don["pond"], fila=np.arange(len(cep)))
    con.register("cep_df", cep_v)
    con.execute(f"create view adultos as select *, {EDUC4} as educ4, {REL4} as rel4 from chile where edad >= 18")
    cep_v["pond_igual"], cubierta = pesos_a_igual_composicion(con, "cep_df", CELDA_CEP, "pond", "adultos", CELDA_CEP)
    con.unregister("cep_df")
    con.register("cep_df", cep_v)
    informe.texto(
        f"La Encuesta CEP N° 96 tiene {miles(len(cep))} entrevistas a mayores de 18 años. Se pondera con `pond`.",
        "",
        "### Distribuciones",
        "",
        "Diferencia máxima, en puntos porcentuales, entre los adultos de la población y la CEP en cada opinión imputada: tal cual, y «a igual composición», "
        f"con la CEP reponderada para que tenga la misma mezcla de sexo, edad, educación y religión que la población (celdas que cubren el {numero(cubierta, 2)} % de los adultos).",
        "",
        "El censo tiene más católicos y menos personas sin religión que la CEP, y la religión es una llave del emparejamiento. "
        "Por eso, tal cual, la población confía algo más en la Iglesia católica que la CEP.",
    )
    filas, peor = [], 0
    for columna in cep_.DE_LA_CEP.values():
        pob = distribucion(con, "adultos", columna, "true")
        diferencias = []
        for peso in ("pond", "pond_igual"):
            fuente = distribucion(con, "cep_df", columna, "true", peso)
            dif = {v: pob.get(v, 0) - fuente.get(v, 0) for v in set(pob) | set(fuente)}
            valor = max(dif, key=lambda v: abs(dif[v]))
            diferencias.append((abs(dif[valor]), f"código {valor}: {numero(fuente.get(valor, 0))} % en la CEP y {numero(pob.get(valor, 0))} % en la población"))
        peor = max(peor, diferencias[1][0])
        filas.append((diferencias[1][0], [f"`{columna}`", len(dif), numero(diferencias[0][0], 2), numero(diferencias[1][0], 2), diferencias[1][1]]))
    filas.sort(key=lambda f: -f[0])
    informe.tabla(["Opinión", "Categorías", "Diferencia tal cual", "A igual composición", "Dónde queda la mayor diferencia"], [f for _, f in filas])
    sobre = sum(1 for d, _ in filas if d > MAX_DISTRIBUCION)
    informe.comprobar(f"distribuciones de las {len(filas)} opiniones imputadas desde la CEP", peor <= MAX_DISTRIBUCION_CEP,
                      f"diferencia máxima de {numero(peor, 2)} puntos a igual composición; {sobre} opiniones superan los {numero(MAX_DISTRIBUCION, 0)} puntos y ninguna el margen de error de la CEP ({numero(MAX_DISTRIBUCION_CEP)})"
                      if peor <= MAX_DISTRIBUCION_CEP else f"diferencia máxima de {numero(peor, 2)} puntos a igual composición, sobre el margen de error de la CEP ({numero(MAX_DISTRIBUCION_CEP)})")
    informe.texto("")

    informe.texto(
        "### Correlaciones",
        "",
        "Entre opiniones, y entre cada opinión y la edad, el sexo y la educación. Como todas las opiniones de una persona vienen del mismo entrevistado, "
        "la relación entre ellas debe conservarse casi intacta. La relación con la edad, el sexo y la educación se conserva porque son llaves del emparejamiento.",
    )
    variables = {**LLAVES_CEP, **OPINIONES}
    columnas = ", ".join(f"{expr} as \"{v}\"" for v, expr in variables.items())
    en_cep = correlaciones_ponderadas(con.execute(f"select {columnas}, pond from cep_df").df(), list(variables), "pond")
    en_poblacion = correlaciones_poblacion(con, "adultos", variables)
    tipo = lambda par: "llave × llave" if all(v in LLAVES_CEP for v in par) else "opinión × opinión" if all(v in OPINIONES for v in par) else "opinión × llave"
    resumen = comparar_correlaciones(informe, "CEP", en_poblacion, en_cep, tipo)
    for nombre in ("opinión × opinión", "opinión × llave"):
        media = np.mean([d for d, _ in resumen[nombre]])
        informe.comprobar(f"correlaciones {nombre} (CEP)", media <= MAX_CORRELACION, f"diferencia media de {numero(media, 3)} en {len(resumen[nombre])} pares; máxima de {numero(max(d for d, _ in resumen[nombre]), 3)}")
    informe.texto("")

    # ------------------------------------------------------------ 4. Entre fuentes
    informe.titulo("## 4. Entre Casen y la CEP: sin fuente con qué comparar")
    informe.texto(
        "Ninguna encuesta mide a la vez el ingreso de Casen y las opiniones de la CEP. En la población esas relaciones existen solo a través de lo que ambas "
        "imputaciones comparten: sexo, edad, educación, zona, actividad y nivel socioeconómico. Son plausibles, pero no están validadas; se muestran para que se sepa qué hay.",
    )
    cruces = {
        "decil de ingreso": IMPUTADAS["decil de ingreso"], "isapre": IMPUTADAS["isapre"], "cotiza para pensión": IMPUTADAS["cotiza para pensión"],
        "posición (1 izquierda a 10 derecha)": OPINIONES["posición (1 izquierda a 10 derecha)"], "aprueba al gobierno": OPINIONES["aprueba al gobierno"],
        "los ingresos no alcanzan": OPINIONES["los ingresos no alcanzan"], "buena situación económica propia": OPINIONES["buena situación económica propia"],
        "sustento: responsabilidad personal": OPINIONES["sustento: responsabilidad personal"],
    }
    entre = correlaciones_poblacion(con, "adultos where id_hogar_muestra is not null", cruces)
    de_casen = ("decil de ingreso", "isapre", "cotiza para pensión")
    informe.tabla(["Par", "Correlación en la población"], [[f"{a} × {b}", numero(r, 3)] for (a, b), r in entre.items() if (a in de_casen) != (b in de_casen)])

    informe.titulo("## Resultado")
    informe.texto("Todas las comprobaciones pasan." if not informe.fallas else f"Fallan {len(informe.fallas)} comprobaciones: {', '.join(informe.fallas)}.", "",
                  "Fuentes: INE, Censo de Población y Vivienda 2024; Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024; Centro de Estudios Públicos, Encuesta CEP N° 96.")
    (contexto / "validacion.md").write_text("\n".join(informe.partes) + "\n", encoding="utf-8")
    print(f"\nInforme en {contexto / 'validacion.md'}")
    if informe.fallas:
        sys.exit(f"Fallan {len(informe.fallas)} comprobaciones: {', '.join(informe.fallas)}")


if __name__ == "__main__":
    main()
