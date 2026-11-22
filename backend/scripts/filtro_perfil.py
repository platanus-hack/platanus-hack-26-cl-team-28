#!/usr/bin/env python3
"""Qué datos del perfil de una persona se le entregan al modelo para que responda.

Uso:
    uv run python -I scripts/filtro_perfil.py                  # el catálogo, el núcleo y los temas
    uv run python -I scripts/filtro_perfil.py TEXTO.md [...]   # qué temas detecta en cada texto y qué datos irían

El perfil completo (scripts/personas_muestra.py) trae cerca de cien datos por persona y unos
1.100 tokens. La mayoría casi no mueve una respuesta sobre una política: en la Encuesta CEP,
la demografía sola explica 4 % de las opiniones y los datos del núcleo, 16 % de un máximo de
19 % (ver contexto/metodo/influencia.md, que escribe scripts/analizar_influencia.py). Este
archivo define el recorte y es el único lugar donde se cambia.

Hay tres niveles:
  completo   todo, como antes. Es `None` en el código: sin filtro.
  nucleo     lo que se entrega siempre: quién es la persona, su posición política y su
             mirada del Estado. Unos 390 tokens.
  tematico   el núcleo más los datos de los temas que toca el texto de la política (hasta
             MAX_TEMAS). Si el texto habla de pensiones, van la cotización y la confianza en
             el sistema de pensiones; si no, no.

El tema se detecta por palabras clave, sin modelo: es instantáneo, no gasta y da siempre lo
mismo para el mismo texto, así que la caché de respuestas sigue sirviendo. Los temas son las
áreas de datos-pruebas/encuestas/ más pueblos originarios.

Cada dato tiene una clave. Las frases del perfil se escriben solo si su clave está en el
conjunto pedido (el argumento `datos` de `describir` en personas_muestra.py). Un dato que no
está en el núcleo ni en ningún tema solo va en el perfil completo.

Solo usa la biblioteca estándar: el servidor lo importa aunque no haya DuckDB.
"""

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

NIVELES = ("completo", "nucleo", "tematico")
MAX_TEMAS = 3

