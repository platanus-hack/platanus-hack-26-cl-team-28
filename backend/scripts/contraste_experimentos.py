#!/usr/bin/env python3
"""Mini experimentos para acercar el pipeline del sitio a las encuestas reales.

Uso:
    uv run python scripts/contraste_experimentos.py correr VARIANTE [--casos dev|prueba|todos] [--concurrencia 40]
    uv run python scripts/contraste_experimentos.py informe [VARIANTE ...] [--casos dev|prueba|todos] [--ancla]

Cada variante cambia una cosa del método del sitio (instrucciones, primera pregunta, datos del
perfil, formato) y se pregunta a los mismos 200 agentes, tomados al azar de los 1.000 del
contraste (data/pruebas/realidad_1000). `base` no se corre: son las respuestas que esos 200
dieron en el contraste con el pipeline vigente.

`dev` son 40 casos de la parte de desarrollo del banco, para iterar. `prueba` son los 42 de la
parte de prueba: se miran solo con las variantes ya elegidas.
"""

import argparse
import json
import math
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
CARPETA = RAIZ / "data" / "pruebas" / "realidad_1000"
SALIDA = CARPETA / "experimentos"
N_AGENTES, LOTE, N_DEV = 200, 20, 40
DUDOSOS = {"c704-bloqueo"}

from servidor import metodo, motor  # noqa: E402
import metodos_banco  # noqa: E402
import probar_modelo as banco  # noqa: E402

# ---------------------------------------------------------------------------------------------
# Piezas con que se arman las variantes
# ---------------------------------------------------------------------------------------------
P1_SITIO = banco.PREGUNTAS[0]
P1_DIRECTA = "¿Estás de acuerdo o en desacuerdo con lo que plantea el tema de la encuesta?"
FRASE_INCLINA = " Una persona que se inclina aunque sea un poco hacia un lado responde 3 o 5, no 4."
FRASE_CUATRO = "El 4 es solo para quien de verdad no tiene opinión o no sabe, y en las encuestas reales eso es poca gente."
CUATRO_REAL = ("El 4 es para quien no tiene opinión formada, no conoce el tema o no sabe qué responder. En las encuestas reales eso "
               "es entre 3 y 15 de cada 100 personas según el tema: más cuando el tema es técnico o lejano a la vida de la persona.")
IDENTIDAD_POLITICA = {"posicion_politica", "partido", "sin_partido", "voto_2025", "aprueba_gobierno", "aprueba_gobierno_anterior"}

COMO_RESPONDE = (
    "\n\nCómo responde la gente de verdad una encuesta en Chile:\n"
    "- La mayoría se interesa poco en la política y no contesta como militante. Frente a una medida concreta pesa primero si le "
    "sirve o le perjudica a ella y a los suyos y si le parece de sentido común; su sector político pesa bastante menos.\n"
    "- Muchas medidas tienen apoyo o rechazo amplio en todos los sectores a la vez: proteger el medio ambiente, dar beneficios "
    "sociales, reconocer derechos, bajar costos, castigar delitos y poner orden suelen gustarle tanto a gente de derecha como de "
    "izquierda. Que una idea suene de izquierda o de derecha no significa que la persona del otro sector la rechace.\n"
    "- La posición política solo divide de verdad cuando la medida lleva el sello explícito de un gobierno, un presidente o un "
    "partido, o cuando toca directamente el tamaño del Estado y los impuestos.\n"
    "- En temas valóricos (eutanasia, matrimonio igualitario, aborto en tres causales) hoy la mayoría de los chilenos de todas las "
    "edades y religiones es permisiva; la oposición fuerte es de una minoría."
)
# La misma idea sin nombrar temas concretos: para ver si lo que ayuda es la regla o la lista de ejemplos.
COMO_RESPONDE_GENERAL = (
    "\n\nCómo responde la gente de verdad una encuesta en Chile:\n"
    "- La mayoría se interesa poco en la política y no contesta como militante. Frente a una medida concreta pesa primero si le "
    "sirve o le perjudica a ella y a los suyos y si le parece de sentido común; su sector político pesa bastante menos.\n"
    "- Que una idea suene de izquierda o de derecha no significa que la persona del otro sector la rechace: lo habitual es que "
    "personas de sectores opuestos respondan parecido, con diferencias de grado. La posición política solo divide de verdad cuando "
    "la medida lleva el sello explícito de un gobierno, un presidente o un partido.\n"
    "- Cuando algo le parece razonable a casi cualquiera, casi todos lo apoyan; cuando le parece abusivo o absurdo a casi cualquiera, "
    "casi todos lo rechazan."
)


