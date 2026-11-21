#!/usr/bin/env python3
"""Valida el método de encuesta contra el banco de referencias externas (../datos-pruebas).

Uso:
    uv run python scripts/validar_banco.py casos
    uv run python scripts/validar_banco.py correr METODO [--parte desarrollo|prueba|todo] [--personas 100]
    uv run python scripts/validar_banco.py informe METODO [METODO ...] [--parte ...] [--detalle]
    uv run python scripts/validar_banco.py prompt METODO CASO

Cada caso del banco es una pregunta de encuesta real con su porcentaje publicado. Aquí se le
hace la misma pregunta a una muestra nacional de agentes adultos (la del sitio, sin filtros,
desde los 18 años, que es a quienes entrevistan las encuestas) y se compara el porcentaje de
acuerdo simulado con el publicado.

Un METODO es una forma de preguntar: instrucciones, preguntas, nivel del perfil. `sitio` es
exactamente lo que hace el motor del sitio (servidor/motor.py con Claude Haiku por la CLI);
los demás son candidatos a reemplazarlo y viven en scripts/metodos_banco.py.

Los casos se parten en dos por familia: `desarrollo`, para iterar, y `prueba`, que se mira
solo al final, para que lo que se afirme no esté ajustado a los mismos casos. Las familias que
el equipo ya había usado para calibrar (`uso` distinto de `candidato`) van a desarrollo.

`correr` gasta: una llamada por lote de personas y caso. Guarda cada lote apenas responde en
data/pruebas/banco/<metodo>.jsonl y, si se corta, al repetir la orden sigue donde quedó.

Opciones de `correr`:
    --personas N       agentes por caso (por defecto 100; las muestras son anidadas)
    --lote K           personas por llamada (por defecto 20, como el sitio)
    --concurrencia K   llamadas simultáneas (por defecto 16)
    --modelo NOMBRE    modelo de la CLI (por defecto haiku)
    --solo ID[,ID]     solo estos casos
"""

import argparse
import hashlib
import json
import statistics
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))

BANCO = RAIZ.parent / "datos-pruebas"
SALIDAS = RAIZ / "data" / "pruebas" / "banco"

DE_ACUERDO = ("De acuerdo", "Muy de acuerdo + De acuerdo", "Sí", "Apoyo reportado", "Adhesión reportada")
EN_DESACUERDO = ("En desacuerdo", "Muy en desacuerdo + En desacuerdo", "No")
NEUTRO = ("Ni de acuerdo ni en desacuerdo",)
TIPOS = ("acuerdo", "percepcion")
# Casos cuya cifra publicada parece mal transcrita; se informan aparte.
DUDOSOS = {"c704-bloqueo"}


def cargar_casos():
    """Los casos comparables: de acuerdo o percepción, a población general, con % de acuerdo."""
    casos = []
    for archivo in sorted((BANCO / "encuestas").glob("*.jsonl")):
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            c = json.loads(linea)
            r = c["respuestas"]
            acuerdo = next((r[k] for k in DE_ACUERDO if k in r), None)
            if c["tipo"] not in TIPOS or c.get("segmento") or acuerdo is None:
                continue
            c["area"] = archivo.stem
            c["real_acuerdo"] = acuerdo
            c["real_desacuerdo"] = next((r[k] for k in EN_DESACUERDO if k in r), None)
            c["real_neutro"] = next((r[k] for k in NEUTRO if k in r), None)
            c["parte"] = parte_de(c)
            casos.append(c)
    return casos


def parte_de(caso):
    if caso.get("uso") != "candidato":
        return "desarrollo"
    return "desarrollo" if int(hashlib.sha1(caso["familia"].encode()).hexdigest(), 16) % 2 == 0 else "prueba"


def elegir(casos, parte, solo=None):
    if solo:
        return [c for c in casos if c["id"] in solo]
    return [c for c in casos if parte == "todo" or c["parte"] == parte]


def agentes_de(n):
    from servidor.poblacion import TablaAgentes

    return TablaAgentes().muestra({"edadMin": 18}, n).agentes


def archivo_de(metodo):
    return SALIDAS / f"{metodo}.jsonl"


def leer(metodo):
    ruta = archivo_de(metodo)
    if not ruta.exists():
        return []
    return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]


