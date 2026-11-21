#!/usr/bin/env python3
"""Saca personas de la muestra del 1 % y arma su perfil para simular sus respuestas.

Uso:
    uv run python -I scripts/personas_muestra.py data/muestra/muestra.parquet data/pruebas/poblacion/al_azar_200.jsonl [N] [SEMILLA]
    uv run python -I scripts/personas_muestra.py data/muestra/muestra.parquet SALIDA --por-region 50
    uv run python -I scripts/personas_muestra.py data/chile/chile.parquet SALIDA --por-region 500

Sirve igual con la muestra del 1 % (data/muestra/muestra.parquet) que con la población
completa (data/chile/chile.parquet), que ya trae las opiniones de la CEP en la misma tabla.

El perfil es general: describe a la persona con todo lo que las fuentes saben de ella, sin
mirar qué se le va a preguntar. Sirve igual para una ley de sala cuna, una de pensiones o una
pregunta sobre seguridad. Lo que es propio de un caso (el texto, las preguntas, las cifras
reales con que se valida) vive en la carpeta del caso, no aquí.

Toma N personas de 14 años o más al azar (--edad-minima cambia el corte). Por defecto
N = 200 y SEMILLA = 1; con la misma semilla sale la misma selección. Con --por-region K
toma K personas de cada región (o todas, si hay menos) y deja en "peso" cuánto vale cada
una para una cifra nacional. Los menores de 14 no se simulan, pero cuentan en la
descripción del hogar de los demás.

Los menores de edad (14 a 17) no tienen opiniones de la CEP, que entrevista desde los 18:
su perfil trae todo lo demás y, si van al colegio, de qué tipo es (imputado desde Casen).

Cada línea del archivo de salida tiene:
  "perfil"     el perfil por secciones: {título de la sección: texto en segunda persona}.
               El modelo lo lee como un solo texto (ver prosa_de en probar_modelo.py).
  "grupos"     pocas categorías por variable, para desagregar los resultados.
  "datos"      unos pocos datos sueltos (edad, género, región, comuna, zona, quintil) para
               los programas que filtran o dibujan a las personas, como el motor del sitio.
  "peso"       1 en la muestra al azar; con --por-region, adultos de la región por persona
               elegida, con media 1.

Secciones (--secciones elige cuáles, separadas por coma; por defecto van todas):
  identidad    edad, género, lugar, origen, estado civil, pueblo originario, religión
  trabajo      educación, situación laboral, ocupación, rama, previsión, traslado
  hogar        con quién vive, niños y adultos mayores, hijos, cuidados
  vivienda     tipo, tenencia, hacinamiento, internet, vehículo
  economia     ingreso del hogar, pobreza, si el dinero alcanza, preocupaciones
  salud_redes  previsión de salud, discapacidad, redes de apoyo, organizaciones, discriminación
  politica     posición, partido, evaluación de los gobiernos, voto, interés, democracia
  pais         problemas del país, economía, rol del Estado, seguridad, inmigración, familia
  confianza    confianza en 15 instituciones

De dónde sale cada dato:
  - Censo 2024: observado en esa persona y su hogar.
  - Casen 2024: imputado (ingresos, previsión, contrato, redes, discriminación...).
  - Encuesta CEP N° 96: imputado desde data/muestra/actitudes.parquet, que crea
    scripts/imputar_cep.py (toda la política, las opiniones y la confianza). Con
    --sin-actitudes, o si el archivo no existe, esas partes se omiten.
Lo imputado es un valor plausible para alguien de su perfil, no un dato de esa persona. Lo
subjetivo de la CEP y lo objetivo de Casen se imputan por separado: una persona puede quedar
con un ingreso alto y la opinión de que el dinero no le alcanza.

Con --personalidad agrega cinco rasgos de personalidad (Big Five) sorteados al azar: no
son un dato de ninguna fuente, solo dan variedad al razonamiento. Se sortea un puntaje T
por rasgo (media 50, desviación 10, entre 20 y 80) y se describe en palabras, como en
Nemotron-Personas. No se inventan valores de Schwartz: ninguna fuente los mide.
"""

import argparse
import csv
import json
import random
import re
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
CONTEXTO = RAIZ / "contexto"

SECCIONES = {
    "identidad": "Quién eres",
    "trabajo": "Educación y trabajo",
    "hogar": "Tu hogar",
    "vivienda": "Tu vivienda",
    "economia": "Tu situación económica",
    "salud_redes": "Salud, redes y participación",
    "politica": "Tu posición política",
    "pais": "Cómo ves el país",
    "confianza": "Tu confianza en las instituciones",
}
# Secciones que salen solo de la Encuesta CEP.
SOLO_CEP = ("politica", "pais", "confianza")

# Integrantes de cada hogar, para describir con quién vive cada persona. La muestra trae a todos
# los integrantes como filas; la población completa trae la composición ya calculada en el hogar,
# porque ahí los menores de 14 no son filas.
COMPOSICION = """
hogar AS (
    SELECT id_hogar_muestra,
           list(edad ORDER BY edad) FILTER (WHERE edad < 18) AS edades_menores,
           list(edad ORDER BY edad) FILTER (WHERE edad < 18 AND parentesco IN (5, 6)) AS edades_hijos_jefatura,
           count(*) FILTER (WHERE edad >= 65) AS mayores_65,
           count(*) FILTER (WHERE dependencia_grado IN (1, 2, 3)) AS dependientes,
           count(*) AS integrantes
    FROM read_parquet($muestra)
    WHERE id_hogar_muestra IS NOT NULL
    GROUP BY 1
),"""
CONSULTA = """
WITH {composicion} elegibles AS (
    SELECT persona.* {del_hogar} {actitudes},
           hash(id_persona_muestra, $semilla) AS orden,
           count(*) OVER (PARTITION BY region) AS adultos_region,
           row_number() OVER (PARTITION BY region ORDER BY hash(id_persona_muestra, $semilla)) AS lugar_en_region
    FROM read_parquet($muestra) AS persona {union_hogar} {union}
    WHERE edad >= $edad_minima
)
SELECT * FROM elegibles
"""

JEFATURA_O_PAREJA = (1, 2, 3, 4)
# El censo se levantó entre marzo y julio de 2024: un menor de 2 años nació desde 2022.
ANIO_MENOR_DE_2 = 2022
PRESIDENTE = "el presidente José Antonio Kast"
ANTERIOR = "Gabriel Boric"