# Clave de cada dato -> sección del perfil en que se escribe (las de SECCIONES en personas_muestra.py).
DATOS = {
    # Quién eres
    "edad": "identidad", "genero": "identidad", "lugar": "identidad",
    "nacionalidad_chilena": "identidad", "nacionalidad_otra": "identidad",
    "nacimiento_chile": "identidad", "nacimiento_extranjero": "identidad", "residencia_anterior": "identidad",
    "estado_civil": "identidad", "pueblo_originario": "identidad", "religion": "identidad",
    # Educación y trabajo
    "educacion": "trabajo", "escolaridad": "trabajo", "estudia": "trabajo", "colegio": "trabajo",
    "situacion_laboral": "trabajo", "ocupacion": "trabajo", "rubro": "trabajo", "sindicato": "trabajo",
    "lugar_trabajo": "trabajo", "medio_transporte": "trabajo", "tiempo_traslado": "trabajo", "cotiza_pension": "trabajo",
    # Tu hogar
    "integrantes": "hogar", "tipo_hogar": "hogar", "rol_hogar": "hogar", "menores_hogar": "hogar", "mayores_hogar": "hogar",
    "hijos": "hogar", "vive_con_padres": "hogar", "educacion_padres": "hogar", "hermanos": "hogar", "cuidados": "hogar",
    # Tu vivienda
    "tipo_vivienda": "vivienda", "tenencia": "vivienda", "hacinamiento": "vivienda", "conectividad": "vivienda", "vehiculo": "vivienda",
    # Tu situación económica
    "decil": "economia", "ingreso_pc": "economia", "pobreza": "economia", "inseguridad_alimentaria": "economia",
    "ingresos_alcanzan": "economia", "economia_personal": "economia", "economia_personal_futuro": "economia",
    "preocupa_deudas": "economia", "preocupa_enfermedad": "economia", "preocupa_pension": "economia", "clase_subjetiva": "economia",
    # Salud, redes y participación
    "prevision_salud": "salud_redes", "discapacidad": "salud_redes", "red_dinero": "salud_redes", "red_trabajo": "salud_redes",
    "red_cuidado": "salud_redes", "organizacion": "salud_redes", "discriminacion": "salud_redes",
    # Tu posición política
    "posicion_politica": "politica", "partido": "politica", "sin_partido": "politica", "aprueba_gobierno": "politica",
    "aprueba_gobierno_anterior": "politica", "voto_2025": "politica", "votaria_voluntario": "politica",
    "interes_politica": "politica", "fuente_noticias": "politica", "apoyo_democracia": "politica", "funciona_democracia": "politica",
    # Cómo ves el país
    "problemas": "pais", "rumbo_pais": "pais", "economia_pais": "pais", "economia_pais_futuro": "pais", "situacion_politica": "pais",
    "responsabilidad_sustento": "pais", "menos_estado": "pais", "estado_burocracia": "pais", "reducir_gasto": "pais",
    "empleados_publicos": "pais", "libertades_seguridad": "pais", "causa_delincuencia": "pais", "justifica_marchas": "pais",
    "justifica_fuerza": "pais", "apertura_inmigracion": "pais", "inmigrantes_criminalidad": "pais", "inmigrantes_aporte": "pais",
    "hijos_ideal": "pais", "hijos_carrera": "pais", "hijos_carga": "pais",
    # Tu confianza en las instituciones (la clave es la columna de la tabla)
    "confianza_gobierno": "confianza", "confianza_congreso": "confianza", "confianza_partidos": "confianza",
    "confianza_tribunales": "confianza", "confianza_municipalidades": "confianza", "confianza_carabineros": "confianza",
    "confianza_fuerzas_armadas": "confianza", "confianza_empresas": "confianza", "confianza_sindicatos": "confianza",
    "confianza_sistema_salud": "confianza", "confianza_sistema_pensiones": "confianza", "confianza_television": "confianza",
    "confianza_redes_sociales": "confianza", "confianza_iglesia_catolica": "confianza", "confianza_universidades": "confianza",
}

# Lo que va siempre. Es lo que más predice una opinión política (posición, voto, evaluación de los
# gobiernos, confianza en el gobierno, rol del Estado) más lo mínimo para saber quién es la persona
# y si una medida la toca: edad, trabajo, hogar con niños e ingreso.
# `menos_estado` predice poco en la CEP, pero el modelo lo usa: sin él, la distancia entre quienes
# quieren menos Estado y el resto baja a la mitad (ver «Perfil filtrado contra perfil completo»
# en servidor/README.md).
NUCLEO = frozenset({
    "edad", "genero", "lugar", "nacionalidad_otra", "religion",
    "educacion", "colegio", "situacion_laboral",
    "integrantes", "tipo_hogar", "rol_hogar", "menores_hogar", "hijos",
    "decil", "pobreza",
    "posicion_politica", "partido", "aprueba_gobierno", "aprueba_gobierno_anterior", "voto_2025", "interes_politica",
    "problemas", "rumbo_pais", "responsabilidad_sustento", "reducir_gasto", "menos_estado",
    "confianza_gobierno", "confianza_congreso",
})