def correr(args):
    import metodos_banco
    from servidor import motor as m

    metodo = metodos_banco.METODOS[args.metodo]
    casos = elegir(cargar_casos(), args.parte, args.solo)
    agentes = agentes_de(args.personas)
    lotes = [agentes[i : i + args.lote] for i in range(0, len(agentes), args.lote)]
    hechos = {(f["caso"], f["agente"]) for f in leer(args.metodo) if "notas" in f}
    cli = m.ClaudeCodigo(modelo=args.modelo)
    SALIDAS.mkdir(parents=True, exist_ok=True)
    cerrojo = threading.Lock()
    salida = open(archivo_de(args.metodo), "a", encoding="utf-8")

    tareas = []
    for caso in casos:
        for k, lote in enumerate(lotes):
            faltan = [a for a in lote if (caso["id"], a.id) not in hechos]
            if faltan:
                tareas.append((caso, k, faltan))
    print(f"{args.metodo}: {len(casos)} casos x {len(agentes)} agentes; faltan {len(tareas)} llamadas", flush=True)

    def una(caso, k, lote):
        sistema, prompt, n, cual = metodos_banco.armar(metodo, caso, lote)
        ultimo = None
        for intento in range(3):
            try:
                inicio = time.perf_counter()
                datos, consumo = cli._llamar(cli._modelo, sistema, prompt, m.ESQUEMA_LOTE)
                if metodo.get("probabilidades"):
                    # El modelo no elige una nota: estima la probabilidad de cada respuesta.
                    respuestas = metodos_banco.leer_probabilidades(datos, lote)
                    filas = [{"caso": caso["id"], "agente": a.id, "lote": k, "notas": p, "prob": p} for a, p in respuestas]
                    if "verdad" in metodo:
                        de = {a.id: metodo["verdad"](caso, a) for a in lote}
                        filas = [{**f, "verdad": de[f["agente"]]} for f in filas]
                else:
                    respuestas = m.leer_lote(datos, [a for a in lote], n)
                    por_indice = {a.indice: a for a in lote}
                    filas = [
                        {"caso": caso["id"], "agente": por_indice[r.agente].id, "lote": k, "notas": r.respuestas, "nota": r.respuestas[cual]}
                        for r in respuestas
                    ]
                filas.append({"caso": caso["id"], "lote": k, "llamada": True, "segundos": round(time.perf_counter() - inicio, 1),
                              "tokens_entrada": consumo.tokens_entrada, "tokens_salida": consumo.tokens_salida, "costo_usd": consumo.costo_usd})
                with cerrojo:
                    for f in filas:
                        salida.write(json.dumps(f, ensure_ascii=False) + "\n")
                    salida.flush()
                return len(respuestas), len(lote)
            except Exception as e:  # una llamada caída no detiene la corrida; se reintenta
                ultimo = e
        print(f"  fallo {caso['id']} lote {k}: {ultimo}", flush=True)
        return 0, len(lote)

    inicio = time.perf_counter()
    bien = total = 0
    with ThreadPoolExecutor(max_workers=args.concurrencia) as grupo:
        futuros = [grupo.submit(una, *t) for t in tareas]
        for j, f in enumerate(as_completed(futuros), start=1):
            b, t = f.result()
            bien += b
            total += t
            if j % 25 == 0 or j == len(futuros):
                print(f"  {j}/{len(futuros)} llamadas, {bien}/{total} respuestas, {time.perf_counter() - inicio:.0f} s", flush=True)
    salida.close()
    guardar_personas(agentes)


SISTEMA_PRONOSTICO = (
    "Eres analista de opinión pública en Chile. Te entregan una pregunta de encuesta a población adulta "
    "general. Estima qué porcentaje respondería «de acuerdo» y qué porcentaje «en desacuerdo» (el resto no "
    "sabe o no responde). Entrega dos enteros de 0 a 100."
)
ESQUEMA_PRONOSTICO = {"type": "object", "properties": {"acuerdo": {"type": "integer"}, "desacuerdo": {"type": "integer"}},
                      "required": ["acuerdo", "desacuerdo"], "additionalProperties": False}


def por_caso(args, nombre, hacer):
    """Una llamada por caso, sin agentes: `hacer(cli, caso)` devuelve la fila a guardar."""
    import metodos_banco
    from servidor import motor as m

    casos = elegir(cargar_casos(), args.parte, args.solo)
    ruta = SALIDAS / f"{nombre}.jsonl"
    hechos = {json.loads(l)["caso"] for l in ruta.read_text(encoding="utf-8").splitlines()} if ruta.exists() else set()
    cli = m.ClaudeCodigo(modelo=args.modelo)
    SALIDAS.mkdir(parents=True, exist_ok=True)
    cerrojo = threading.Lock()

    def una(caso):
        for intento in range(3):
            try:
                fila = hacer(cli, caso, metodos_banco)
                with cerrojo, open(ruta, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"caso": caso["id"], **fila}, ensure_ascii=False) + "\n")
                return True
            except Exception as e:
                ultimo = e
        print(f"  fallo {caso['id']}: {ultimo}", flush=True)
        return False

    faltan = [c for c in casos if c["id"] not in hechos]
    with ThreadPoolExecutor(max_workers=args.concurrencia) as grupo:
        bien = sum(grupo.map(una, faltan))
    print(f"{nombre}: {bien}/{len(faltan)} casos nuevos")