ESTADO_CIVIL = {
    1: "Estás casad@.",
    2: "Convives con tu pareja.",
    3: "Convives con tu pareja, con acuerdo de unión civil.",
    4: "Tu matrimonio fue anulado.",
    5: "Estás separad@.",
    6: "Estás divorciad@.",
    7: "Eres viud@.",
    8: "Estás solter@.",
}
ROL = {
    1: "eres jef@ de hogar", 2: "eres la pareja de quien encabeza el hogar", 3: "eres la pareja de quien encabeza el hogar",
    4: "eres la pareja de quien encabeza el hogar", 5: "eres hij@ de quien encabeza el hogar",
    6: "eres hij@ de la pareja de quien encabeza el hogar", 7: "eres herman@ de quien encabeza el hogar",
    8: "eres padre o madre de quien encabeza el hogar", 9: "eres cuñad@ de quien encabeza el hogar",
    10: "eres suegr@ de quien encabeza el hogar", 11: "eres yerno o nuera de quien encabeza el hogar",
    12: "eres niet@ de quien encabeza el hogar", 13: "eres abuel@ de quien encabeza el hogar",
    14: "eres pariente de quien encabeza el hogar", 15: "no eres pariente de quien encabeza el hogar",
    16: "trabajas puertas adentro en el hogar donde vives",
}
TIPO_HOGAR = {
    1: "vives sol@", 2: "es un hogar de un padre o una madre con sus hijos", 3: "es una pareja sin hijos en casa",
    4: "es una pareja con hijos", 5: "es un hogar extenso, con otros parientes además del núcleo",
    6: "es un hogar compuesto, donde también vive gente que no es pariente", 7: "es un hogar sin núcleo familiar",
}
OCUPACION = {
    0: "miembro de las Fuerzas Armadas", 1: "directiv@ o gerente", 2: "profesional",
    3: "técnic@ o profesional de nivel medio", 4: "personal de apoyo administrativo",
    5: "trabajador@ de servicios o vendedor@", 6: "agricultor@ o trabajador@ agropecuario o pesquero",
    7: "operari@ o artesan@ de un oficio", 8: "operador@ de máquinas o conductor@",
    9: "trabajador@ en una ocupación elemental, sin calificación",
}
RAMA = {
    "A": "agricultura, ganadería, silvicultura o pesca", "B": "minería", "C": "industria manufacturera",
    "D": "electricidad y gas", "E": "agua y gestión de desechos", "F": "construcción", "G": "comercio",
    "H": "transporte y almacenamiento", "I": "alojamiento y servicios de comida", "J": "información y comunicaciones",
    "K": "actividades financieras y de seguros", "L": "actividades inmobiliarias",
    "M": "actividades profesionales, científicas y técnicas", "N": "servicios administrativos y de apoyo",
    "O": "administración pública y defensa", "P": "enseñanza", "Q": "salud y asistencia social",
    "R": "arte, entretenimiento y recreación", "S": "otros servicios", "T": "servicio doméstico en hogares",
}
TENENCIA = {
    1: "propia y ya pagada", 2: "propia y la están pagando", 3: "arrendada con contrato", 4: "arrendada sin contrato",
    5: "cedida por trabajo o servicio", 6: "cedida por un familiar u otra persona", 7: "en usufructo",
    8: "ocupada de hecho", 9: "una propiedad en sucesión o litigio",
}
DISCRIMINACION = {
    "nivel_socioeconomico": "su nivel socioeconómico", "nivel_educacional": "su nivel educacional", "ocupacion": "su ocupación",
    "sexo": "su sexo", "estado_civil": "su estado civil", "ropa": "su forma de vestir", "color_piel": "su color de piel",
    "extranjero": "ser extranjero", "edad": "su edad", "orientacion_genero": "su orientación sexual o identidad de género",
    "tatuajes": "tatuajes o piercings", "apariencia": "su apariencia física", "religion": "su religión",
    "politica": "sus ideas políticas", "sindicato": "participar en sindicatos", "lugar_residencia": "el lugar donde vive",
    "establecimiento": "el establecimiento donde estudió", "pueblo_indigena": "pertenecer a un pueblo indígena",
    "salud_discapacidad": "su salud o una discapacidad", "otro": "otro motivo",
}
# Tipo de colegio de los menores que asisten (códigos de Casen): (texto del perfil, grupo para el informe).
COLEGIO = {
    1: ("municipal", "Público"), 5: ("público, de un servicio local de educación", "Público"),
    2: ("particular subvencionado", "Particular subvencionado"), 3: ("particular pagado", "Particular pagado"),
    4: ("técnico de administración delegada", "Administración delegada"),
}
RELIGION = {
    1: "Eres católic@", 2: "Eres evangélic@ o protestante", 5: "Eres de la Iglesia de Jesucristo de los Santos de los Últimos Días",
    10: "Eres Testigo de Jehová", 12: "No tienes religión", 999: "Tienes otra religión o credo",
}
INSTITUCIONES = {
    "confianza_gobierno": "el gobierno", "confianza_congreso": "el Congreso", "confianza_partidos": "los partidos políticos",
    "confianza_tribunales": "los tribunales de justicia", "confianza_municipalidades": "las municipalidades",
    "confianza_carabineros": "Carabineros", "confianza_fuerzas_armadas": "las Fuerzas Armadas",
    "confianza_empresas": "las empresas privadas", "confianza_sindicatos": "los sindicatos",
    "confianza_sistema_salud": "el sistema de salud", "confianza_sistema_pensiones": "el sistema de pensiones",
    "confianza_television": "la televisión", "confianza_redes_sociales": "las redes sociales",
    "confianza_iglesia_catolica": "la Iglesia católica", "confianza_universidades": "las universidades",
}
# Rasgo: (cómo es quien puntúa bajo, cómo es quien puntúa alto).
BIG_FIVE = {
    "Apertura a la experiencia": ("prefieres lo conocido y lo práctico antes que las ideas nuevas", "eres curios@ y te gusta probar cosas nuevas"),
    "Responsabilidad": ("eres espontáne@ y te cuesta planificar", "eres ordenad@ y cumples lo que te propones"),
    "Extraversión": ("eres reservad@ y prefieres estar con poca gente", "eres sociable y te gusta conversar con la gente"),
    "Amabilidad": ("desconfías de las intenciones de los demás y dices lo que piensas sin rodeos", "confías en los demás y evitas los conflictos"),
    "Neuroticismo": ("te mantienes tranquil@ ante los problemas", "te preocupas con facilidad y te cuesta soltar los problemas"),
}