# Tema -> palabras que lo delatan en el texto y datos que agrega. Las palabras van sin tildes y
# en minúsculas; cada una calza desde el inicio de una palabra del texto ("pension" calza con
# "pensiones" y "pensionados"). Con "=" adelante calza solo la palabra exacta: "=bus" no calza
# con "buscar" ni "=metro" con "metropolitana".
TEMAS = {
    "trabajo": {
        "palabras": ["trabaj", "emple", "sueld", "salari", "contrat", "sindic", "jornada", "laboral", "despid", "cesant",
                     "teletrabajo", "40 horas", "horas semanales", "sala cuna", "licencia medica", "finiquito", "pyme"],
        "datos": ["ocupacion", "rubro", "sindicato", "cotiza_pension", "red_trabajo", "confianza_empresas", "confianza_sindicatos"],
    },
    "familia-derechos": {
        "palabras": ["famili", "hijo", "hija", "nino", "nina", "ninez", "infancia", "guagua", "sala cuna", "jardin infantil", "cuidador",
                     "cuidados", "cuidado infantil", "cuidado de", "postnatal", "prenatal", "maternidad", "paternidad", "madre", "padre", "adopcion", "adoptar", "matrimonio",
                     "casarse", "parejas del mismo sexo", "homosexual", "lgbt", "identidad de genero", "divorcio", "pension de alimentos",
                     "labores del hogar", "natalidad", "embaraz", "gestar", "geste"],
        "datos": ["estado_civil", "mayores_hogar", "vive_con_padres", "cuidados", "hijos_ideal", "hijos_carrera", "hijos_carga"],
    },
    "pensiones": {
        "palabras": ["pension", "jubil", "=afp", "cotizacion", "prevision", "=pgu", "vejez", "adulto mayor", "adultos mayores",
                     "tercera edad", "ahorro previsional", "ahorros previsionales", "administradora", "reparto"],
        "datos": ["cotiza_pension", "preocupa_pension", "mayores_hogar", "confianza_sistema_pensiones"],
    },
    "salud": {
        "palabras": ["salud", "hospital", "consultorio", "cesfam", "fonasa", "isapre", "medico", "medica", "medicamento", "medicina", "enfermedad", "enfermo", "lista de espera",
                     "listas de espera", "paciente", "vacuna", "aborto", "abortar", "eutanasia", "discapacidad", "cannabis", "farmac",
                     "remedio", "pubertad", "salud mental"],
        "datos": ["prevision_salud", "discapacidad", "cuidados", "preocupa_enfermedad", "red_cuidado", "confianza_sistema_salud"],
    },
    "vivienda": {
        "palabras": ["vivienda", "arriendo", "arrend", "hipotec", "dividendo", "subsidio habitacional", "campamento", "toma de terreno",
                     "allegad", "contribuciones", "inmobiliari", "casa propia", "deficit habitacional", "reconstru"],
        "datos": ["tipo_vivienda", "tenencia", "hacinamiento"],
    },
    "transporte": {
        "palabras": ["transporte", "locomocion", "=metro", "=micro", "=micros", "=bus", "=buses", "pasaje", "tarifa", "=tag", "peaje",
                     "autopista", "carretera", "bencina", "diesel", "combustible", "=auto", "=autos", "automovil", "vehiculo", "camioner",
                     "ciclovia", "patente", "permiso de circulacion", "congestion", "=taco", "=tacos", "=tren", "=trenes"],
        "datos": ["lugar_trabajo", "medio_transporte", "tiempo_traslado", "vehiculo"],
    },
    "migracion": {
        "palabras": ["migra", "inmigra", "extranjer", "frontera", "expuls", "deportar", "deportac", "refugiad", "remesa", "=visa", "=visas", "regulariz",
                     "nacionalidad", "clandestin"],
        "datos": ["nacionalidad_chilena", "nacimiento_extranjero", "apertura_inmigracion", "inmigrantes_criminalidad", "inmigrantes_aporte"],
    },
    "seguridad-justicia": {
        "palabras": ["seguridad", "delincuen", "delito", "crimen", "criminal", "narco", "droga", "carcel", "carabiner", "policia", "=pdi",
                     "condena", "=pena", "=penas", "penal", "justicia", "tribunal", "fiscalia", "gendarmeria", "estado de excepcion", "toque de queda",
                     "terroris", "violencia", "=robo", "=robos", "asalto", "orden publico", "militar", "=arma", "=armas", "barricada", "saqueo", "protesta",
                     "manifestacion"],
        "datos": ["libertades_seguridad", "causa_delincuencia", "justifica_marchas", "justifica_fuerza",
                  "confianza_carabineros", "confianza_fuerzas_armadas", "confianza_tribunales"],
    },
    "economia-impuestos": {
        "palabras": ["impuesto", "tribut", "=iva", "gasto publico", "gasto fiscal", "deuda publica", "situacion fiscal", "deficit fiscal",
                     "presupuesto", "inflacion", "alza de precios", "costo de la vida", "crecimiento", "inversion", "royalty", "burocracia",
                     "privatiz", "subsidio", "=bono", "=bonos", "finanzas publicas", "economia", "propiedad", "recaud", "sueldo minimo",
                     "deudor", "deudas"],
        "datos": ["ingreso_pc", "ingresos_alcanzan", "economia_personal", "preocupa_deudas", "economia_pais", "economia_pais_futuro",
                  "menos_estado", "estado_burocracia", "empleados_publicos", "confianza_empresas"],
    },
    "educacion": {
        "palabras": ["educaci", "colegio", "escuela", "liceo", "universi", "estudiant", "alumn", "profesor", "docente", "=cae", "gratuidad",
                     "beca", "matricula", "simce", "=paes", "sala de clases", "jardin infantil", "admision escolar", "parvul"],
        "datos": ["escolaridad", "estudia", "vive_con_padres", "educacion_padres", "confianza_universidades"],
    },
    "regulacion-digital": {
        "palabras": ["internet", "redes sociales", "red social", "plataforma", "digital", "celular", "apuesta", "casino", "en linea",
                     "online", "datos personales", "inteligencia artificial", "aplicaciones moviles", "=app", "=apps", "ciberseguridad", "pantalla",
                     "television", "noticias falsas", "desinformacion", "conectividad", "fibra optica"],
        "datos": ["conectividad", "fuente_noticias", "confianza_television", "confianza_redes_sociales"],
    },
    "instituciones-elecciones": {
        "palabras": ["constituci", "congreso", "diputad", "senador", "parlament", "partido", "eleccion", "=voto", "=votos", "votar", "plebiscito",
                     "democra", "presidencial", "mandato", "reeleccion", "sistema politico", "corrupcion", "municip", "alcalde",
                     "gobernador", "cargos electivos", "candidat"],
        "datos": ["sin_partido", "votaria_voluntario", "apoyo_democracia", "funciona_democracia", "situacion_politica",
                  "confianza_partidos", "confianza_tribunales", "confianza_municipalidades"],
    },
    "bienestar-servicios": {
        "palabras": ["pobreza", "vulnerab", "hambre", "alimentacion", "canasta", "tramite", "servicio publico", "servicios administrativos",
                     "servicios publicos", "municipalidad", "junta de vecinos", "organizacion vecinal", "organizaciones vecinales",
                     "discrimina", "ayuda social", "registro social", "satisfaccion", "calidad de vida", "soledad"],
        "datos": ["inseguridad_alimentaria", "red_dinero", "red_cuidado", "organizacion", "discriminacion", "confianza_municipalidades"],
    },
    "medio-ambiente": {
        "palabras": ["ambient", "contamina", "clima", "calentamiento global", "emision", "=lena", "calefaccion", "=agua", "sequia", "residuo",
                     "recicl", "plastic", "energia", "electricidad", "=luz", "minera", "mineria", "litio", "bosque", "incendio", "naturaleza",
                     "animales", "glaciar", "termoelectrica", "zona de sacrificio", "parrillada", "asado"],
        "datos": ["rubro", "vehiculo", "tipo_vivienda"],
    },
    "pueblos-originarios": {
        "palabras": ["indigena", "pueblos originarios", "pueblo originario", "mapuche", "aymara", "rapa nui", "plurinacional",
                     "araucania", "tierras ancestrales", "consulta indigena", "escanos reservados"],
        "datos": ["pueblo_originario", "discriminacion"],
    },
}