def pronostico(cli, caso, metodos_banco):
    """El modelo como analista: estima el porcentaje nacional directamente, sin agentes."""
    datos, _ = cli._llamar(cli._modelo, SISTEMA_PRONOSTICO, metodos_banco.tema_del_caso(caso), ESQUEMA_PRONOSTICO)
    a, d = int(datos["acuerdo"]), int(datos["desacuerdo"])
    return {"agente": "pronostico", "prob": [a, d]}


def pronostico_referencias(cli, caso, metodos_banco):
    """El pronóstico directo con las mismas referencias reales que reciben los agentes."""
    datos, _ = cli._llamar(cli._modelo, SISTEMA_PRONOSTICO, metodos_banco.tema_con_referencias(caso), ESQUEMA_PRONOSTICO)
    return {"agente": "pronostico", "prob": [int(datos["acuerdo"]), int(datos["desacuerdo"])]}


SISTEMA_NOTICIAS = (
    "Eres documentalista. Busca en la web noticias chilenas sobre la medida o el tema que se te entrega y "
    "escribe una nota informativa de 100 a 140 palabras para alguien que no ha seguido el tema: qué se "
    "propone exactamente, quién lo impulsa, a quién beneficia, a quién le cuesta y qué argumentos a favor y "
    "en contra circulan. Describe la situación a la fecha indicada. No incluyas resultados de encuestas ni "
    "porcentajes de apoyo o rechazo, y no digas si la medida es popular o impopular. Responde solo con la nota."
)
_fuentes = None


def noticias(cli, caso, metodos_banco):
    """Una nota de contexto escrita con búsqueda web: lo que haría un agente que busca noticias antes
    de la encuesta. Se guarda con las fuentes que citó, para poder revisar si se coló una encuesta."""
    import subprocess

    global _fuentes
    if _fuentes is None:
        _fuentes = json.loads((BANCO / "fuentes.json").read_text(encoding="utf-8"))
    fecha = _fuentes.get(caso["fuente_id"], {}).get("periodo") or "2026"
    pedido = f"{metodos_banco.tema_del_caso(caso)}\n\nFecha: {fecha}. País: Chile."
    orden = ["claude", "-p", "--model", cli._modelo, "--setting-sources", "", "--strict-mcp-config", "--tools", "WebSearch",
             "--allowedTools", "WebSearch", "--no-session-persistence", "--output-format", "json", "--system-prompt", SISTEMA_NOTICIAS]
    salida = subprocess.run(orden, cwd=cli._carpeta, input=pedido, capture_output=True, text=True, timeout=300, check=False, env=cli._entorno())
    datos = json.loads(salida.stdout or "{}")
    if datos.get("is_error") or not datos.get("result"):
        raise RuntimeError(f"sin nota: {salida.stderr[:200]}")
    texto, _, fuentes = datos["result"].partition("Sources:")
    return {"nota": " ".join(texto.replace("**", "").split()), "fuentes": fuentes.strip(), "costo_usd": datos.get("total_cost_usd")}


SISTEMA_RASGOS = (
    "Clasificas preguntas de encuestas de opinión en Chile. Para la pregunta que se te entrega indica:\n"
    "- tipo: «beneficio» (entrega algo concreto a la gente o le baja un costo), «restriccion» (prohíbe, limita, cobra o "
    "sanciona), «principio» (declara un deber, un derecho o un principio general), «valorico» (moral, familia, "
    "sexualidad, vida y muerte), «institucional» (reglas del sistema político o del Estado) o «percepcion» (una "
    "afirmación sobre cómo son las cosas).\n"
    "- transversal: de 1 a 5, cuánto esperas que la respuesta sea la misma en personas de distinta posición política "
    "(1: divide por completo según posición; 5: casi todos responden igual, sea a favor o en contra).\n"
    "- sello: true si la pregunta menciona o se asocia claramente a un gobierno, un presidente o un sector político."
)
ESQUEMA_RASGOS = {"type": "object", "properties": {
    "tipo": {"type": "string", "enum": ["beneficio", "restriccion", "principio", "valorico", "institucional", "percepcion"]},
    "transversal": {"type": "integer"}, "sello": {"type": "boolean"}}, "required": ["tipo", "transversal", "sello"], "additionalProperties": False}


def rasgos(cli, caso, metodos_banco):
    """Rasgos de la pregunta, sin cifras: para ver si el error del simulador se puede predecir."""
    datos, _ = cli._llamar(cli._modelo, SISTEMA_RASGOS, metodos_banco.tema_del_caso(caso), ESQUEMA_RASGOS)
    return {"tipo": datos["tipo"], "transversal": max(1, min(5, int(datos["transversal"]))), "sello": bool(datos["sello"])}


def clima(cli, caso, metodos_banco):
    datos, _ = cli._llamar(cli._modelo, metodos_banco.SISTEMA_CLIMA, metodos_banco.tema_del_caso(caso), metodos_banco.ESQUEMA_CLIMA)
    return {"clima": " ".join(str(datos["clima"]).split())}