def cambiar(*pares):
    """Una función que aplica reemplazos al mensaje de sistema del sitio y falla si alguno no calza."""
    def f(sistema):
        for viejo, nuevo in pares:
            assert viejo in sistema, f"no está en el sistema: {viejo[:50]}"
            sistema = sistema.replace(viejo, nuevo)
        return sistema
    return f


def agregar_a_instrucciones(texto):
    return lambda sistema: sistema.replace(banco.REDACCIONES[1], banco.REDACCIONES[1] + texto, 1)


def en_cadena(*funciones):
    def f(sistema):
        for g in funciones:
            sistema = g(sistema)
        return sistema
    return f


directa = cambiar((P1_SITIO, P1_DIRECTA))
con_indecision = cambiar((FRASE_INCLINA, ""), (FRASE_CUATRO, CUATRO_REAL))
sin_identidad = lambda datos: frozenset(datos - IDENTIDAD_POLITICA)  # noqa: E731

# La postura explícita de Rai (contexto/modelo-luna-postura-explicita.md): primero si la persona tiene postura,
# después su intensidad. Devuelve la indecisión sin empujar a nadie al 4.
INSTRUCCION_POSTURA = (
    "Para la primera pregunta, decide si la persona ya tiene una postura. Devuelve tiene_postura: true si tiene una postura a favor "
    "o en contra, aunque sea moderada. Devuelve tiene_postura: false si no ha formado una opinión, no sabe qué responder o ninguna de "
    "las dos posturas predomina. Si es true, devuelve apoyo con la nota 1, 2 o 3 para rechazo y 5, 6 o 7 para apoyo, según la "
    "intensidad. Si es false, devuelve apoyo: null. Contesta las otras cuatro preguntas con enteros del 1 al 7 según sus escalas."
)
FORMATO_SITIO = banco.FORMATO.format(n=5, claves="r1,r2,r3,r4,r5")
con_postura = cambiar((FORMATO_SITIO, INSTRUCCION_POSTURA))
LOTE_POSTURA = (
    "Vienen varias personas, numeradas. Responde la encuesta por separado como cada una de ellas, sin que una influya en otra. "
    "Para cada persona devuelve `i` (su número), `tiene_postura`, `apoyo` y `p` (sus 4 respuestas a las preguntas 2 a 5, enteros de 1 a 7, en orden)."
)
ESQUEMA_POSTURA = {"type": "object", "properties": {"r": {"type": "array", "items": {"type": "object", "properties": {
    "i": {"type": "integer"}, "tiene_postura": {"type": "boolean"}, "apoyo": {"type": ["integer", "null"]},
    "p": {"type": "array", "items": {"type": "integer"}}}, "required": ["i", "tiene_postura", "apoyo", "p"], "additionalProperties": False}}},
    "required": ["r"], "additionalProperties": False}


def leer_postura(datos, agentes):
    """Las cinco notas como las espera el resto: sin postura queda en 4."""
    salida, vistos = [], set()
    for f in datos.get("r", []):
        k, p, apoyo = f.get("i"), f.get("p"), f.get("apoyo")
        if not isinstance(k, int) or not 0 <= k < len(agentes) or k in vistos or not motor.notas_validas(p, 4):
            continue
        if f.get("tiene_postura") and apoyo in (1, 2, 3, 5, 6, 7):
            nota = apoyo
        elif not f.get("tiene_postura"):
            nota = 4
        else:
            continue
        vistos.add(k)
        salida.append(motor.Respuesta(agentes[k].indice, [nota, *p]))
    return salida