def _revisar():
    """Falla al importar si el filtro nombra un dato que no existe o un nivel mal escrito."""
    sobran = set(NUCLEO) - set(DATOS)
    for tema, definicion in TEMAS.items():
        sobran |= {f"{tema}: {dato}" for dato in definicion["datos"] if dato not in DATOS}
    if sobran:
        raise ValueError(f"El filtro del perfil nombra datos que no están en DATOS: {sorted(sobran)}")


_revisar()

#: Cambia si cambia cualquier definición: quien guarda respuestas la usa para no mezclar perfiles distintos.
VERSION = hashlib.sha256(
    json.dumps([sorted(DATOS), sorted(NUCLEO), {t: [d["palabras"], d["datos"]] for t, d in TEMAS.items()}, MAX_TEMAS], ensure_ascii=False).encode()
).hexdigest()[:8]


def normalizar(texto):
    """Minúsculas y sin tildes, para comparar con las palabras de los temas."""
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")


def _patron(palabras):
    partes = [re.escape(p[1:]) + r"\b" if p.startswith("=") else re.escape(p) for p in palabras]
    return re.compile(r"\b(?:" + "|".join(partes) + ")")


_PATRONES = {tema: _patron(definicion["palabras"]) for tema, definicion in TEMAS.items()}


def puntajes(texto):
    """Cuántas veces aparecen en el texto las palabras de cada tema, solo de los temas que aparecen."""
    plano = normalizar(texto or "")
    cuentas = {tema: len(patron.findall(plano)) for tema, patron in _PATRONES.items()}
    return {tema: n for tema, n in cuentas.items() if n}