def guardar_personas(agentes):
    """Atributos de cada agente, para desagregar sin volver a leer la tabla."""
    ruta = SALIDAS / "personas.jsonl"
    conocidos = {json.loads(l)["agente"] for l in ruta.read_text(encoding="utf-8").splitlines()} if ruta.exists() else set()
    with open(ruta, "a", encoding="utf-8") as f:
        for a in agentes:
            if a.id not in conocidos:
                f.write(json.dumps({"agente": a.id, "orden": a.indice, "edad": a.edad, "genero": a.genero, "quintil": a.quintil,
                                    "educacion": a.educacion, "politica": a.politica, "region": a.region, "grupos": a.atributos}, ensure_ascii=False) + "\n")


def simulado(filas, personas=None):
    """{caso: (% de acuerdo, % en desacuerdo, % nota 4, n, media)} con las primeras `personas` de la muestra."""
    por_caso, probables = defaultdict(list), defaultdict(list)
    for f in filas:
        if personas is not None and f.get("agente") not in personas and f.get("agente") != "pronostico":
            continue
        if "prob" in f:
            probables[f["caso"]].append(f["prob"])
        elif "nota" in f:
            por_caso[f["caso"]].append(f["nota"])
    salida = {
        caso: (100 * sum(v >= 5 for v in notas) / len(notas), 100 * sum(v <= 3 for v in notas) / len(notas),
               100 * notas.count(4) / len(notas), len(notas), statistics.mean(notas))
        for caso, notas in por_caso.items()
    }
    # Con probabilidades, el porcentaje esperado es el promedio de las de cada persona; sortear
    # una respuesta por persona (Monte Carlo) converge a lo mismo. La «media» va en la escala 1 a 7.
    for caso, ps in probables.items():
        a, d = statistics.mean(p[0] for p in ps), statistics.mean(p[1] for p in ps)
        salida[caso] = (a, d, 100 - a - d, len(ps), 4 + 3 * (a - d) / 100)
    return salida


def metricas(pares):
    """pares: [(real, simulado)]. Error absoluto medio, sesgo, raíz del error cuadrático y correlación."""
    if not pares:
        return None
    difs = [s - r for r, s in pares]
    r = statistics.correlation([a for a, _ in pares], [b for _, b in pares]) if len(pares) > 2 and statistics.pstdev([b for _, b in pares]) > 0 else float("nan")
    return {"n": len(pares), "eam": statistics.mean(abs(d) for d in difs), "sesgo": statistics.mean(difs),
            "recm": statistics.mean(d * d for d in difs) ** 0.5, "r": r,
            "dentro_10": 100 * sum(abs(d) <= 10 for d in difs) / len(difs)}


def recta(pares):
    """Mínimos cuadrados de real = a + b * simulado."""
    xs, ys = [s for _, s in pares], [r for r, _ in pares]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    var = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var if var else 0.0
    return my - b * mx, b


def calibrado(ids, casos, t):
    """Corrige el simulado con una recta ajustada en las demás familias (se deja fuera la familia
    del caso, para que ninguno se corrija con sus parientes). Devuelve [(real, corregido)]."""
    salida = []
    for c in ids:
        otros = [(casos[o]["real_acuerdo"], t[o][0]) for o in ids if casos[o]["familia"] != casos[c]["familia"]]
        a, b = recta(otros)
        salida.append((casos[c]["real_acuerdo"], max(0.0, min(100.0, a + b * t[c][0]))))
    return salida


def piso_de_ruido(ids, casos, t):
    """Error medio que tendría una simulación perfecta solo por preguntarle a n agentes y por el
    margen de la encuesta real (se asume una encuesta de 700 casos): Monte Carlo sobre ambos sorteos."""
    import random

    azar = random.Random(7)
    errores = []
    for _ in range(400):
        for c in ids:
            p, n = casos[c]["real_acuerdo"] / 100, t[c][3]
            sim = sum(azar.random() < p for _ in range(n)) / n
            enc = sum(azar.random() < p for _ in range(700)) / 700
            errores.append(abs(sim - enc) * 100)
    return statistics.mean(errores)