def leer_csv(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def cargar_etiquetas():
    censo = {}
    for fila in leer_csv(CONTEXTO / "censo2024" / "etiquetas.csv"):
        if re.fullmatch(r"-?\d+", fila["valor"]):  # hay filas de rangos, sin valor único
            censo.setdefault(fila["variable"], {})[int(fila["valor"])] = fila["etiqueta"].replace("​", "").strip()
    casen = {}
    for fila in leer_csv(CONTEXTO / "muestra" / "etiquetas_casen.csv"):
        if re.fullmatch(r"-?\d+", fila["valor"]):
            casen.setdefault(fila["columna"], {})[int(fila["valor"])] = re.sub(r"^\d+\.\s*", "", fila["etiqueta"])
    cep = {}
    ruta = CONTEXTO / "muestra" / "etiquetas_cep.csv"
    for fila in leer_csv(ruta) if ruta.exists() else []:
        cep.setdefault(fila["columna"], {})[int(fila["valor"])] = fila["etiqueta"].strip()
    territorios = {(f["nivel"], int(f["codigo"])): f["nombre"] for f in leer_csv(CONTEXTO / "censo2024" / "territorios.csv")}
    paises = {int(f["codigo"]): f["nombre"] for f in leer_csv(CONTEXTO / "censo2024" / "territorios_especificos.csv")}
    return {"censo": censo, "casen": casen, "cep": cep, "territorios": territorios, "paises": paises}


def valido(x):
    return x is not None and x >= 0


def minuscula(texto):
    return texto[0].lower() + texto[1:]


def lista(elementos):
    """'a', 'a y b', 'a, b y c'."""
    elementos = list(elementos)
    return elementos[0] if len(elementos) == 1 else ", ".join(elementos[:-1]) + " y " + elementos[-1]


def femenino(f):
    """True, False o None (sin dato o género no binario): decide las terminaciones del texto."""
    if f["genero"] in (1, 3):
        return False
    if f["genero"] in (2, 4):
        return True
    if valido(f["genero"]):
        return None
    return {1: False, 2: True}.get(f["sexo"])


def nivel_educacional(codigo, censo):
    etiqueta = censo["cine11"].get(codigo) if valido(codigo) else None
    return re.sub(r"^\d+:\s*", "", etiqueta) if etiqueta else None


def cantidad_hijos(f):
    """Los hijos de hombres vienen imputados de Casen: nunca menos que los que el censo ve en su hogar."""
    if not valido(f["hijos_total"]):
        return None
    return max(f["hijos_total"], f["hijos_en_hogar"] or 0)


def situacion_laboral(f):
    """(frase en segunda persona, grupo para el informe). El contrato es el que declara Casen: no dice si es indefinido."""
    situacion, categoria = f["sit_fuerza_trabajo"], f["categoria_ocupacional"]
    if situacion == 2:
        return "No tienes trabajo y estás buscando", "Desocupado"
    if situacion == 3:
        return "No trabajas remuneradamente ni buscas trabajo", "Fuera de la fuerza de trabajo"
    if situacion != 1:
        return None, None
    contrato = {1: ", con contrato de trabajo", 0: ", sin contrato de trabajo"}.get(f["tiene_contrato"], "")
    grupo = {1: "Asalariado con contrato", 0: "Asalariado sin contrato"}.get(f["tiene_contrato"], "Asalariado sin dato de contrato")
    if categoria == 1:
        return "Trabajas como empleador@: tienes un negocio o empresa con trabajadores a tu cargo", "Empleador"
    if categoria == 2:
        return "Trabajas por cuenta propia, como independiente", "Cuenta propia"
    if categoria in (3, 4):
        return f"Trabajas como emplead@ del sector público{contrato}", grupo
    if categoria == 5:
        return f"Trabajas como emplead@ de una empresa privada{contrato}", grupo
    if categoria in (6, 7):
        return f"Trabajas en una casa particular, en servicio doméstico{contrato}", "Casa particular"
    if categoria == 8:
        return "Trabajas en las Fuerzas Armadas o de Orden", grupo
    if categoria == 9:
        return "Trabajas sin sueldo en el negocio de un familiar", "Otro ocupado"
    return "Trabajas", "Otro ocupado"


# ---------------------------------------------------------------- secciones del censo y de Casen


def identidad(f, e, g):
    quien = {1: "hombre", 2: "mujer", 3: "hombre trans", 4: "mujer trans", 5: "una persona no binaria"}.get(f["genero"])
    quien = quien or (None if valido(f["genero"]) else {1: "hombre", 2: "mujer"}.get(f["sexo"]))
    edad = "85 años o más" if f["edad"] >= 85 else f"{f['edad']} años"
    region = e["territorios"].get(("region", f["region"]))
    comuna = e["territorios"].get(("comuna", f["comuna"]))
    zona = {1: "urbana", 2: "rural"}.get(f["area"])
    donde = f"vives en {comuna}, {'Región ' + region if region.startswith('Metropolitana') else 'región de ' + region}, en zona {zona}"
    frases = [f"Tienes {edad}, eres {quien} y {donde}." if quien else f"Tienes {edad} y {donde}."]
    g["Edad"] = "14 a 17" if f["edad"] < 18 else "18 a 29" if f["edad"] < 30 else "30 a 44" if f["edad"] < 45 else "45 a 59" if f["edad"] < 60 else "60 o más"
    g["Género"] = {1: "Masculino", 2: "Femenino", 3: "Masculino", 4: "Femenino"}.get(f["genero"]) or {1: "Masculino", 2: "Femenino"}.get(f["sexo"])
    g["Región"], g["Zona"] = region, zona.capitalize() if zona else None

    pais = e["paises"].get(f["p27_nacionalidad_esp"])
    if f["p27_nacionalidad"] == 1:
        frases.append("Tu nacionalidad es chilena.")
    elif f["p27_nacionalidad"] == 2:
        frases.append(f"Tienes doble nacionalidad: chilena y {pais if pais and pais != 'Chile' else 'otra'}.")
    elif f["p27_nacionalidad"] == 3:
        frases.append(f"Eres extranjer@, de {pais}." if pais else "Eres extranjer@.")
    g["Nacionalidad"] = {1: "Chilena", 2: "Doble nacionalidad", 3: "Extranjera"}.get(f["p27_nacionalidad"])
    if f["p25_lug_nacimiento"] == 1:
        frases.append("Naciste en la misma comuna donde vives.")
    elif f["p25_lug_nacimiento"] == 2:
        frases.append("Naciste en otra comuna de Chile.")
    elif f["p25_lug_nacimiento"] == 3:
        llegada = e["censo"]["p26_llegada_periodo"].get(f["p26_llegada_periodo"]) if valido(f["p26_llegada_periodo"]) else None
        frases.append(f"Naciste en otro país y llegaste a Chile {minuscula(llegada)}." if llegada else "Naciste en otro país.")
    if f["p24_lug_resid5"] in (3, 4):
        frases.append(f"Hace cinco años vivías en {'otra comuna' if f['p24_lug_resid5'] == 3 else 'otro país'}.")

    if f["p23_est_civil"] in ESTADO_CIVIL:
        frases.append(ESTADO_CIVIL[f["p23_est_civil"]])
    if f["p28_autoid_pueblo"] == 1:
        pueblo = e["censo"]["p28_pueblo_pert"].get(f["p28_pueblo_pert"]) if valido(f["p28_pueblo_pert"]) else None
        frases.append(f"Perteneces al pueblo {pueblo}." if pueblo and pueblo != "Otro" else "Perteneces a un pueblo indígena u originario.")
    g["Etnia"] = {1: "Pueblo indígena u originario", 2: "No pertenece a un pueblo indígena"}.get(f["p28_autoid_pueblo"])
    if f["p31_religion"] in RELIGION:
        frases.append(RELIGION[f["p31_religion"]] + ".")
    g["Religión"] = {1: "Católica", 2: "Evangélica", 12: "Ninguna"}.get(f["p31_religion"], "Otra" if valido(f["p31_religion"]) else None)
    return frases


def trabajo(f, e, g):
    frases = []
    nivel = nivel_educacional(f["cine11"], e["censo"])
    if nivel:
        escolaridad = f" ({f['escolaridad']} años de escolaridad)" if valido(f["escolaridad"]) else ""
        estudia = " y estudias actualmente" if f["p33_edu_asiste"] == 1 else ""
        frases.append(f"Tu nivel educacional es {minuscula(nivel)}{escolaridad}{estudia}.")
        g["Nivel educacional"] = "Superior" if 8 <= f["cine11"] <= 11 else "Media" if f["cine11"] in (6, 7) else "Básica o menos"
    colegio = COLEGIO.get(f.get("dependencia_colegio"))
    if colegio:
        frases.append(f"Vas a un colegio {colegio[0]}.")
        g["Tipo de colegio"] = colegio[1]

    frase, g["Situación laboral"] = situacion_laboral(f)
    if frase:
        frases.append(frase + ".")
    if f["sit_fuerza_trabajo"] == 1:
        oficio, rama = OCUPACION.get(f["cod_ciuo"]), RAMA.get(f["cod_caenes"])
        if oficio and rama:
            frases.append(f"Tu ocupación es de {oficio}, en el rubro de {rama}.")
        elif oficio or rama:
            frases.append(f"Tu ocupación es de {oficio}." if oficio else f"Trabajas en el rubro de {rama}.")
        if f["sindicato"] == 1:
            frases.append("Perteneces a un sindicato.")
        donde = {1: "en tu misma comuna", 2: "en tu misma comuna", 3: "en otra comuna", 4: "en otro país", 5: "en varias comunas"}.get(f["p44_lug_trab"])
        medio = e["censo"]["p45_medio_transporte"].get(f["p45_medio_transporte"]) if valido(f["p45_medio_transporte"]) else None
        minutos = f", y demoras unos {f['tiempo_traslado_min']} minutos" if valido(f["tiempo_traslado_min"]) and f["tiempo_traslado_min"] > 0 else ""
        if donde and medio:
            frases.append(f"Trabajas {donde}; para llegar usas: {minuscula(medio)}{minutos}.")
        elif donde:
            frases.append(f"Trabajas {donde}.")
        tipo = {1: "Privado", 2: "Público", 5: "Privado"}.get(f["p45_medio_transporte"], "Otro") if medio else None
        g["Tipo de transporte"] = tipo or "No se traslada a un trabajo"
    else:
        g["Tipo de transporte"] = "No se traslada a un trabajo"
    if f["cotiza_pension"] in (0, 1) and (f["edad"] >= 18 or f["sit_fuerza_trabajo"] == 1):
        frases.append("El mes pasado cotizaste para tu pensión." if f["cotiza_pension"] == 1 else "El mes pasado no cotizaste para tu pensión.")
    return frases


def menores_del_hogar(f):
    """(frase, grupo): los niños y adolescentes que viven en el hogar, con sus edades."""
    todos = list(f["edades_menores"] or [])
    if not todos:
        return "En tu hogar no viven menores de 18 años.", "Sin menores"
    grupo = "Con menores de 2 años" if todos[0] < 2 else "Con menores de 2 a 5 años" if todos[0] < 6 else "Con menores de 6 a 17 años"
    # Quien es menor de edad no se cuenta a sí mismo entre los menores con que vive.
    edades, propio = list(todos), f["edad"] < 18 and f["edad"] in todos
    if propio:
        edades.remove(f["edad"])
        if not edades:
            return "Eres la única persona menor de 18 años de tu hogar.", grupo
    cuantos = ("otro menor de 18 años" if propio else "un menor de 18 años") if len(edades) == 1 else f"{'otros ' if propio else ''}{len(edades)} menores de 18 años"
    anos = lista("menos de 1" if x == 0 else str(x) for x in edades)
    detalle = f"de {anos} {'año' if edades == [1] or edades == [0] else 'años'}"
    hijos = f["edades_hijos_jefatura"] or []
    # A las mujeres el censo les pregunta cuándo nació su último hijo, aunque no sean la jefatura.
    madre_reciente = f["sexo"] == 2 and (f["p48_anio_nac_uh"] or 0) >= ANIO_MENOR_DE_2 and edades[0] < 2
    if f["parentesco"] in JEFATURA_O_PAREJA and hijos == edades:
        quienes = "es tu hij@" if len(edades) == 1 else "son tus hijos"
    elif madre_reciente:
        quienes = "es tu hij@" if len(edades) == 1 else "el menor es tu hij@"
    else:
        quienes = None
    frase = f"En tu hogar vive {cuantos}, {detalle}" if len(edades) == 1 else f"En tu hogar viven {cuantos}, {detalle}"
    frase += f"; {quienes}." if quienes else "."
    return frase, grupo


def hogar(f, e, g):
    if f["id_hogar_muestra"] is None:
        g["Menores en el hogar"] = g["Tipo de hogar"] = "Sin dato"
        tipo = "una vivienda colectiva" if f["parentesco"] == 17 else "situación de calle" if f["parentesco"] == 19 else None
        return [f"Vives en {tipo}, no en un hogar particular."] if tipo else []
    frases = []
    n = f["integrantes"]
    tipo, rol = TIPO_HOGAR.get(f["tipologia_hogar"]), ROL.get(f["parentesco"])
    if n == 1:
        frases.append("Vives sol@.")
    else:
        frases.append(f"En tu hogar viven {n} personas contigo incluid@{'; ' + tipo if tipo else ''}{', y tú ' + rol if rol else ''}.")
    g["Tipo de hogar"] = e["censo"]["tipologia_hogar"].get(f["tipologia_hogar"]) if valido(f["tipologia_hogar"]) else None

    frase, g["Menores en el hogar"] = menores_del_hogar(f)
    if n > 1:
        frases.append(frase)
    otros_mayores = (f["mayores_65"] or 0) - (1 if f["edad"] >= 65 else 0)
    if otros_mayores > 0:
        frases.append("Vives con una persona de 65 años o más." if otros_mayores == 1 else f"Vives con {otros_mayores} personas de 65 años o más.")

    hijos = cantidad_hijos(f)
    if hijos is not None:
        frases.append("No tienes hijos." if hijos == 0 else "Tienes un@ hij@." if hijos == 1 else f"Tienes {hijos} hijos.")
        g["Hijos"] = "Sin hijos" if hijos == 0 else "Con hijos"
    padres = []
    for quien, vive, nivel in (("tu madre", f["vive_con_madre"], f["cine11_madre"]), ("tu padre", f["vive_con_padre"], f["cine11_padre"])):
        if vive:
            estudios = nivel_educacional(nivel, e["censo"])
            padres.append(quien + (f" (nivel educacional: {minuscula(estudios)})" if estudios else ""))
    hermanos = f["hermanos_en_hogar"] if valido(f["hermanos_en_hogar"]) else 0
    if hermanos:
        padres.append("un herman@" if hermanos == 1 else f"{hermanos} hermanos")
    if padres:
        frases.append(f"Vives con {lista(padres)}.")
    g["Vive con sus padres"] = "Sí" if f["vive_con_padre"] or f["vive_con_madre"] else "No"

    if f["es_cuidador"] == 1:
        frases.append("Cuidas a una persona de tu hogar que depende de otros para sus actividades diarias.")
    elif (f["dependientes"] or 0) - (1 if f["dependencia_grado"] in (1, 2, 3) else 0) > 0:
        frases.append("En tu hogar vive una persona que depende de otros para sus actividades diarias.")
    return frases


def vivienda(f, e, g):
    if f["id_hogar_muestra"] is None:
        return []
    frases = []
    tipo = {1: "una casa", 3: "un departamento"}.get(f["p2_tipo_vivienda"])
    if not tipo and valido(f["p2_tipo_vivienda"]):
        tipo = f"una vivienda de tipo «{minuscula(e['censo']['p2_tipo_vivienda'][f['p2_tipo_vivienda']])}»"
    tenencia = TENENCIA.get(f["p12_tenencia_viv"])
    if tipo:
        frases.append(f"Vives en {tipo}{', ' + tenencia if tenencia else ''}.")
    g["Tenencia de la vivienda"] = {1: "Propia", 2: "Propia", 3: "Arrendada", 4: "Arrendada"}.get(f["p12_tenencia_viv"], "Cedida u otra" if valido(f["p12_tenencia_viv"]) else None)
    if f["indice_hacinamiento"] in (2, 3):
        frases.append("En tu vivienda hay hacinamiento: duermen más de dos personas y media por dormitorio." if f["indice_hacinamiento"] == 2
                      else "En tu vivienda hay hacinamiento crítico: duermen cinco o más personas por dormitorio.")
    equipo = [nombre for columna, nombre in (("p15d_serv_internet_fija", "internet fija"), ("p15e_serv_internet_movil", "internet móvil"), ("p15b_serv_compu", "computador")) if f[columna] == 1]
    falta = [nombre for columna, nombre in (("p15d_serv_internet_fija", "internet fija"), ("p15e_serv_internet_movil", "internet móvil"), ("p15b_serv_compu", "computador")) if f[columna] == 2]
    if equipo or falta:
        frases.append("En tu hogar " + lista(([f"hay {lista(equipo)}"] if equipo else []) + ([f"no hay {lista(falta).replace(' y ', ' ni ')}"] if falta else [])) + ".")
    if f["tiene_vehiculo"] in (1, 2):
        frases.append("Tu hogar tiene vehículo." if f["tiene_vehiculo"] == 1 else "Tu hogar no tiene vehículo.")
    return frases


def economia(f, e, g, con_cep):
    frases = []
    decil = f["decil_ingreso"]
    if valido(decil):
        tramo = ("entre los de menores ingresos del país" if decil <= 2 else "bajo la mitad de los hogares del país" if decil <= 4
                 else "cerca de la mitad de los hogares del país" if decil <= 6 else "sobre la mitad de los hogares del país" if decil <= 8
                 else "entre los de mayores ingresos del país")
        pesos = f"{round(f['ingreso_total_pc'], -4):,.0f}".replace(",", ".") if valido(f["ingreso_total_pc"]) else None
        monto = f", con unos ${pesos} al mes por persona" if pesos else ""
        frases.append(f"Por ingresos, tu hogar está {tramo} (decil {decil} de 10){monto}.")
        g["Tramo socioeconómico"] = f"Quintil {f['quintil_ingreso']}"
    if f["pobreza_ingresos"] in (1, 2):
        frases.append("Tu hogar está en situación de pobreza extrema por ingresos." if f["pobreza_ingresos"] == 1 else "Tu hogar está en situación de pobreza por ingresos.")
    if valido(f["inseg_alim_n"]) and f["inseg_alim_n"] > 0:
        grado = "alguna vez" if f["inseg_alim_n"] <= 2 else "varias veces" if f["inseg_alim_n"] <= 5 else "con frecuencia"
        frases.append(f"En el último año, en tu hogar {grado} faltó dinero para comer lo suficiente o de forma variada.")
    if not con_cep:
        return frases
    alcanza = {1: "les alcanza bien y pueden ahorrar", 2: "les alcanza justo, sin grandes dificultades",
               3: "no les alcanza y tienen algunas dificultades", 4: "no les alcanza y tienen grandes dificultades"}.get(f.get("ingresos_alcanzan"))
    if alcanza:
        frases.append(f"Sientes que, con los ingresos de tu familia, {alcanza}.")
    actual = {1: "muy mala", 2: "mala", 3: "ni buena ni mala", 4: "buena", 5: "muy buena"}.get(f.get("economia_personal"))
    futuro = {1: "mucho mejor", 2: "mejor", 3: "igual", 4: "peor", 5: "mucho peor"}.get(f.get("economia_personal_futuro"))
    if actual:
        frases.append(f"Calificas tu situación económica como {actual}" + (f" y crees que en un año estará {futuro}." if futuro else "."))
    preocupa = [nombre for columna, nombre in (("preocupa_deudas", "pagar tus deudas"), ("preocupa_enfermedad", "enfrentar una enfermedad grave sin poder pagarla"),
                                               ("preocupa_pension", "tener una pensión adecuada en la vejez")) if (f.get(columna) or 0) >= 8]
    if preocupa:
        frases.append(f"Te preocupa mucho {lista(preocupa)}.")
    clase = f.get("clase_subjetiva")
    if valido(clase) and clase > 0:
        frases.append(f"En una escala social de 1 (lo más bajo) a 10 (lo más alto), te ubicas en el {clase}.")
    return frases


def salud_redes(f, e, g):
    frases = []
    casen = e["casen"]
    if f["prevision_salud"] == 1:
        grupo = casen["fonasa_grupo"].get(f["fonasa_grupo"]) if valido(f["fonasa_grupo"]) else None
        frases.append(f"En salud estás en Fonasa{', ' + minuscula(grupo) if grupo else ''}.")
        g["Previsión de salud"] = "Fonasa A o B" if f["fonasa_grupo"] in (1, 2) else "Fonasa C o D" if f["fonasa_grupo"] in (3, 4) else "Fonasa sin grupo"
    elif valido(f["prevision_salud"]):
        frases.append({2: "En salud estás en una isapre.", 3: "En salud estás en el sistema de las Fuerzas Armadas y de Orden.",
                       4: "No tienes previsión de salud: te atiendes como particular."}.get(f["prevision_salud"], "En salud estás en otro sistema."))
        g["Previsión de salud"] = "Isapre" if f["prevision_salud"] == 2 else "Otra o ninguna"
    if f["dependencia_grado"] in (1, 2, 3):
        frases.append("Necesitas ayuda de otra persona para tus actividades diarias.")
    elif f["discapacidad"] == 1:
        frases.append("Tienes una discapacidad.")

    conoce = {1: True, 2: True, 3: True, 4: False}
    redes = [(nombre, conoce.get(f[columna])) for columna, nombre in (("red_dinero", "prestarte dinero"), ("red_trabajo", "ayudarte a conseguir trabajo"),
                                                                      ("red_cuidado_enfermedad", "cuidarte si te enfermas"))]
    si, no = [n for n, c in redes if c is True], [n for n, c in redes if c is False]
    if si:
        frases.append(f"Si lo necesitaras, conoces a alguien que podría {lista(si)}.")
    if no:
        frases.append(f"No conoces a nadie que pudiera {lista(no).replace(' y ', ' ni ')}.")
    organizacion = f["participa_organizacion"]
    if organizacion == 15:
        frases.append("No participas en ninguna organización o grupo.")
    elif valido(organizacion) and organizacion in casen["participa_organizacion"]:
        nombre = re.sub(r"\s*\(.*\)$", "", casen["participa_organizacion"][organizacion])
        frases.append("Participas en una organización." if organizacion == 14 else f"Participas en: {minuscula(nombre)}.")
    motivos = [nombre for columna, nombre in DISCRIMINACION.items() if f.get(f"discrim_{columna}") == 1]
    if motivos:
        frases.append(f"En el último año alguien de tu hogar fue discriminado por {lista(motivos[:4])}.")
    return frases


# ---------------------------------------------------------------- secciones de la Encuesta CEP


def politica(f, e, g):
    """Los códigos -8 (no sabe) y -9 (no contesta) se omiten, salvo en la posición política,
    donde no ubicarse es en sí una respuesta."""
    frases = []
    posicion = f["posicion_politica"]
    if posicion > 0:
        nombre = ["izquierda", "centroizquierda", "centro", "centroderecha", "derecha"][(posicion - 1) // 2]
        frases.append(f"Te ubicas en {'el' if nombre == 'centro' else 'la'} {nombre} ({posicion} en una escala de 1, izquierda, a 10, derecha).")
        g["Posición política"] = "Izquierda (1 a 4)" if posicion <= 4 else "Centro (5 y 6)" if posicion <= 6 else "Derecha (7 a 10)"
    else:
        frases.append("No te ubicas en la izquierda ni en la derecha.")
        g["Posición política"] = "No se ubica"
    partido = f["partido"]
    if partido == 15:
        frases.append("No te identificas con ningún partido político.")
    elif partido == 14:
        frases.append("Simpatizas con un partido pequeño.")
    elif e["cep"].get("partido", {}).get(partido) and partido > 0:
        nombre = e["cep"]["partido"][partido]
        frases.append(f"Simpatizas con {'el ' if nombre.startswith(('Partido', 'Frente')) else ''}{nombre}.")

    tu = {1: "Apruebas", 2: "Desapruebas", 3: "Ni apruebas ni desapruebas"}
    g["Evaluación del gobierno"] = {1: "Aprueba", 2: "Desaprueba", 3: "Ni aprueba ni desaprueba"}.get(f["aprueba_gobierno"], "Sin respuesta")
    if f["aprueba_gobierno"] in tu:
        frases.append(f"{tu[f['aprueba_gobierno']]} la forma en que {PRESIDENTE} conduce el gobierno.")
    if f["aprueba_gobierno_anterior"] in tu:
        frases.append(f"{tu[f['aprueba_gobierno_anterior']]} la forma en que {ANTERIOR} condujo el gobierno anterior.")
    voto = {1: "votaste por Jeannette Jara", 2: "votaste por José Antonio Kast", 3: "votaste en blanco", 4: "anulaste tu voto"}.get(f["voto_segunda_vuelta_2025"])
    g["Voto en 2025"] = {1: "Jara", 2: "Kast", 3: "Blanco o nulo", 4: "Blanco o nulo"}.get(f["voto_segunda_vuelta_2025"], "No votó o no responde")
    if voto:
        frases.append(f"En la segunda vuelta presidencial de 2025 {voto}.")
    elif f["voto_segunda_vuelta_2025"] is None:
        frases.append("No votaste en la segunda vuelta presidencial de 2025.")
    if f["votaria_voluntario"] in (1, 2):
        frases.append("Habrías ido a votar aunque no fuera obligatorio." if f["votaria_voluntario"] == 1 else "No habrías ido a votar si no fuera obligatorio.")
    interes = {1: "te interesa mucho", 2: "te interesa bastante", 3: "te interesa algo", 4: "te interesa poco", 5: "no te interesa nada"}.get(f["interes_politica"])
    fuente = {1: "las redes sociales", 2: "la televisión", 3: "los diarios", 4: "la radio y los podcasts", 5: "sitios web"}.get(f["fuente_noticias"])
    if interes:
        frases.append(f"La política {interes}" + (f"; te informas sobre todo por {fuente}." if fuente else "."))
    democracia = {1: "la democracia siempre es preferible a cualquier otra forma de gobierno", 2: "a veces un régimen autoritario puede ser preferible",
                  3: "a la gente como tú le da lo mismo un régimen democrático que uno autoritario"}.get(f["apoyo_democracia"])
    funciona = {1: "muy mal", 2: "mal", 3: "regular", 4: "bien", 5: "muy bien"}.get(f["funciona_democracia"])
    if democracia:
        frases.append(f"Piensas que {democracia}" + (f", y que en Chile la democracia funciona {funciona}." if funciona else "."))
    return frases


def acuerdo(valor, afirmacion):
    """Frase para una escala de 1 (muy de acuerdo) a 5 (muy en desacuerdo); None en el punto medio o sin respuesta."""
    inicio = {1: "Estás muy de acuerdo con que", 2: "Estás de acuerdo con que", 4: "Estás en desacuerdo con que", 5: "Estás muy en desacuerdo con que"}.get(valor)
    return f"{inicio} {afirmacion}." if inicio else None


def pais(f, e, g):
    frases = []
    cep = e["cep"]
    problemas = [minuscula(cep["problema_1"][f[c]]) for c in ("problema_1", "problema_2", "problema_3") if valido(f[c]) and f[c] in cep.get("problema_1", {})]
    if problemas:
        # Algunas etiquetas traen comas ("alzas de precios, inflación"): se separan con punto y coma.
        frases.append(f"Para ti, los problemas a los que el gobierno debería dedicar más esfuerzo son: {'; '.join(problemas)}.")
    rumbo = {1: "está progresando", 2: "está estancado", 3: "está en decadencia"}.get(f["rumbo_pais"])
    if rumbo:
        frases.append(f"Crees que Chile {rumbo}.")
    calidad = {1: "muy mala", 2: "mala", 3: "ni buena ni mala", 4: "buena", 5: "muy buena"}
    economia_pais = calidad.get(f["economia_pais"])
    futuro = {1: "mejorará", 2: "no cambiará", 3: "empeorará"}.get(f["economia_pais_futuro"])
    if economia_pais:
        frases.append(f"Calificas la situación económica del país como {economia_pais}" + (f" y crees que en un año {futuro}." if futuro else "."))
    situacion = {1: "muy buena", 2: "buena", 3: "ni buena ni mala", 4: "mala", 5: "muy mala"}.get(f["situacion_politica"])
    if situacion:
        frases.append(f"Calificas la situación política como {situacion}.")

    sustento = f["responsabilidad_sustento"]
    if valido(sustento) and sustento > 0:
        quien = "sobre todo del Estado" if sustento <= 3 else "compartida entre el Estado y las personas" if sustento <= 7 else "sobre todo de cada persona"
        frases.append(f"Crees que el sustento económico de las personas es una responsabilidad {quien}.")
    frases += [x for x in (
        acuerdo(f["menos_estado_economia"], "el país estará mejor mientras menos participe el Estado en la economía"),
        acuerdo(f["estado_burocracia"], "la intervención del Estado lleva a demasiada burocracia y muchos problemas"),
        acuerdo(f["reducir_gasto_publico"], "el gobierno reduzca el gasto público para mejorar las finanzas del Estado"),
    ) if x]
    empleados = {1: "demasiado alto", 2: "alto", 3: "adecuado", 4: "bajo", 5: "demasiado bajo"}.get(f["empleados_publicos"])
    if empleados:
        frases.append(f"Te parece que el número de empleados públicos es {empleados}.")

    orden = f["libertades_o_seguridad"]
    if valido(orden):
        postura = ("hay que garantizar las libertades aunque eso dificulte controlar la delincuencia" if orden <= 3
                   else "hay que equilibrar las libertades y el control de la delincuencia" if orden <= 6
                   else "se pueden restringir libertades para controlar la delincuencia")
        frases.append(f"Crees que {postura} ({orden} en una escala de 0 a 10).")
    causa = cep.get("causa_delincuencia", {}).get(f["causa_delincuencia"]) if valido(f["causa_delincuencia"]) and f["causa_delincuencia"] != 12 else None
    if causa:
        frases.append(f"Para ti, la principal causa de la delincuencia: {minuscula(causa)}.")
    cuando = {1: "Siempre", 2: "Casi siempre", 3: "A veces", 4: "Casi nunca", 5: "Nunca"}
    if f["justifica_marchas"] in cuando:
        frases.append(f"{cuando[f['justifica_marchas']]} justificas que la gente marche para protestar.")
    if f["justifica_fuerza_carabineros"] in cuando:
        frases.append(f"{cuando[f['justifica_fuerza_carabineros']]} justificas que Carabineros use la fuerza contra un manifestante violento.")

    inmigracion = f["apertura_inmigracion"]
    if valido(inmigracion) and inmigracion > 0:
        postura = "restringir fuertemente" if inmigracion <= 3 else "permitir con límites" if inmigracion <= 7 else "permitir con amplitud"
        frases.append(f"Sobre la inmigración, prefieres {postura} la llegada de extranjeros ({inmigracion} en una escala de 1, prohibirla, a 10, permitirla libremente).")
    frases += [x for x in (
        acuerdo(f["inmigrantes_criminalidad"], "los inmigrantes elevan los índices de criminalidad"),
        acuerdo(f["inmigrantes_aporte"], "los inmigrantes son un aporte para la economía de Chile"),
    ) if x]

    ideal = f["hijos_ideal"]
    if valido(ideal) and ideal <= 8:
        frases.append("Tu número ideal de hijos es ninguno." if ideal == 0 else f"Tu número ideal de hijos es {ideal}.")
    # Estas dos escalas van al revés: 1 es muy en desacuerdo y 5 es muy de acuerdo.
    al_reves = {1: 5, 2: 4, 4: 2, 5: 1}
    frases += [x for x in (
        acuerdo(al_reves.get(f["hijos_restringen_carrera"]), "tener hijos restringe las posibilidades de trabajo y carrera de los padres"),
        acuerdo(al_reves.get(f["hijos_carga_financiera"]), "los hijos son una carga financiera para sus padres"),
    ) if x]
    return frases


def confianza(f, e, g):
    niveles = {1: [], 2: [], 3: [], 4: []}
    for columna, nombre in INSTITUCIONES.items():
        if f[columna] in niveles:
            niveles[f[columna]].append(nombre)
    g["Confianza en el gobierno"] = {1: "Mucha o bastante", 2: "Mucha o bastante", 3: "Poca o nada", 4: "Poca o nada"}.get(f["confianza_gobierno"], "Sin respuesta")
    textos = {1: "Tienes mucha confianza en", 2: "Tienes bastante confianza en", 3: "Tienes poca confianza en", 4: "No tienes ninguna confianza en"}
    return [f"{textos[n]} {lista(nombres)}." for n, nombres in niveles.items() if nombres]


def personalidad(id_persona, semilla):
    """Capa sorteada: una frase en segunda persona. Los rasgos en el promedio no se mencionan."""
    rng = random.Random(f"personalidad-{semilla}-{id_persona}")
    partes = []
    for bajo, alto in BIG_FIVE.values():
        t = min(80, max(20, rng.gauss(50, 10)))
        if not 45 <= t < 55:
            texto = bajo if t < 45 else alto
            partes.append(f"muy marcadamente, {texto}" if t < 35 or t >= 65 else texto)
    return [f"{minuscula(lista(partes)).capitalize()}."] if partes else []


def datos_sueltos(f, etiquetas, g):
    """Lo mínimo en forma de dato, para filtrar y dibujar sin leer el texto del perfil."""
    return {
        "edad": f["edad"],
        "genero": g.get("Género"),
        "region": f["region"],
        "nombre_region": g.get("Región"),
        "comuna": etiquetas["territorios"].get(("comuna", f["comuna"])),
        "zona": g.get("Zona"),
        "quintil": f["quintil_ingreso"] if valido(f["quintil_ingreso"]) else None,
        "educacion": g.get("Nivel educacional"),
    }


def describir(f, etiquetas, secciones, con_cep, semilla_personalidad=None):
    """Devuelve (perfil por secciones, grupos para el informe) de una fila de la muestra."""
    fem = femenino(f)
    final = lambda texto: texto.replace("@", "o/a" if fem is None else "a" if fem else "o")
    g, perfil = {}, {}
    armar = {
        "identidad": lambda: identidad(f, etiquetas, g),
        "trabajo": lambda: trabajo(f, etiquetas, g),
        "hogar": lambda: hogar(f, etiquetas, g),
        "vivienda": lambda: vivienda(f, etiquetas, g),
        "economia": lambda: economia(f, etiquetas, g, con_cep),
        "salud_redes": lambda: salud_redes(f, etiquetas, g),
        "politica": lambda: politica(f, etiquetas, g),
        "pais": lambda: pais(f, etiquetas, g),
        "confianza": lambda: confianza(f, etiquetas, g),
    }
    for clave, titulo in SECCIONES.items():
        if clave in SOLO_CEP and (not con_cep or f.get("posicion_politica") is None):
            continue
        # Los grupos se calculan siempre; el texto, solo para las secciones pedidas.
        frases = armar[clave]()
        if clave in secciones and frases:
            perfil[titulo] = final(" ".join(frases))
    if semilla_personalidad is not None:
        frases = personalidad(f["id_persona_muestra"], semilla_personalidad)
        if frases:
            perfil["Tu forma de ser"] = final(" ".join(frases))
    return perfil, {clave: valor for clave, valor in g.items() if valor}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("muestra", type=Path)
    ap.add_argument("salida", type=Path)
    ap.add_argument("n", type=int, nargs="?", default=200)
    ap.add_argument("semilla", type=int, nargs="?", default=1)
    ap.add_argument("--por-region", type=int, metavar="K")
    ap.add_argument("--edad-minima", type=int, default=14)
    ap.add_argument("--secciones", default=",".join(SECCIONES))
    ap.add_argument("--sin-actitudes", action="store_true")
    ap.add_argument("--personalidad", action="store_true")
    args = ap.parse_args()
    secciones = [s.strip() for s in args.secciones.split(",")]
    if set(secciones) - set(SECCIONES):
        ap.error(f"secciones desconocidas: {sorted(set(secciones) - set(SECCIONES))}; las que hay son {', '.join(SECCIONES)}")

    etiquetas = cargar_etiquetas()
    filtro = "WHERE lugar_en_region <= $k ORDER BY region, orden" if args.por_region else "ORDER BY orden LIMIT $k"
    ruta_actitudes = args.muestra.parent / "actitudes.parquet"
    con = duckdb.connect()
    # La tabla de la población completa ya trae las opiniones y la composición del hogar; la muestra, no.
    columnas_tabla = {c[0] for c in con.execute("describe select * from read_parquet($m)", {"m": str(args.muestra)}).fetchall()}
    ya_incluidas = "posicion_politica" in columnas_tabla
    con_cep = (ya_incluidas or ruta_actitudes.exists()) and not args.sin_actitudes
    parametros = {"muestra": str(args.muestra), "semilla": args.semilla, "k": args.por_region or args.n, "edad_minima": args.edad_minima}
    if "edades_menores" in columnas_tabla:
        del_hogar = dict(composicion="", del_hogar=", n_personas AS integrantes", union_hogar="")
    else:
        del_hogar = dict(composicion=COMPOSICION, del_hogar=", hogar.* EXCLUDE (id_hogar_muestra)", union_hogar="LEFT JOIN hogar USING (id_hogar_muestra)")
    if con_cep and not ya_incluidas:
        consulta = CONSULTA.format(actitudes=", actitud.* EXCLUDE (id_persona_muestra)", union="LEFT JOIN read_parquet($actitudes) AS actitud USING (id_persona_muestra)", **del_hogar)
        parametros["actitudes"] = str(ruta_actitudes)
    else:
        consulta = CONSULTA.format(actitudes="", union="", **del_hogar)
    resultado = con.execute(consulta + filtro, parametros)
    columnas = [c[0] for c in resultado.description]
    filas = [dict(zip(columnas, fila)) for fila in resultado.fetchall()]

    # Peso para cifras nacionales: adultos de la región por cada persona elegida, con media 1.
    elegidas = {}
    for fila in filas:
        elegidas[fila["region"]] = elegidas.get(fila["region"], 0) + 1
    crudos = [fila["adultos_region"] / elegidas[fila["region"]] if args.por_region else 1 for fila in filas]
    media = sum(crudos) / len(crudos)

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    largo = 0
    with open(args.salida, "w", encoding="utf-8") as f:
        for fila, crudo in zip(filas, crudos):
            perfil, grupos = describir(fila, etiquetas, secciones, con_cep, args.semilla if args.personalidad else None)
            largo += sum(len(titulo) + len(texto) + 3 for titulo, texto in perfil.items())
            persona = {"id": f"m{fila['id_persona_muestra']}", "perfil": perfil, "grupos": grupos,
                       "datos": datos_sueltos(fila, etiquetas, grupos), "peso": round(crudo / media, 4)}
            f.write(json.dumps(persona, ensure_ascii=False) + "\n")
    forma = f"{args.por_region} por región" if args.por_region else "al azar"
    capa = "con opiniones de la CEP" if con_cep else "sin opiniones de la CEP"
    capa += ", con personalidad sorteada" if args.personalidad else ""
    print(f"{len(filas)} personas en {args.salida} ({forma}, semilla {args.semilla}, {capa})")
    print(f"Perfil medio: {largo / len(filas):.0f} caracteres, unos {largo / len(filas) / 3.6:.0f} tokens")


if __name__ == "__main__":
    main()