POSTURA = {"esquema": ESQUEMA_POSTURA, "leer": leer_postura, "lote": LOTE_POSTURA}
SECCIONES_CEP = ("politica", "pais", "confianza")
solo_demografia = lambda datos: frozenset(k for k in datos if metodo.filtro.DATOS.get(k) not in SECCIONES_CEP)  # noqa: E731

VARIANTES = {
    # El método del sitio sin cambios: para los casos que no pasaron por el contraste de 1.000 agentes.
    "sitio": {},
    # El motor después de integrar los cambios (servidor/metodo.py): debe dar lo mismo que `directa_sin_identidad`.
    "integrado": {"integrado": True},
    # Ronda 2: la postura explícita de Rai sobre Haiku, sola y con los cambios de perfil y de pregunta.
    "postura": {**POSTURA, "sistema": con_postura},
    "postura_sin_identidad": {**POSTURA, "sistema": con_postura, "datos": sin_identidad},
    "postura_sin_identidad_directa": {**POSTURA, "sistema": en_cadena(con_postura, directa), "datos": sin_identidad},
    "postura_demografia": {**POSTURA, "sistema": con_postura, "datos": solo_demografia},
    "postura_demografia_directa": {**POSTURA, "sistema": en_cadena(con_postura, directa), "datos": solo_demografia},
    # Ronda 3: lo que funcionó junto (la instrucción general, el perfil sin etiquetas políticas y la postura de Rai).
    "general_sin_identidad": {"sistema": agregar_a_instrucciones(COMO_RESPONDE_GENERAL), "datos": sin_identidad},
    "general_sin_identidad_directa": {"sistema": en_cadena(directa, agregar_a_instrucciones(COMO_RESPONDE_GENERAL)), "datos": sin_identidad},
    "postura_general": {**POSTURA, "sistema": en_cadena(con_postura, agregar_a_instrucciones(COMO_RESPONDE_GENERAL))},
    "postura_general_sin_identidad": {**POSTURA, "sistema": en_cadena(con_postura, agregar_a_instrucciones(COMO_RESPONDE_GENERAL)), "datos": sin_identidad},
    "postura_general_sin_identidad_directa": {**POSTURA, "sistema": en_cadena(con_postura, directa, agregar_a_instrucciones(COMO_RESPONDE_GENERAL)), "datos": sin_identidad},
    # Ronda 1: un cambio cada una.
    "directa": {"sistema": directa},
    "sin_identidad": {"datos": sin_identidad},
    "instruccion": {"sistema": agregar_a_instrucciones(COMO_RESPONDE)},
    "indecision": {"sistema": con_indecision},
    # Ronda 2: combinaciones.
    "instruccion_general": {"sistema": agregar_a_instrucciones(COMO_RESPONDE_GENERAL)},
    "directa_instruccion": {"sistema": en_cadena(directa, agregar_a_instrucciones(COMO_RESPONDE))},
    "directa_instruccion_general": {"sistema": en_cadena(directa, agregar_a_instrucciones(COMO_RESPONDE_GENERAL))},
    "directa_sin_identidad": {"sistema": directa, "datos": sin_identidad},
    "todo": {"sistema": en_cadena(directa, con_indecision, agregar_a_instrucciones(COMO_RESPONDE)), "datos": sin_identidad},
    "todo_general": {"sistema": en_cadena(directa, con_indecision, agregar_a_instrucciones(COMO_RESPONDE_GENERAL)), "datos": sin_identidad},
    "directa_instruccion_indecision": {"sistema": en_cadena(directa, con_indecision, agregar_a_instrucciones(COMO_RESPONDE))},
    "directa_general_indecision": {"sistema": en_cadena(directa, con_indecision, agregar_a_instrucciones(COMO_RESPONDE_GENERAL))},
}