def curva(args):
    """Error contra el número de agentes: para cada n, sortea muchas veces n agentes de los que
    respondieron (los mismos en todos los casos) y promedia el error. Dice cuántos agentes hacen
    falta para que el error deje de bajar."""
    import random

    casos = {c["id"]: c for c in elegir(cargar_casos(), args.parte, args.solo)}
    filas = [f for f in leer(args.metodo) if f.get("caso") in casos and ("nota" in f or "prob" in f)]
    por_agente = defaultdict(dict)
    for f in filas:
        por_agente[f["agente"]][f["caso"]] = f["prob"] if "prob" in f else [100.0 * (f["nota"] >= 5), 100.0 * (f["nota"] <= 3)]
    completos = [a for a, r in por_agente.items() if len(r) == len(casos)]
    print(f"{args.metodo}: {len(completos)} agentes con respuesta en los {len(casos)} casos de {args.parte}")
    azar = random.Random(11)
    ids = sorted(casos)
    todos = [statistics.mean(por_agente[a][c][0] for a in completos) for c in ids]
    print("agentes   EAM contra la encuesta (de 300 sorteos)   distancia al resultado con todos los agentes")
    for n in (10, 20, 50, 100, 200, 500, 1000, 2000):
        if n > len(completos):
            break
        errores, distancias = [], []
        for _ in range(300):
            elegidos = azar.sample(completos, n)
            sim = [statistics.mean(por_agente[a][c][0] for a in elegidos) for c in ids]
            errores.append(statistics.mean(abs(s - casos[c]["real_acuerdo"]) for s, c in zip(sim, ids)))
            distancias.append(statistics.mean(abs(s - t) for s, t in zip(sim, todos)))
        print(f"{n:>7}   {statistics.mean(errores):5.1f} ± {statistics.pstdev(errores):.1f}                           {statistics.mean(distancias):5.1f}")


def agudo(p, k, g):
    """Corrige las probabilidades de una persona: [acuerdo, desacuerdo] en 0 a 100.

    El modelo es tibio persona por persona: a quien claramente apoya algo le pone 70 y no 90, y
    deja 10 a 15 % de «no sabe» donde las encuestas tienen 3 a 5 %. `k` > 1 aleja de 50 la parte
    que toma posición (70 pasa a 84 con k = 2) y `g` es cuánto del «no sabe» se conserva. Va por
    persona y no sobre el total: una medida que divide (mitad en 85, mitad en 15) sigue dando 50,
    y una de consenso (todos en 70) sube."""
    a, d = p
    if a + d <= 0:
        return [0.0, 0.0]
    s = a / (a + d)
    s = s**k / (s**k + (1 - s) ** k)
    toma = 100 - g * (100 - a - d)
    return [toma * s, toma * (1 - s)]


K_POSIBLES = [1 + 0.25 * i for i in range(17)]
G_POSIBLES = [0.0, 0.25, 0.5, 0.75, 1.0]


def agudizar(args):
    """Ajusta `k` y `g` en los casos de la parte pedida y dice cuánto mejora, dejando fuera la
    familia de cada caso al ajustar. Con --k y --g no ajusta: aplica esos valores (para la prueba)."""
    casos = {c["id"]: c for c in elegir(cargar_casos(), args.parte, args.solo) if c["id"] not in DUDOSOS or args.con_dudosos}
    por_caso = defaultdict(list)
    for f in leer(args.metodo):
        if "prob" in f and f["caso"] in casos:
            por_caso[f["caso"]].append(f["prob"])
    ids = sorted(por_caso)

    tabla = {}  # (k, g) -> {caso: % de acuerdo}
    pares_kg = [(args.k, args.g)] if args.k else [(k, g) for k in K_POSIBLES for g in G_POSIBLES]
    for k, g in pares_kg + [(1.0, 1.0)]:
        tabla[k, g] = {c: statistics.mean(agudo(p, k, g)[0] for p in por_caso[c]) for c in ids}

    def eam(kg, cuales):
        return statistics.mean(abs(tabla[kg][c] - casos[c]["real_acuerdo"]) for c in cuales)

    def informe_de(nombre, sim):
        pares = [(casos[c]["real_acuerdo"], sim[c]) for c in ids]
        print("  " + fila_metricas(nombre, metricas(pares), 100 * sum(lado(r, x) for r, x in pares) / len(pares)))

    print(f"{args.metodo}, parte {args.parte}: {len(ids)} casos")
    informe_de("sin corregir", tabla[1.0, 1.0])
    if args.k:
        informe_de(f"k={args.k} g={args.g}", tabla[args.k, args.g])
        return
    mejor = min(pares_kg, key=lambda kg: eam(kg, ids))
    informe_de(f"k={mejor[0]} g={mejor[1]} (ajustado aquí)", tabla[mejor])
    cruzado = {}
    elegidos = defaultdict(int)
    for familia in {casos[c]["familia"] for c in ids}:
        dentro = [c for c in ids if casos[c]["familia"] == familia]
        fuera = [c for c in ids if casos[c]["familia"] != familia]
        kg = min(pares_kg, key=lambda kg: eam(kg, fuera))
        elegidos[kg] += 1
        for c in dentro:
            cruzado[c] = tabla[kg][c]
    informe_de("dejando fuera la familia", cruzado)
    print("  valores elegidos al dejar fuera cada familia:", dict(elegidos))