def temas_de(texto):
    """Los temas que toca un texto, del más al menos presente, a lo más MAX_TEMAS.

    Un tema entra si sus palabras aparecen al menos una cuarta parte de lo que aparecen las
    del tema principal: así una mención suelta en un texto largo no agrega datos."""
    cuentas = puntajes(texto)
    if not cuentas:
        return []
    piso = max(cuentas.values()) / 4
    orden = sorted(cuentas, key=lambda tema: (-cuentas[tema], list(TEMAS).index(tema)))
    return [tema for tema in orden if cuentas[tema] >= piso][:MAX_TEMAS]


def datos_de_temas(temas):
    """El núcleo más los datos de estos temas."""
    desconocidos = [tema for tema in temas if tema not in TEMAS]
    if desconocidos:
        raise ValueError(f"Temas desconocidos: {desconocidos}; los que hay son {', '.join(TEMAS)}")
    return NUCLEO | frozenset(dato for tema in temas for dato in TEMAS[tema]["datos"])


def datos_para(texto, nivel="tematico", temas=None):
    """El conjunto de datos que se entregan para un texto, o None si va el perfil completo.

    `temas` fija los temas a mano y se salta la detección."""
    if nivel not in NIVELES:
        raise ValueError(f"Nivel de perfil desconocido: {nivel!r}; los que hay son {', '.join(NIVELES)}")
    if nivel == "completo":
        return None
    if nivel == "nucleo":
        return NUCLEO
    return datos_de_temas(temas if temas is not None else temas_de(texto))


def main():
    if len(sys.argv) > 1:
        for ruta in sys.argv[1:]:
            texto = Path(ruta).read_text(encoding="utf-8")
            temas = temas_de(texto)
            extra = sorted(datos_de_temas(temas) - NUCLEO)
            print(f"{ruta}\n  palabras por tema: {puntajes(texto)}\n  temas: {', '.join(temas) or '(ninguno: solo el núcleo)'}")
            print(f"  datos: {len(NUCLEO)} del núcleo + {len(extra)} de tema: {', '.join(extra) or '-'}")
        return
    de_tema = {dato for definicion in TEMAS.values() for dato in definicion["datos"]}
    print(f"Filtro del perfil, versión {VERSION}: {len(DATOS)} datos en el perfil completo")
    print(f"\nNúcleo ({len(NUCLEO)}): {', '.join(sorted(NUCLEO))}")
    print("\nTemas:")
    for tema, definicion in TEMAS.items():
        print(f"  {tema:<26} +{len(set(definicion['datos']) - NUCLEO):>2}  {', '.join(definicion['datos'])}")
    print(f"\nSolo en el perfil completo ({len(set(DATOS) - NUCLEO - de_tema)}): {', '.join(sorted(set(DATOS) - NUCLEO - de_tema))}")


if __name__ == "__main__":
    main()