# ---------------------------------------------------------------------------------------------
# Datos comunes
# ---------------------------------------------------------------------------------------------
def cargar_casos():
    return {c["id"]: c for c in json.loads((CARPETA / "casos.json").read_text(encoding="utf-8")) if c["grupo"] == "comparable"}


def casos_de_rai():
    """Las preguntas que Rai agregó en su benchmark con Luna y que no están en el banco: otras olas y
    otras encuestadoras. Nada de este contraste se ajustó mirándolas."""
    datos = json.loads((RAIZ.parent / "datos-pruebas" / "benchmark-politicas-chile.json").read_text(encoding="utf-8"))["casos"]
    propios = cargar_casos()
    return {k: {"id": k, "enunciado": c["pregunta"], "familia": c["familia"], "area": c["area"], "fuente_id": c["fuente_id"], "parte": "rai",
                "real_acuerdo": c["referencia_pct"][0], "real_desacuerdo": c["referencia_pct"][1], "luna": c["simulacion"]["pct"]}
            for k, c in datos.items() if k not in propios and c["origen_caso"] != "banco_del_repositorio"}


# Propuestas que alguien del público podría escribir para probar el sitio, sin encuesta real: lo que se
# espera de cada una es de sentido común («alto»: casi todos a favor; «bajo»: casi todos en contra;
# «dividido»: sin mayoría clara). Sirven para ver si el motor responde algo razonable fuera del banco.
LOCOS = [
    ("loco-millon", "Entregar un bono de un millón de pesos a cada persona adulta del país, por una sola vez.", "alto"),
    ("loco-sueldo-politicos", "Rebajar a la mitad el sueldo de diputados y senadores.", "alto"),
    ("loco-transporte-gratis", "Hacer gratuito el transporte público en todo Chile.", "alto"),
    ("loco-medicamentos", "Bajar el precio de los medicamentos fijando un precio máximo por ley.", "alto"),
    ("loco-internet", "Dar internet gratis a todos los hogares del país.", "alto"),
    ("loco-agua", "Garantizar que nadie se quede sin agua potable por no poder pagar la cuenta.", "alto"),
    ("loco-iva-30", "Subir el IVA de 19 % a 30 %.", "bajo"),
    ("loco-pan", "Prohibir la venta de pan en todo el país.", "bajo"),
    ("loco-feriados", "Eliminar todos los feriados del año.", "bajo"),
    ("loco-sueldo-parlamentarios", "Duplicar el sueldo de diputados y senadores.", "bajo"),
    ("loco-robo", "Dejar de sancionar los robos de menos de 500 mil pesos.", "bajo"),
    ("loco-jubilacion-80", "Subir la edad de jubilación a 80 años.", "bajo"),
    ("loco-futbol", "Prohibir el fútbol profesional en Chile.", "bajo"),
    ("loco-mascotas", "Cobrar un impuesto anual de 100 mil pesos por cada mascota.", "bajo"),
    ("loco-4-dias", "Pasar a una semana laboral de cuatro días manteniendo el sueldo.", "alto"),
    ("loco-servicio-militar", "Hacer obligatorio el servicio militar para hombres y mujeres de 18 años.", "dividido"),
    ("loco-capital", "Trasladar la capital de Chile desde Santiago a Concepción.", "dividido"),
    ("loco-voto-16", "Bajar la edad para votar a los 16 años.", "dividido"),
    ("loco-bandera", "Cambiar la bandera de Chile por un diseño nuevo.", "bajo"),
    ("loco-marte", "Destinar el 5 % del presupuesto nacional a una misión chilena tripulada a Marte.", "bajo"),
]