def anclar(probs, ancla):
    """Mueve las probabilidades de cada agente para que el total nacional coincida con un ancla.

    `probs` son [acuerdo, desacuerdo] por agente (0 a 100) y `ancla` es el [acuerdo, desacuerdo]
    nacional que se quiere (por ejemplo, el pronóstico directo de un modelo más grande). A todos se
    les suma la misma constante en escala logit a la parte que toma posición, así que el orden entre
    personas y las diferencias entre grupos se conservan; el «no sabe» se escala parejo."""
    import math

    a0, d0 = ancla
    toma_ancla = max(1.0, min(100.0, a0 + d0))
    meta = a0 / toma_ancla
    partes = [(max(0.5, min(99.5, 100 * a / (a + d))) / 100 if a + d > 0 else 0.5) for a, d in probs]
    logits = [math.log(x / (1 - x)) for x in partes]
    bajo, alto = -12.0, 12.0
    for _ in range(50):
        medio = (bajo + alto) / 2
        if statistics.mean(1 / (1 + math.exp(-(l + medio))) for l in logits) < meta:
            bajo = medio
        else:
            alto = medio
    return [[toma_ancla / (1 + math.exp(-(l + medio))), toma_ancla * (1 - 1 / (1 + math.exp(-(l + medio))))] for l in logits]


def tramo_de(dimension, segmento, persona):
    """Si la persona cae en un corte publicado. El grupo socioeconómico se aproxima con el quintil
    de ingreso imputado (bajo: quintiles 1 y 2; medio: 3 y 4; alto: 5): no es la misma medida."""
    if dimension == "edad":
        texto = segmento.replace("+", "–200").replace("-", "–")
        desde, hasta = (int(x) for x in texto.split("–"))
        return desde <= persona["edad"] <= hasta
    if dimension == "gse":
        return {"Bajo": (0, 1), "Medio": (2, 3), "Alto": (4,)}.get(segmento, ()).__contains__(persona["quintil"])
    if dimension == "sexo":
        return persona["genero"] == {"Mujeres": 0, "Hombres": 1}.get(segmento)
    return None


def segmentos(args):
    """Compara los cortes publicados por edad, sexo y grupo socioeconómico con los mismos cortes
    entre los agentes. Lo que importa es la diferencia de cada segmento con el total del caso: si
    los agentes mueven a los mayores o a los más pobres en la misma dirección que la encuesta."""
    casos = {c["id"]: c for c in cargar_casos()}
    personas = {}
    for linea in (SALIDAS / "personas.jsonl").read_text(encoding="utf-8").splitlines():
        f = json.loads(linea)
        personas[f["agente"]] = f
    por_caso = defaultdict(list)
    crudas = defaultdict(list)
    for f in leer(args.metodo):
        if f.get("agente") in personas and ("prob" in f or "nota" in f):
            por_caso[f["caso"]].append((personas[f["agente"]], f["prob"][0] if "prob" in f else 100.0 * (f["nota"] >= 5)))
            crudas[f["caso"]].append(f.get("prob"))
    if args.ancla:
        anclas = {f["caso"]: f["prob"] for f in leer(args.ancla)}
        for caso in list(por_caso):
            if caso in anclas and all(crudas[caso]):
                movidas = anclar(crudas[caso], anclas[caso])
                por_caso[caso] = [(persona, m[0]) for (persona, _), m in zip(por_caso[caso], movidas)]
            else:
                del por_caso[caso]
    pares = []
    print(f"{args.metodo}: diferencia de cada segmento con el total (real y simulada), en puntos")
    for linea in (BANCO / "segmentacion.jsonl").read_text(encoding="utf-8").splitlines():
        corte = json.loads(linea)
        caso, filas = casos.get(corte["caso_id"]), por_caso.get(corte["caso_id"])
        real = next((corte["respuestas"][k] for k in DE_ACUERDO if k in corte["respuestas"]), None)
        if not caso or not filas or real is None:
            continue
        dentro = [v for persona, v in filas if tramo_de(corte["dimension"], corte["segmento"], persona)]
        if len(dentro) < 20:
            continue
        total = statistics.mean(v for _, v in filas)
        d_real, d_sim = real - caso["real_acuerdo"], statistics.mean(dentro) - total
        pares.append((d_real, d_sim))
        print(f"  {corte['caso_id']:<30} {corte['dimension']:<5} {corte['segmento']:<8} n={len(dentro):<4} real {real:5.1f} ({d_real:+5.1f})   simulado {statistics.mean(dentro):5.1f} ({d_sim:+5.1f})")
    if len(pares) > 2:
        r = statistics.correlation([a for a, _ in pares], [b for _, b in pares])
        mismo = 100 * sum((a > 0) == (b > 0) for a, b in pares if abs(a) >= 3) / max(1, sum(abs(a) >= 3 for a, _ in pares))
        print(f"\n  {len(pares)} cortes. Correlación entre la diferencia real y la simulada: {r:.2f}. "
              f"Misma dirección en los cortes que se alejan 3 puntos o más del total: {mismo:.0f} %")
        print(f"  Tamaño medio de la diferencia: real {statistics.mean(abs(a) for a, _ in pares):.1f}, simulada {statistics.mean(abs(b) for _, b in pares):.1f}")


def individual(args):
    """Parecido persona a persona en los casos donde el agente trae la respuesta real de su donante
    de la CEP y se le ocultó. Para cada método: el % de acuerdo simulado contra el de esas mismas
    personas; el AUC (probabilidad de que el modelo ponga más alto a alguien que sí estaba de
    acuerdo que a alguien que estaba en desacuerdo; 0,5 es azar); y el acierto al elegir lado."""
    for metodo in args.metodos:
        por_caso = defaultdict(list)
        for f in leer(metodo):
            if f.get("verdad") is not None and "prob" in f:
                por_caso[f["caso"]].append((f["prob"], f["verdad"]))
        print(f"\n{metodo}")
        aucs, aciertos, bases = [], [], []
        for caso, filas in sorted(por_caso.items()):
            real_acuerdo = 100 * sum(v <= 2 for _, v in filas) / len(filas)
            sim_acuerdo = statistics.mean(p[0] for p, _ in filas)
            si = [p[0] - p[1] for p, v in filas if v <= 2]
            no = [p[0] - p[1] for p, v in filas if v >= 4]
            if not si or not no:
                continue
            gana = sum((a > b) + 0.5 * (a == b) for a in si for b in no) / (len(si) * len(no))
            acierto = 100 * (sum(a > 0 for a in si) + sum(b < 0 for b in no) + 0.5 * (si.count(0) + no.count(0))) / (len(si) + len(no))
            base = 100 * max(len(si), len(no)) / (len(si) + len(no))
            aucs.append(gana); aciertos.append(acierto); bases.append(base)
            print(f"  {caso:<26} n={len(filas):<4} acuerdo entre estas personas {real_acuerdo:5.1f} %  simulado {sim_acuerdo:5.1f} %   AUC {gana:.2f}   "
                  f"acierta el lado {acierto:4.0f} % (decir siempre el lado mayoritario: {base:.0f} %)")
        if aucs:
            print(f"  promedio: AUC {statistics.mean(aucs):.2f}, acierta el lado {statistics.mean(aciertos):.0f} % (lado mayoritario: {statistics.mean(bases):.0f} %)")


def lado(real, sim):
    """Si la simulación deja la mayoría del mismo lado que la encuesta (50 % de acuerdo)."""
    return (real >= 50) == (sim >= 50)


def primeras(n):
    ruta = SALIDAS / "personas.jsonl"
    if n is None or not ruta.exists():
        return None
    filas = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines()]
    return {f["agente"] for f in filas if f["orden"] < n}


def fila_metricas(nombre, m, lados):
    return (f"{nombre:<26} n={m['n']:<3} EAM {m['eam']:5.1f}  sesgo {m['sesgo']:+6.1f}  RECM {m['recm']:5.1f}  "
            f"r {m['r']:5.2f}  a 10 pts o menos {m['dentro_10']:3.0f} %  mismo lado {lados:3.0f} %")