def elegir_casos(cuales):
    if cuales == "locos":
        return {k: {"id": k, "enunciado": t, "familia": k, "area": "sentido-comun", "fuente_id": "", "parte": "locos",
                    "real_acuerdo": float("nan"), "real_desacuerdo": float("nan"), "esperado": e} for k, t, e in LOCOS}
    if cuales == "rai":
        return casos_de_rai()
    casos = cargar_casos()
    if cuales == "todos":
        return casos
    if cuales == "prueba":
        return {k: c for k, c in casos.items() if c["parte"] == "prueba"}
    # dev: los de la CEP que caen en desarrollo y el resto al azar, repartido por apoyo real.
    dev = sorted((c for c in casos.values() if c["parte"] == "desarrollo" and c["id"] not in DUDOSOS), key=lambda c: (c["real_acuerdo"], c["id"]))
    fijos = [c for c in dev if c["id"].startswith("cep96-")]
    resto = [c for c in dev if not c["id"].startswith("cep96-")]
    k = N_DEV - len(fijos)
    elegidos = fijos + [resto[round(i * (len(resto) - 1) / (k - 1))] for i in range(k)]
    return {c["id"]: c for c in elegidos}


def ids_agentes():
    todos = [json.loads(l)["agente"] for l in (CARPETA / "personas.jsonl").read_text(encoding="utf-8").splitlines()]
    return set(random.Random(42).sample(todos, N_AGENTES))


def agentes_elegidos():
    from contraste_realidad import agentes

    ids = ids_agentes()
    return [a for a in agentes() if a.id in ids]


def leer(variante, ids):
    if variante == "base":
        ruta = CARPETA / "respuestas.jsonl"
    else:
        ruta = SALIDA / f"{variante}.jsonl"
    filas = []
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            f = json.loads(linea)
            if "notas" in f and f["agente"] in ids:
                filas.append({"caso": f["caso"], "agente": f["agente"], **{f"p{i + 1}": v for i, v in enumerate(f["notas"])}})
    return pd.DataFrame(filas).drop_duplicates(["caso", "agente"]) if filas else pd.DataFrame(columns=["caso", "agente", "p1"])