def informe(args):
    casos = {c["id"]: c for c in elegir(cargar_casos(), args.parte, args.solo)}
    personas = primeras(args.personas)
    tablas = {}
    for metodo in args.metodos:
        sim = simulado(leer(metodo), personas)
        tablas[metodo] = {c: v for c, v in sim.items() if c in casos}
    comunes = set.intersection(*(set(t) for t in tablas.values())) if tablas else set()
    print(f"Parte: {args.parte}. Casos con respuesta en todos los métodos: {len(comunes)} de {len(casos)}\n")
    print("% de acuerdo simulado (notas 5 a 7 sobre todas las respuestas) contra el publicado:")
    for metodo, t in tablas.items():
        pares = [(casos[c]["real_acuerdo"], t[c][0]) for c in sorted(comunes)]
        if pares:
            print("  " + fila_metricas(metodo, metricas(pares), 100 * sum(lado(r, s) for r, s in pares) / len(pares)))
    if args.calibrar:
        print("\nCon corrección lineal ajustada en las otras familias (real = a + b x simulado):")
        ids = sorted(comunes)
        for metodo, t in tablas.items():
            pares = calibrado(ids, casos, t)
            a, b = recta([(casos[c]["real_acuerdo"], t[c][0]) for c in ids])
            print("  " + fila_metricas(metodo, metricas(pares), 100 * sum(lado(r, x) for r, x in pares) / len(pares)) + f"   recta con todos: {a:+.1f} + {b:.2f} x")
        primero = next(iter(tablas.values()))
        print(f"  Piso de ruido (simulación perfecta con estos n y una encuesta de 700 casos): EAM {piso_de_ruido(ids, casos, primero):.1f}")
    print("\nLo mismo sin indecisos: acuerdo / (acuerdo + desacuerdo), en los casos que publican ambos:")
    for metodo, t in tablas.items():
        pares = []
        for c in sorted(comunes):
            real_d = casos[c]["real_desacuerdo"]
            a, d = t[c][0], t[c][1]
            if real_d is not None and a + d > 0:
                real_a = casos[c]["real_acuerdo"]
                pares.append((100 * real_a / (real_a + real_d), 100 * a / (a + d)))
        if pares:
            print("  " + fila_metricas(metodo, metricas(pares), 100 * sum(lado(r, s) for r, s in pares) / len(pares)))
    if args.detalle:
        for metodo, t in tablas.items():
            print(f"\n{metodo}: caso por caso (real, simulado, diferencia; indecisos simulados; media 1 a 7)")
            orden = sorted(comunes, key=lambda c: t[c][0] - casos[c]["real_acuerdo"])
            for c in orden:
                a, d, ind, n, media = t[c]
                real = casos[c]["real_acuerdo"]
                print(f"  {c:<34} {casos[c]['area'][:14]:<14} real {real:5.1f}  sim {a:5.1f}  dif {a - real:+6.1f}  ind {ind:4.1f}  media {media:.2f}  n={n}  {casos[c]['enunciado'][:70]}")
            print("\n  Por área:")
            por_area = defaultdict(list)
            for c in comunes:
                por_area[casos[c]["area"]].append((casos[c]["real_acuerdo"], t[c][0]))
            for area, pares in sorted(por_area.items()):
                mm = metricas(pares)
                print(f"    {area:<26} n={mm['n']:<3} EAM {mm['eam']:5.1f}  sesgo {mm['sesgo']:+6.1f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    sub.add_parser("casos")
    c = sub.add_parser("correr")
    c.add_argument("metodo")
    c.add_argument("--personas", type=int, default=100)
    c.add_argument("--lote", type=int, default=20)
    c.add_argument("--concurrencia", type=int, default=16)
    c.add_argument("--modelo", default="haiku")
    i = sub.add_parser("informe")
    i.add_argument("metodos", nargs="+")
    i.add_argument("--personas", type=int)
    i.add_argument("--detalle", action="store_true")
    i.add_argument("--calibrar", action="store_true")
    cu = sub.add_parser("curva")
    cu.add_argument("metodo")
    ag = sub.add_parser("agudizar")
    ag.add_argument("metodo")
    ag.add_argument("--k", type=float)
    ag.add_argument("--g", type=float, default=1.0)
    ag.add_argument("--con-dudosos", action="store_true")
    ind = sub.add_parser("individual")
    ind.add_argument("metodos", nargs="+")
    se = sub.add_parser("segmentos")
    se.add_argument("metodo")
    se.add_argument("--ancla", help="método de pronóstico con que se ancla el total nacional")
    pr = sub.add_parser("pronostico")
    pr.add_argument("--referencias", action="store_true")
    cl = sub.add_parser("clima")
    no = sub.add_parser("noticias")
    ra = sub.add_parser("rasgos")
    for s_ in (pr, cl, no, ra):
        s_.add_argument("--modelo", default="sonnet")
        s_.add_argument("--concurrencia", type=int, default=8)
    p = sub.add_parser("prompt")
    p.add_argument("metodo")
    p.add_argument("caso")
    for s in (c, i, pr, cl, cu, ag, no, ra):
        s.add_argument("--parte", choices=["desarrollo", "prueba", "todo"], default="desarrollo")
        s.add_argument("--solo", type=lambda t: set(t.split(",")))
    args = ap.parse_args()
    if args.orden == "casos":
        casos = cargar_casos()
        for parte in ("desarrollo", "prueba"):
            suyos = [c for c in casos if c["parte"] == parte]
            print(f"{parte}: {len(suyos)} casos, {len({c['familia'] for c in suyos})} familias")
            for c in suyos:
                print(f"  {c['id']:<34} {c['tipo']:<10} {c['real_acuerdo']:5.1f}  {c['enunciado'][:90]}")
    elif args.orden == "correr":
        correr(args)
    elif args.orden == "agudizar":
        agudizar(args)
    elif args.orden == "individual":
        individual(args)
    elif args.orden == "segmentos":
        segmentos(args)
    elif args.orden == "curva":
        curva(args)
    elif args.orden == "pronostico":
        if args.referencias:
            por_caso(args, f"pronostico_referencias_{args.modelo}", pronostico_referencias)
        else:
            por_caso(args, f"pronostico_{args.modelo}", pronostico)
    elif args.orden == "rasgos":
        por_caso(args, "rasgos", rasgos)
    elif args.orden == "noticias":
        por_caso(args, "noticias", noticias)
    elif args.orden == "clima":
        por_caso(args, "clima", clima)
    elif args.orden == "informe":
        informe(args)
    else:
        import metodos_banco

        caso = next(c for c in cargar_casos() if c["id"] == args.caso)
        sistema, prompt, n, cual = metodos_banco.armar(metodos_banco.METODOS[args.metodo], caso, agentes_de(2))
        print(f"--- sistema ---\n{sistema}\n\n--- usuario ---\n{prompt}\n\n(respuestas por persona: {n}; la que se compara: {cual + 1})")


if __name__ == "__main__":
    main()