# ---------------------------------------------------------------------------------------------
# Correr
# ---------------------------------------------------------------------------------------------
def correr(args):
    v = VARIANTES[args.variante]
    casos = elegir_casos(args.casos)
    gente = agentes_elegidos()
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / f"{args.variante}.jsonl"
    previas = leer(args.variante, {a.id for a in gente})
    hechos = set(zip(previas.caso, previas.agente))
    cli = motor.ClaudeCodigo(modelo=args.modelo)
    cerrojo = threading.Lock()
    salida = open(ruta, "a", encoding="utf-8")
    por_indice = {a.indice: a for a in gente}
    tareas = []
    for caso in casos.values():
        for k in range(0, len(gente), LOTE):
            faltan = [a for a in gente[k:k + LOTE] if (caso["id"], a.id) not in hechos]
            if faltan:
                tareas.append((caso, k // LOTE, faltan))
    print(f"{args.variante}: {len(casos)} casos x {len(gente)} agentes; faltan {len(tareas)} llamadas", flush=True)

    def una(caso, k, lote):
        texto = metodos_banco.tema_del_caso(caso)
        if v.get("integrado"):
            # El motor tal como quedó: su pregunta de apoyo y su perfil sin etiquetas políticas.
            sistema, datos = metodo.sistema_con_politica(texto), metodo.datos_de(texto)
        else:
            # Las variantes se definen sobre el método anterior del sitio: preguntas del banco y perfil temático entero.
            sistema = metodo.sistema_del_banco(texto)
            if "sistema" in v:
                sistema = v["sistema"](sistema)
            datos = metodo.filtro.datos_para(texto, metodo.NIVEL)
            if "datos" in v and datos is not None:
                datos = v["datos"](datos)
        prompt = motor.prompt_lote(lote, datos)
        if "lote" in v:
            prompt = prompt.replace(motor.instruccion_lote(len(metodo.PREGUNTAS)), v["lote"])
            assert v["lote"] in prompt
        ultimo = None
        for _ in range(3):
            try:
                crudo, consumo = cli._llamar(cli._modelo, sistema, prompt, v.get("esquema", motor.ESQUEMA_LOTE))
                r = v.get("leer", motor.leer_lote)(crudo, lote)
                with cerrojo:
                    for x in r:
                        salida.write(json.dumps({"caso": caso["id"], "agente": por_indice[x.agente].id, "lote": k, "notas": x.respuestas}, ensure_ascii=False) + "\n")
                    salida.write(json.dumps({"caso": caso["id"], "lote": k, "llamada": True, "costo_usd": consumo.costo_usd}) + "\n")
                    salida.flush()
                return len(r), len(lote)
            except Exception as e:
                ultimo = e
        print(f"  fallo {caso['id']} lote {k}: {str(ultimo)[:160]}", flush=True)
        return 0, len(lote)

    inicio = time.perf_counter()
    bien = total = 0
    with ThreadPoolExecutor(max_workers=args.concurrencia) as grupo:
        for j, f in enumerate(as_completed([grupo.submit(una, *t) for t in tareas]), start=1):
            b, t = f.result()
            bien += b
            total += t
    salida.close()
    print(f"  {bien}/{total} respuestas en {time.perf_counter() - inicio:.0f} s", flush=True)


# ---------------------------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------------------------
def politica3(pos):
    if pos is None or (isinstance(pos, float) and math.isnan(pos)) or pos <= 0:
        return "nou"
    return "izq" if pos <= 4 else "cen" if pos <= 6 else "der"


VARIABLES_CEP = {"cep96-criminalidad": "iden_nacional_8_a", "cep96-trabajo": "iden_nacional_8_c", "cep96-gasto": "iden_nacional_8_e", "cep96-educacion": "iden_nacional_8_i",
                 "cep96-aporte-economico": "iden_nacional_8_l", "cep96-seleccion-educacion": "iden_nacional_8_m", "cep96-tomas": "educacion_84_a",
                 "cep96-estado-economia": "democracia_33_a", "cep96-burocracia": "democracia_33_d", "cep96-recorte": "rol_gobierno_31"}


def personas():
    filas = []
    for linea in (CARPETA / "personas.jsonl").read_text(encoding="utf-8").splitlines():
        f = json.loads(linea)
        x, g = f["fila"], f["grupos"]
        filas.append({"agente": f["agente"], "politica": politica3(x.get("posicion_politica")),
                      "voto": {1: "jara", 2: "kast"}.get(x.get("voto_segunda_vuelta_2025"), "otro"),
                      "edad": "18-34" if f["edad"] < 35 else "35-54" if f["edad"] < 55 else "55+",
                      "educacion": g.get("Nivel educacional") or "Media", "sexo": "M" if f["genero"] == 0 else "H",
                      "burocracia": x.get("estado_burocracia")})
    return pd.DataFrame(filas).set_index("agente")


def cortes_cep():
    """Acuerdo neto real por segmento en las diez preguntas de la CEP, con las mismas definiciones."""
    cep = pd.read_parquet(RAIZ / "data" / "cep96" / "cep96.parquet")
    C = pd.DataFrame({"w": cep.pond, "politica": cep.iden_pol_2.map(politica3),
                      "voto": cep.elec_pres_155.map({1: "jara", 2: "kast"}).fillna("otro"),
                      "edad": cep.edad.map(lambda e: "18-34" if e < 35 else "35-54" if e < 55 else "55+"),
                      "educacion": cep.esc_nivel_1_c.map(lambda v: "Básica o menos" if v <= 3 else "Superior" if v in (6, 8, 9, 10) else "Media"),
                      "sexo": cep.sexo.map({1: "H", 2: "M"})})
    filas = []
    for caso, var in VARIABLES_CEP.items():
        v = cep[var]
        dos = caso == "cep96-tomas"
        C["a"] = ((v == 1) if dos else v.isin([1, 2])) * 1.0
        C["d"] = ((v == 2) if dos else v.isin([4, 5])) * 1.0
        ta, td = np.average(C.a, weights=C.w), np.average(C.d, weights=C.w)
        for dim in ("politica", "voto", "edad", "educacion", "sexo"):
            for seg, g in C.groupby(dim):
                a, d = np.average(g.a, weights=g.w), np.average(g.d, weights=g.w)
                filas.append({"caso": caso, "dim": dim, "seg": seg, "real": 100 * a / (a + d), "tot_real": 100 * ta / (ta + td)})
    return pd.DataFrame(filas)


def anclar_por_orden(R, anclas):
    """Reparte el total nacional de un ancla entre los agentes sin cambiar su orden: quedan «de acuerdo»
    los que más alto puntuaron (p1, y para desempatar la media de p2 y p4) hasta completar el % del ancla."""
    partes = []
    for caso, g in R.groupby("caso"):
        if caso not in anclas:
            continue
        a, d = anclas[caso]
        g = g.copy()
        puntaje = g.p1 + 0.01 * (g.get("p2", 0) + g.get("p4", 0)) + 1e-6 * g.agente.map(lambda s: hash(s) % 1000)
        orden = puntaje.rank(method="first", ascending=False)
        n = len(g)
        g["a"] = (orden <= round(n * a / 100)) * 100.0
        g["d"] = (orden > n - round(n * d / 100)) * 100.0
        partes.append(g)
    return pd.concat(partes)


def medir(R, casos, P, Q):
    R = R[R.caso.isin(casos)].copy()
    if "a" not in R:
        R["a"], R["d"] = (R.p1 >= 5) * 100.0, (R.p1 <= 3) * 100.0
    R = R.join(P, on="agente")
    T = R.groupby("caso").agg(sim=("a", "mean"), sim_d=("d", "mean"), n=("a", "size"))
    T["real"] = [casos[c]["real_acuerdo"] for c in T.index]
    T["real_d"] = [casos[c]["real_desacuerdo"] for c in T.index]
    T["dif"] = T.sim - T.real
    pol = R.pivot_table(index="caso", columns="politica", values="a", aggfunc="mean")
    T["brecha"] = pol["izq"] - pol["der"]
    m = {"casos": len(T), "n": T.n.mean(), "EAM": abs(T.dif).mean(), "sesgo": T.dif.mean(), "lado": 100 * ((T.real >= 50) == (T.sim >= 50)).mean(),
         "a≤5": 100 * (abs(T.dif) <= 5).mean(), "a≤10": 100 * (abs(T.dif) <= 10).mean(), "r": T.real.corr(T.sim), "EAM≥75": abs(T.dif[T.real >= 75]).mean(), "sesgo≥75": T.dif[T.real >= 75].mean(),
         "sesgo≤45": T.dif[T.real <= 45].mean(), "indecisos": (100 - T.sim - T.sim_d).mean(),
         "EAM_desac": abs(T.sim_d - T.real_d.astype(float)).mean(), "|brecha|": abs(T.brecha).mean()}
    # CEP: brecha real contra simulada y dirección de los segmentos.
    S = R[R.caso.isin(VARIABLES_CEP)]
    if len(S):
        tot = S.groupby("caso").apply(lambda g: 100 * g.a.mean() / max(1e-9, g.a.mean() + g.d.mean()), include_groups=False)
        filas = []
        for dim in ("politica", "voto", "edad", "educacion", "sexo"):
            for (caso, seg), g in S.groupby(["caso", dim]):
                if len(g) >= 20 and g.a.mean() + g.d.mean() > 0:
                    filas.append({"caso": caso, "dim": dim, "seg": seg, "sim": 100 * g.a.mean() / (g.a.mean() + g.d.mean()), "tot_sim": tot[caso]})
        J = pd.DataFrame(filas).merge(Q, on=["caso", "dim", "seg"])
        J["d_real"], J["d_sim"] = J.real - J.tot_real, J.sim - J.tot_sim
        pv = J[J.dim == "politica"].pivot(index="caso", columns="seg", values=["real", "sim"])
        m["cep_casos"] = S.caso.nunique()
        m["cep_brecha_real"] = abs(pv["real"]["izq"] - pv["real"]["der"]).mean()
        m["cep_brecha_sim"] = abs(pv["sim"]["izq"] - pv["sim"]["der"]).mean()
        m["cep_corr_seg"] = J.d_real.corr(J.d_sim)
        m["cep_err_seg"] = abs(J.d_sim - J.d_real).mean()
        m["cep_err_seg_dem"] = abs(J[J.dim.isin(["edad", "educacion", "sexo"])].d_sim - J[J.dim.isin(["edad", "educacion", "sexo"])].d_real).mean()
        b = R[(R.caso == "cep96-burocracia") & R.burocracia.isin([1, 2, 4, 5])]
        if len(b):
            m["burocracia_acierta"] = 100 * (((b.burocracia <= 2) & (b.a > 0)) | ((b.burocracia >= 4) & (b.d > 0))).mean()
    return m, T


def informe(args):
    casos = elegir_casos(args.casos)
    casos = {k: c for k, c in casos.items() if k not in DUDOSOS}
    ids = ids_agentes()
    P, Q = personas(), cortes_cep()
    anclas = {}
    if args.ancla:
        juntas = {}
        for ruta in (RAIZ / "data" / "pruebas" / "banco" / f"{args.ancla}.jsonl", SALIDA / f"ancla_{args.ancla}.jsonl"):
            if ruta.exists():
                for f in map(json.loads, ruta.read_text(encoding="utf-8").splitlines()):
                    juntas.setdefault(f["caso"], []).append(f["prob"])
        anclas = {c: [float(np.mean([p[0] for p in ps])), float(np.mean([p[1] for p in ps]))] for c, ps in juntas.items()}
    if args.casos == "rai":
        ids_base = set()
    variantes = args.variantes or ["base"] + [v for v in VARIANTES if (SALIDA / f"{v}.jsonl").exists()]
    filas, tablas = {}, {}
    for v in variantes:
        R = leer(v, ids)
        R = R[R.caso.isin(casos)]
        completos = R.groupby("caso").size()
        completos = set(completos[completos >= 0.95 * N_AGENTES].index)
        if not completos:
            continue
        tablas[v] = (R, completos)
    comunes = set.intersection(*(c for _, c in tablas.values()))
    sub = {k: casos[k] for k in comunes}
    print(f"Casos: {args.casos}. Comunes a todas las variantes: {len(sub)} de {len(casos)}. Agentes: {N_AGENTES}." + (f" Ancla: {args.ancla}." if args.ancla else ""))
    for v, (R, _) in tablas.items():
        filas[v], T = medir(R, sub, P, Q)
        if args.ancla:
            filas[v + "+ancla"], _ = medir(anclar_por_orden(R[R.caso.isin(sub)], anclas), sub, P, Q)
        if args.detalle and v in args.detalle:
            T["enunciado"] = [sub[c]["enunciado"][:60] for c in T.index]
            print(f"\n{v}\n{T.sort_values('dif').round(1).to_string()}")
    pd.set_option("display.width", 320)
    pd.set_option("display.max_columns", 40)
    print(pd.DataFrame(filas).T.round(1).to_string())
    print(f"\nReferencias: responder siempre 60 %: EAM {np.mean([abs(60 - c['real_acuerdo']) for c in sub.values()]):.1f}; "
          f"brecha real izquierda-derecha en la CEP: ver cep_brecha_real; indecisos reales medios en el banco: 6,6 %")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="orden", required=True)
    c = sub.add_parser("correr")
    c.add_argument("variante", choices=sorted(VARIANTES))
    c.add_argument("--concurrencia", type=int, default=40)
    c.add_argument("--modelo", default="haiku")
    i = sub.add_parser("informe")
    i.add_argument("variantes", nargs="*")
    i.add_argument("--ancla")
    i.add_argument("--detalle", nargs="*")
    for s in (c, i):
        s.add_argument("--casos", choices=["dev", "prueba", "todos", "rai", "locos"], default="dev")
    args = ap.parse_args()
    {"correr": correr, "informe": informe}[args.orden](args)


if __name__ == "__main__":
    main()
