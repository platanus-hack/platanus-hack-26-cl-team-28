#!/usr/bin/env python3
"""Banco de pruebas: aplica la encuesta a cada persona con el modelo que sirve llama-server.

Uso:
    scripts/servir_modelo.sh qwen4        # en otra terminal
    uv run python -I scripts/probar_modelo.py data/pruebas/poblacion/regiones_50.jsonl data/pruebas/sala_cuna/validacion/iniciativa.md
    uv run python -I scripts/probar_modelo.py data/pruebas/poblacion/regiones_50.jsonl data/pruebas/sala_cuna/variantes

Las personas son generales y sirven para cualquier caso. Un caso es una carpeta (ver
data/pruebas/README.md) con sus textos y, si quiere preguntas propias, un encuesta.json:
    {"preguntas": ["...", "..."], "indice": [1, 2], "abiertas": {"clave": "pregunta"}}
"indice" dice qué preguntas se promedian en el índice de aceptación. Sin ese archivo se usan
las seis preguntas sobre una política que están más abajo. La escala es siempre de 1 a 7.
Los resultados se guardan en la carpeta del caso.

POLITICA es un archivo o una carpeta. Si es una carpeta, cada .md es una variante: se
encuesta a las mismas personas con la misma semilla en cada una, para que la diferencia
entre variantes se deba solo al texto. Las variantes se comparan con
scripts/comparar_variantes.py.

La primera respuesta que da el modelo casi no depende del perfil, sea cual sea la pregunta,
así que la encuesta parte con una pregunta de control ("¿Entiendes las instrucciones?") que
absorbe ese efecto. Se guarda aparte, en "control", y no entra en ningún indicador.

Hace una llamada por persona, con la salida restringida por gramática a "[d,d,d,d,d,d,d]",
guarda las respuestas en data/pruebas/resultados_<modelo>.jsonl e imprime un
informe de velocidad, validez, aceptación, dispersión, coherencia entre preguntas y
sensibilidad al perfil. Solo usa la biblioteca estándar.

Opciones:
    --url URL            servidor (por defecto http://127.0.0.1:8080)
    --concurrencia K     llamadas simultáneas (por defecto 16, igual que los slots)
    --limite N           usa solo las primeras N personas
    --semilla S          semilla base del muestreo (por defecto 0)
    --temperatura T      por defecto 1.0: cada respuesta es una muestra, no la moda
    --repetir K          repite las primeras K personas con otra semilla (por defecto 20)
    --agrupar ATRIBUTO   compara medias por este atributo; se puede repetir.
                         Por defecto, todos los de "grupos" si las personas los traen
    --salida RUTA        archivo de resultados
    --perfil FORMA       "prosa" (por defecto, si las personas la traen) o "lista"
    --redaccion N        redacción de las instrucciones: 1 (por defecto) o 2
    --orden LISTA        orden en que se hacen las preguntas, por ejemplo 2,3,4,5,6,1.
                         Las respuestas se guardan siempre como p1..p6
    --sin-control        no hace la pregunta de control: p1 vuelve a ser la primera respuesta
    --etiqueta TEXTO     agrega quién propone la política, por ejemplo "del Gobierno"
    --alternativas RUTA  en vez de la encuesta, hace una sola pregunta de alternativas (un JSON
                         con "pregunta" y "alternativas"). El orden de las alternativas se
                         sortea por persona para que no gane la que va primero
    --encuesta RUTA      preguntas del caso; por defecto, encuesta.json en la carpeta del caso
    --abiertas N         después de la encuesta, pide a N personas repartidas en la lista que
                         justifiquen cada respuesta y contesten las preguntas abiertas.
                         Son unos 400 tokens de salida por persona: sirve el modelo con CTX=32768
    --mostrar-prompt     imprime el prompt de la primera persona y termina
    --sin-logprobs       no pide la distribución de probabilidades de cada respuesta
    --exportar-prompts RUTA  escribe en JSON el prompt de cada persona y termina (sin servidor)
    --solo-informe RUTA      imprime el informe de un archivo de resultados ya existente (sin servidor)
"""

import argparse
import json
import math
import random
import re
import statistics
import sys
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PREGUNTAS = [
    "¿Estarías de acuerdo con que se implemente esta política en tu región?",
    "Si esta política se implementara tal como está descrita, ¿estarías satisfecho con ella?",
    "¿Te parece justa la forma en que esta política reparte costos y beneficios?",
    "¿Confías en que el Estado chileno sea capaz de implementar bien esta política?",
    "Si esta política fuera obligatoria, ¿la cumplirías?",
    "¿Crees que esta política va a lograr lo que se propone?",
]
CLAVES = [f"p{i}" for i in range(1, len(PREGUNTAS) + 1)]
# Va primero y no mide nada: recibe la primera respuesta, que el modelo da casi sin mirar el perfil.
CONTROL = "¿Entiendes las instrucciones de esta encuesta?"
# Índice de aceptación: promedio de las preguntas 1 a 4.
INDICE = CLAVES[:4]
ESCALA = list(range(1, 8))

ABIERTAS = {
    "hogar": "¿Cómo crees que esta política afectaría tu situación personal o la de tu hogar?",
    "comunidad": "¿Cómo crees que afectaría a tu comunidad o región?",
    "cambio": "¿Qué cambiarías de esta política para apoyarla más, o cuál es tu principal preocupación?",
    "accion": "¿Qué estarías dispuesto a hacer frente a esta política?",
}

REDACCIONES = {
    1: (
        "Vas a contestar una encuesta poniéndote en el lugar de una persona real que vive en Chile. "
        "Responde como lo haría esa persona según su perfil (su situación, sus intereses y su forma "
        "de pensar), no como un asistente ni como un experto neutral. Las personas reales difieren "
        "entre sí: usa toda la escala cuando el perfil lo justifique."
    ),
    2: (
        "Eres una persona que vive en Chile y te están haciendo una encuesta de opinión. Tu perfil "
        "dice quién eres. Contesta lo que de verdad pensarías tú, con tu situación, tus intereses y "
        "tus preocupaciones; no des la respuesta de un especialista ni la que suena correcta. La "
        "gente opina distinto: si algo te conviene o te perjudica, que se note en tus respuestas."
    ),
}
FORMATO = (
    "Todas las preguntas usan una escala de 1 a 7, donde 1 es totalmente en desacuerdo y 7 es "
    "totalmente de acuerdo.\n"
    "Responde solo con {n} enteros de 1 a 7, uno por pregunta y en el mismo orden, "
    "con el formato [{claves}]."
)



def gramatica(n):
    """Obliga a responder exactamente "[d,d,...]": dos tokens por respuesta más uno.
    Un objeto JSON con claves daba las mismas respuestas con el triple de tokens y de tiempo."""
    return 'root ::= "[" ' + ' "," '.join("d" for _ in range(n)) + ' "]"\nd ::= [1-7]'


def preguntas_de(cfg):
    """Las preguntas de esta corrida: las de `cfg` si las trae (el servidor deja configurarlas
    por corrida, sin tocar las del módulo), o las del banco."""
    return cfg.get("preguntas") or PREGUNTAS


def claves_de(cfg):
    return [f"p{i}" for i in range(1, len(preguntas_de(cfg)) + 1)]


def cuantas(cfg):
    """Respuestas que se piden en cada llamada."""
    return len(preguntas_de(cfg)) + (1 if cfg["control"] else 0)


def carpeta_del_caso(ruta):
    """La carpeta del caso al que pertenece un texto: la más cercana, hacia arriba, que tenga
    encuesta.json, benchmarks.json o una carpeta variantes."""
    inicio = ruta if ruta.is_dir() else ruta.parent
    for carpeta in [inicio, *inicio.parents][:3]:
        if (carpeta / "encuesta.json").exists() or (carpeta / "benchmarks.json").exists() or (carpeta / "variantes").is_dir():
            return carpeta
    return inicio


def usar_encuesta(ruta):
    """Reemplaza las preguntas del módulo por las de un encuesta.json. Devuelve True si existe."""
    global PREGUNTAS, CLAVES, INDICE, ABIERTAS
    if not ruta or not ruta.exists():
        return False
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    PREGUNTAS = list(datos["preguntas"])
    CLAVES = [f"p{i}" for i in range(1, len(PREGUNTAS) + 1)]
    INDICE = [f"p{i}" for i in datos.get("indice") or range(1, len(PREGUNTAS) + 1)]
    ABIERTAS = datos.get("abiertas", ABIERTAS)
    return True


def atributos(persona):
    """El perfil como lista."""
    return persona.get("atributos") or persona.get("perfil") or {**persona.get("censo", {}), **persona.get("relleno_aleatorio", {})}


def prosa_de(persona):
    """El perfil como un solo texto: una línea por sección, o None si la persona no trae perfil en prosa."""
    if persona.get("prosa"):
        return persona["prosa"]
    if persona.get("perfil"):
        return "\n".join(f"{titulo}. {texto}" for titulo, texto in persona["perfil"].items())
    return None


def grupos(persona):
    """Categorías para comparar medias en el informe."""
    return persona.get("grupos") or atributos(persona)


def mensajes(politica, persona, cfg):
    """Todo lo que es igual para todos va en el mensaje de sistema y queda en caché;
    el mensaje de usuario lleva solo el perfil, que es lo único que cambia."""
    textos = ([CONTROL] if cfg["control"] else []) + [preguntas_de(cfg)[k] for k in cfg["orden"]]
    preguntas = "\n".join(f"{i}. {texto}" for i, texto in enumerate(textos, start=1))
    formato = FORMATO.format(n=len(textos), claves=",".join(f"r{i}" for i in range(1, len(textos) + 1)))
    texto = politica.strip()
    if cfg["etiqueta"]:
        texto += f"\n\nEsta política es una propuesta {cfg['etiqueta']}."
    sistema = f"{REDACCIONES[cfg['redaccion']]}\n\n{formato}\n\n# Tema de la encuesta\n\n{texto}\n\n# Preguntas\n\n{preguntas}"
    if cfg["perfil"] == "prosa" and prosa_de(persona):
        perfil = prosa_de(persona)
    else:
        perfil = "\n".join(f"- {clave}: {valor}" for clave, valor in atributos(persona).items())
    usuario = f"# Tu perfil\n\n{perfil}\n\nResponde las {len(textos)} preguntas como esta persona."
    return [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]


def pedir(url, cuerpo=None, espera=300):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    solicitud = urllib.request.Request(url, data=datos, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(solicitud, timeout=espera) as r:
        return json.load(r)


def distribuciones(logprobs, n):
    """Probabilidad de cada valor 1..7 en cada una de las n respuestas, según los logprobs del modelo."""
    salida, previo = [], ""
    for ficha in (logprobs or {}).get("content") or []:
        texto = ficha.get("token", "")
        if len(texto.strip()) == 1 and texto.strip() in "1234567" and previo.rstrip()[-1:] in ("[", ","):
            masa = defaultdict(float)
            for alternativa in ficha.get("top_logprobs") or []:
                valor = alternativa.get("token", "").strip()
                if len(valor) == 1 and valor in "1234567":
                    masa[int(valor)] += math.exp(alternativa["logprob"])
            total = sum(masa.values())
            if total > 0:
                salida.append([round(masa[v] / total, 4) for v in ESCALA])
        previo += texto
    return salida if len(salida) == n else None


def en_orden_canonico(valores, orden):
    """La respuesta k contesta la pregunta orden[k]: devuelve los valores como p1..p6."""
    canonico = [None] * len(orden)
    for valor, pregunta in zip(valores, orden):
        canonico[pregunta] = valor
    return canonico


def encuestar(politica, persona, semilla, cfg):
    cuerpo = {
        "messages": mensajes(politica, persona, cfg),
        "temperature": cfg["temperatura"],
        "seed": semilla,
        "max_tokens": 2 * cuantas(cfg) + 4,
        "cache_prompt": True,
        "chat_template_kwargs": {"enable_thinking": False},
        "grammar": gramatica(cuantas(cfg)),
    }
    if cfg["logprobs"]:
        cuerpo |= {"logprobs": True, "top_logprobs": 10}
    registro = {"id": persona["id"], "semilla": semilla, "respuestas": None, "valida": False}
    inicio = time.perf_counter()
    try:
        r = pedir(f"{cfg['url']}/v1/chat/completions", cuerpo)
    except Exception as e:  # el informe cuenta los errores; no se detiene la corrida
        registro["error"] = f"{type(e).__name__}: {e}"
        registro["segundos"] = round(time.perf_counter() - inicio, 3)
        return registro
    registro["segundos"] = round(time.perf_counter() - inicio, 3)
    eleccion = r["choices"][0]
    mensaje = eleccion["message"]
    registro["crudo"] = mensaje.get("content")
    registro["razono"] = bool(mensaje.get("reasoning_content"))
    registro["tokens_prompt"] = r.get("usage", {}).get("prompt_tokens")
    registro["tokens_salida"] = r.get("usage", {}).get("completion_tokens")
    registro["tokens_en_cache"] = r.get("timings", {}).get("cache_n")
    try:
        respuestas = json.loads(registro["crudo"])
        if len(respuestas) == cuantas(cfg) and all(type(v) is int and 1 <= v <= 7 for v in respuestas):
            if cfg["control"]:
                registro["control"] = respuestas.pop(0)
            registro["respuestas"] = dict(zip(claves_de(cfg), en_orden_canonico(respuestas, cfg["orden"])))
            registro["valida"] = True
    except (TypeError, ValueError):
        pass
    dist = distribuciones(eleccion.get("logprobs"), cuantas(cfg))
    if dist and cfg["control"]:
        registro["distribucion_control"] = dist.pop(0)
    registro["distribuciones"] = en_orden_canonico(dist, cfg["orden"]) if dist else None
    return registro


def correr(politica, personas, semilla_base, cfg):
    def una(par):
        i, persona = par
        return encuestar(politica, persona, semilla_base * 1_000_003 + i, cfg)

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=cfg["concurrencia"]) as grupo:
        registros = list(grupo.map(una, enumerate(personas)))
    return registros, time.perf_counter() - inicio


def preguntar_abiertas(politica, persona, registro, cfg):
    """Segunda vuelta: la persona ya contestó y ahora explica cada respuesta y contesta las abiertas."""
    claves_j = [f"j{i}" for i in range(1, len(CLAVES) + 1)]
    pedido = (
        "Ahora explica tus respuestas, siempre como esa persona y con sus palabras. Responde en JSON con estas claves:\n"
        + "\n".join(f"- {j}: una frase que justifique tu respuesta a la pregunta {i}." for i, j in enumerate(claves_j, start=cuantas(cfg) - len(CLAVES) + 1))
        + "\n"
        + "\n".join(f"- {clave}: {texto} Una o dos frases." for clave, texto in ABIERTAS.items())
    )
    todas = claves_j + list(ABIERTAS)
    cuerpo = {
        "messages": mensajes(politica, persona, cfg)
        + [{"role": "assistant", "content": registro["crudo"]}, {"role": "user", "content": pedido}],
        "temperature": cfg["temperatura"],
        "seed": registro["semilla"],
        "max_tokens": 700,
        "cache_prompt": True,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {
            "type": "json_object",
            "schema": {
                "type": "object",
                "properties": {clave: {"type": "string"} for clave in todas},
                "required": todas,
                "additionalProperties": False,
            },
        },
    }
    inicio = time.perf_counter()
    try:
        r = pedir(f"{cfg['url']}/v1/chat/completions", cuerpo)
        datos = json.loads(r["choices"][0]["message"]["content"])
        justificaciones = en_orden_canonico([datos[j] for j in claves_j], cfg["orden"])
        registro["abiertas"] = {"justificaciones": dict(zip(CLAVES, justificaciones))} | {c: datos[c] for c in ABIERTAS}
    except Exception as e:  # una respuesta cortada o un error de red no detienen la corrida
        registro["error_abiertas"] = f"{type(e).__name__}: {e}"
    registro["segundos_abiertas"] = round(time.perf_counter() - inicio, 3)


def correr_abiertas(politica, personas, registros, cuantas, cfg):
    """Elige personas repartidas en toda la lista (que puede venir ordenada por región)."""
    validos = [(p, r) for p, r in zip(personas, registros) if r["valida"]]
    paso = max(1, len(validos) // cuantas)
    elegidos = validos[::paso][:cuantas]
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=cfg["concurrencia"]) as grupo:
        list(grupo.map(lambda par: preguntar_abiertas(politica, par[0], par[1], cfg), elegidos))
    hechas = sum(1 for _, r in elegidos if "abiertas" in r)
    return hechas, len(elegidos), time.perf_counter() - inicio


def elegir_alternativa(politica, persona, semilla, cfg, pregunta):
    """Una pregunta de alternativas. Las alternativas van en el mensaje de usuario, en orden sorteado."""
    claves = list(pregunta["alternativas"])
    random.Random(semilla).shuffle(claves)
    sistema, usuario = mensajes(politica, persona, cfg)
    sistema["content"] = f"{REDACCIONES[cfg['redaccion']]}\n\n# Tema de la encuesta\n\n{politica.strip()}"
    opciones = "\n".join(f"{i}. {pregunta['alternativas'][c]}" for i, c in enumerate(claves, start=1))
    usuario["content"] = (
        usuario["content"].rsplit("\n\n", 1)[0]
        + f"\n\n# Pregunta\n\n{pregunta['pregunta']}\n{opciones}\n\nResponde como esta persona, solo con el número de la alternativa."
    )
    cuerpo = {
        "messages": [sistema, usuario],
        "temperature": cfg["temperatura"],
        "seed": semilla,
        "max_tokens": 2,
        "cache_prompt": True,
        "chat_template_kwargs": {"enable_thinking": False},
        "grammar": f"root ::= [1-{len(claves)}]",
        "logprobs": True,
        "top_logprobs": 10,
    }
    registro = {"id": persona["id"], "semilla": semilla, "valida": False}
    try:
        eleccion = pedir(f"{cfg['url']}/v1/chat/completions", cuerpo)["choices"][0]
        registro["eleccion"] = claves[int(eleccion["message"]["content"].strip()) - 1]
        masa = defaultdict(float)
        for alternativa in eleccion["logprobs"]["content"][0]["top_logprobs"]:
            valor = alternativa["token"].strip()
            if valor.isdigit() and 1 <= int(valor) <= len(claves):
                masa[claves[int(valor) - 1]] += math.exp(alternativa["logprob"])
        total = sum(masa.values())
        registro["probabilidades"] = {c: round(masa[c] / total, 4) for c in pregunta["alternativas"]}
        registro["valida"] = True
    except Exception as e:  # el informe cuenta los errores; no se detiene la corrida
        registro["error"] = f"{type(e).__name__}: {e}"
    return registro


def correr_alternativas(politica, personas, semilla_base, cfg, pregunta, modelo, salida):
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=cfg["concurrencia"]) as grupo:
        registros = list(grupo.map(lambda par: elegir_alternativa(politica, par[1], semilla_base * 1_000_003 + par[0], cfg, pregunta), enumerate(personas)))
    segundos = time.perf_counter() - inicio
    with open(salida, "w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps({"modelo": modelo, "perfil": cfg["perfil"], "redaccion": cfg["redaccion"], "pregunta": pregunta.get("nombre"), **r}, ensure_ascii=False) + "\n")
    validos = [r for r in registros if r["valida"]]
    pesos_por_id = {p["id"]: p.get("peso", 1) for p in personas}
    pesos = [pesos_por_id[r["id"]] for r in validos]
    print(f"\n=== {modelo} ===\n{pregunta['pregunta']}")
    print(f"Personas: {len(registros)} en {segundos:.1f} s -> {len(registros) / segundos:.2f} personas/s   Válidas: {len(validos)}")
    print("                                           según logprobs   respuestas sorteadas")
    for clave, texto in pregunta["alternativas"].items():
        probable = 100 * media_ponderada([r["probabilidades"][clave] for r in validos], pesos)
        sorteada = 100 * media_ponderada([r["eleccion"] == clave for r in validos], pesos)
        print(f"  {texto[:38]:<38} {probable:>12.1f} %  {sorteada:>18.1f} %")
    print(f"\nResultados en {salida}")


def revisar_contexto(url, politicas, personas, cfg):
    """Avisa antes de partir si el prompt más largo no cabe en el contexto de un slot del servidor."""
    try:
        por_slot = pedir(f"{url}/props", espera=10)["default_generation_settings"]["n_ctx"]
        larga = max(personas, key=lambda p: len(prosa_de(p) or json.dumps(atributos(p))))
        politica = max((texto for _, texto in politicas), key=len)
        texto = "\n".join(m["content"] for m in mensajes(politica, larga, cfg))
        tokens = len(pedir(f"{url}/tokenize", {"content": texto}, espera=30)["tokens"])
    except Exception:  # un servidor sin estos puntos de consulta no impide la corrida
        return
    # Margen para la plantilla del chat y la respuesta.
    if tokens + 2 * cuantas(cfg) + 60 > por_slot:
        sys.exit(
            f"El prompt más largo tiene unos {tokens} tokens y cada slot del servidor admite {por_slot}.\n"
            f"Sube el contexto (por ejemplo CTX={16 * (tokens + 300)} scripts/servir_modelo.sh ...) o acorta el perfil "
            "con --secciones en scripts/personas_muestra.py."
        )


def correlacion(x, y):
    if len(x) < 3 or statistics.pstdev(x) == 0 or statistics.pstdev(y) == 0:
        return None
    return statistics.correlation(x, y)


def media_ponderada(valores, pesos):
    return sum(v * w for v, w in zip(valores, pesos)) / sum(pesos)


def indice(respuestas):
    return statistics.mean(respuestas[c] for c in INDICE)


def resumen(registros, pesos):
    """(índice de aceptación, % de acuerdo en P1, % en desacuerdo en P1), ponderados."""
    validos = [r for r in registros if r["valida"]]
    if not validos:
        return None
    w = [pesos.get(r["id"], 1) for r in validos]
    p1 = [r["respuestas"]["p1"] for r in validos]
    return (
        media_ponderada([indice(r["respuestas"]) for r in validos], w),
        100 * media_ponderada([v >= 5 for v in p1], w),
        100 * media_ponderada([v <= 3 for v in p1], w),
    )


def informe(modelo, personas, registros, segundos, repeticion, agrupar):
    n = len(registros)
    validos = [r for r in registros if r["valida"]]
    errores = [r for r in registros if "error" in r]
    print(f"\n=== {modelo} ===")
    if segundos:
        print(f"Personas: {n} en {segundos:.1f} s -> {n / segundos:.2f} personas/s")
    else:
        print(f"Personas: {n}")
    print(f"Válidas: {len(validos)}/{n} ({100 * len(validos) / n:.1f} %)   Errores de red o servidor: {len(errores)}")
    if errores:
        print(f"  primer error: {errores[0]['error']}")
    con_uso = [r for r in registros if r.get("tokens_prompt")]
    if con_uso:
        prompt = statistics.mean(r["tokens_prompt"] for r in con_uso)
        salida = statistics.mean(r["tokens_salida"] or 0 for r in con_uso)
        cache = [r["tokens_en_cache"] for r in con_uso if r.get("tokens_en_cache") is not None]
        texto_cache = f", {statistics.mean(cache):.0f} servidos desde caché" if cache else ""
        print(f"Tokens por persona: {prompt:.0f} de prompt{texto_cache}, {salida:.0f} de salida")
    controles = [r["control"] for r in registros if r.get("control")]
    if controles:
        sietes = 100 * controles.count(7) / len(controles)
        print(f"Pregunta de control: media {statistics.mean(controles):.2f}, de {statistics.pstdev(controles):.2f}, responde 7 el {sietes:.0f} %")
    razonaron = sum(1 for r in registros if r.get("razono"))
    if razonaron:
        print(f"AVISO: {razonaron} respuestas traen razonamiento; el modelo no lo tiene apagado.")
    if not validos:
        return
    # Los archivos anteriores a la pregunta 6 traen solo p1..p5.
    claves = [c for c in CLAVES if c in validos[0]["respuestas"]]
    pesos_por_id = {p["id"]: p.get("peso", 1) for p in personas}
    pesos = [pesos_por_id.get(r["id"], 1) for r in validos]
    ponderado = " ponderado" if len(set(pesos)) > 1 else ""

    print(f"\nAceptación{ponderado} (de acuerdo: 5 a 7; en desacuerdo: 1 a 3):")
    if all(c in claves for c in INDICE):
        print(f"  Índice de aceptación (media de {', '.join(INDICE)}): {media_ponderada([indice(r['respuestas']) for r in validos], pesos):.2f}")
    for clave in claves:
        valores = [r["respuestas"][clave] for r in validos]
        acuerdo = 100 * media_ponderada([v >= 5 for v in valores], pesos)
        desacuerdo = 100 * media_ponderada([v <= 3 for v in valores], pesos)
        print(f"  {clave}   de acuerdo {acuerdo:5.1f} %   en desacuerdo {desacuerdo:5.1f} %")

    print("\nDistribución por pregunta (muestras, sin ponderar):")
    print("       media   de    " + "  ".join(f"{v:>4}" for v in ESCALA))
    for clave in claves:
        valores = [r["respuestas"][clave] for r in validos]
        conteo = "  ".join(f"{valores.count(v):>4}" for v in ESCALA)
        print(f"  {clave}   {statistics.mean(valores):.2f}  {statistics.pstdev(valores):.2f}   {conteo}")

    con_dist = [r for r in validos if r.get("distribuciones")]
    if con_dist:
        print(f"\nDistribución por pregunta según logprobs (promedio de {len(con_dist)} personas, en %):")
        for j, clave in enumerate(claves):
            medias = [statistics.mean(r["distribuciones"][j][k] for r in con_dist) for k in range(7)]
            elegida = statistics.mean(r["distribuciones"][j][r["respuestas"][clave] - 1] for r in con_dist)
            fila = "  ".join(f"{100 * m:>4.0f}" for m in medias)
            print(f"  {clave}                 {fila}   (prob. media del valor elegido: {100 * elegida:.0f} %)")
        # Cuánto de lo que varía cada respuesta viene de la persona y cuánto del sorteo.
        # En las preguntas que no van primero, la distribución ya depende de las respuestas anteriores.
        print("\nSeñal del perfil: varianza del valor esperado entre personas / varianza de las respuestas:")
        for j, clave in enumerate(claves):
            esperados = [sum(v * p for v, p in zip(ESCALA, r["distribuciones"][j])) for r in con_dist]
            total = statistics.pvariance([r["respuestas"][clave] for r in con_dist])
            parte = 100 * statistics.pvariance(esperados) / total if total else 0
            print(f"  {clave}   {parte:3.0f} %")
    else:
        print("\nEl servidor no devolvió logprobs utilizables.")

    print("\nCorrelación entre preguntas:")
    print("       " + "     ".join(claves))
    for a in claves:
        celdas = []
        for b in claves:
            c = correlacion([r["respuestas"][a] for r in validos], [r["respuestas"][b] for r in validos])
            celdas.append(" n/d " if c is None else f"{c:5.2f}")
        print(f"  {a}  " + "  ".join(celdas))

    por_id = {p["id"]: grupos(p) for p in personas}
    for atributo in agrupar:
        grupos_ = defaultdict(list)
        for r in validos:
            grupos_[por_id[r["id"]].get(atributo, "(sin dato)")].append(r["respuestas"])
        print(f"\nMedia por «{atributo}»:")
        medias = {}
        for nombre, filas in sorted(grupos_.items()):
            medias[nombre] = [statistics.mean(f[c] for f in filas) for c in claves]
            print(f"  {nombre[:38]:<38} n={len(filas):<4} " + "  ".join(f"{m:.2f}" for m in medias[nombre]))
        grandes = [medias[nombre] for nombre, filas in grupos_.items() if len(filas) >= 10]
        if len(grandes) > 1:
            rangos = [max(m[j] for m in grandes) - min(m[j] for m in grandes) for j in range(len(claves))]
            print(f"  {'diferencia máx - mín (grupos con n >= 10)':<45} " + "  ".join(f"{x:.2f}" for x in rangos))

    if repeticion:
        primeras = {r["id"]: r for r in validos}
        pares = [(primeras[r["id"]], r) for r in repeticion if r["valida"] and r["id"] in primeras]
        if pares:
            print(f"\nEstabilidad: {len(pares)} personas repetidas con otra semilla")
            for clave in claves:
                difs = [abs(a["respuestas"][clave] - b["respuestas"][clave]) for a, b in pares]
                iguales = 100 * difs.count(0) / len(difs)
                print(f"  {clave}   diferencia media {statistics.mean(difs):.2f}   iguales {iguales:.0f} %")


def cargar_politicas(ruta):
    """[(variante o None, texto)]: una por archivo .md si la ruta es una carpeta."""
    if ruta.is_dir():
        archivos = sorted(ruta.glob("*.md"))
        if not archivos:
            sys.exit(f"No hay archivos .md en {ruta}")
        return [(a.stem, a.read_text(encoding="utf-8")) for a in archivos]
    return [(None, ruta.read_text(encoding="utf-8"))]


def leer_orden(texto):
    if not texto:
        return list(range(len(CLAVES)))
    orden = [int(x) - 1 for x in texto.split(",")]
    if sorted(orden) != list(range(len(CLAVES))):
        sys.exit(f"--orden debe traer cada pregunta de 1 a {len(CLAVES)} una vez, por ejemplo 2,3,4,5,6,1")
    return orden


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("personas", type=Path)
    ap.add_argument("politica", type=Path)
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--concurrencia", type=int, default=16)
    ap.add_argument("--limite", type=int)
    ap.add_argument("--semilla", type=int, default=0)
    ap.add_argument("--temperatura", type=float, default=1.0)
    ap.add_argument("--repetir", type=int, default=20)
    ap.add_argument("--agrupar", action="append")
    ap.add_argument("--salida", type=Path)
    ap.add_argument("--perfil", choices=["prosa", "lista"], default="prosa")
    ap.add_argument("--redaccion", type=int, choices=sorted(REDACCIONES), default=1)
    ap.add_argument("--orden")
    ap.add_argument("--sin-control", action="store_true")
    ap.add_argument("--etiqueta")
    ap.add_argument("--abiertas", type=int, default=0)
    ap.add_argument("--alternativas", type=Path)
    ap.add_argument("--encuesta", type=Path)
    ap.add_argument("--mostrar-prompt", action="store_true")
    ap.add_argument("--sin-logprobs", action="store_true")
    ap.add_argument("--exportar-prompts", type=Path)
    ap.add_argument("--solo-informe", type=Path)
    args = ap.parse_args()
    caso = carpeta_del_caso(args.solo_informe or args.politica)
    usar_encuesta(args.encuesta or caso / "encuesta.json")
    with open(args.personas, encoding="utf-8") as f:
        personas = [json.loads(linea) for linea in f if linea.strip()][: args.limite]
    if args.agrupar:
        agrupar = args.agrupar
    elif "grupos" in personas[0]:
        agrupar = list(dict.fromkeys(clave for p in personas for clave in p["grupos"]))
    else:
        agrupar = ["Tendencia política", "Tramo socioeconómico"]

    if args.solo_informe:
        with open(args.solo_informe, encoding="utf-8") as f:
            guardados = [json.loads(linea) for linea in f if linea.strip()]
        for variante in dict.fromkeys(r.get("variante") for r in guardados):
            suyos = [r for r in guardados if r.get("variante") == variante]
            registros = [r for r in suyos if not r.get("repeticion")]
            repeticion = [r for r in suyos if r.get("repeticion")]
            titulo = registros[0].get("modelo", "?") + (f" · variante {variante}" if variante else "")
            informe(titulo, personas, registros, None, repeticion, agrupar)
        return

    politicas = cargar_politicas(args.politica)
    cfg = {
        "url": args.url,
        "temperatura": args.temperatura,
        "concurrencia": args.concurrencia,
        "logprobs": not args.sin_logprobs,
        "perfil": args.perfil,
        "redaccion": args.redaccion,
        "orden": leer_orden(args.orden),
        "control": not args.sin_control,
        "etiqueta": args.etiqueta,
    }

    if args.mostrar_prompt:
        for variante, politica in politicas:
            if variante:
                print(f"===== variante {variante} =====")
            for m in mensajes(politica, personas[0], cfg):
                print(f"--- {m['role']} ---\n{m['content']}\n")
        return

    if args.exportar_prompts:
        prompts = []
        for variante, politica in politicas:
            for p in personas:
                sistema, usuario = mensajes(politica, p, cfg)
                prompts.append({"id": p["id"], "variante": variante, "sistema": sistema["content"], "usuario": usuario["content"]})
        args.exportar_prompts.write_text(json.dumps(prompts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{len(prompts)} prompts en {args.exportar_prompts}")
        return

    try:
        modelo = pedir(f"{args.url}/v1/models", espera=10)["data"][0]["id"]
    except Exception as e:
        sys.exit(f"No hay servidor en {args.url} ({e}). Levántalo con scripts/servir_modelo.sh")
    modelo = Path(modelo).name.removesuffix(".gguf")

    revisar_contexto(args.url, politicas, personas, cfg)
    nombre = re.sub(r"[^A-Za-z0-9._-]+", "_", modelo)
    if args.alternativas:
        pregunta = json.loads(args.alternativas.read_text(encoding="utf-8")) | {"nombre": args.alternativas.stem}
        salida = args.salida or caso / f"resultados_{args.alternativas.stem}_{nombre}.jsonl"
        correr_alternativas(politicas[0][1], personas, args.semilla, cfg, pregunta, modelo, salida)
        return
    nombre = f"{args.politica.name if args.politica.is_dir() else args.politica.stem}_{nombre}"
    salida = args.salida or caso / f"resultados_{nombre}.jsonl"
    # Lo que distingue esta corrida de otra con las mismas personas y el mismo modelo.
    condicion = {"perfil": args.perfil, "redaccion": args.redaccion, "con_control": not args.sin_control}
    if not args.politica.is_dir():
        condicion["politica"] = args.politica.stem
    if args.orden:
        condicion["orden"] = args.orden
    if args.etiqueta:
        condicion["etiqueta"] = args.etiqueta
    pesos = {p["id"]: p.get("peso", 1) for p in personas}

    filas = []
    with open(salida, "w", encoding="utf-8") as f:
        for variante, politica in politicas:
            registros, segundos = correr(politica, personas, args.semilla, cfg)
            repeticion = []
            if args.repetir:
                repeticion, _ = correr(politica, personas[: args.repetir], args.semilla + 1, cfg)
            abiertas = correr_abiertas(politica, personas, registros, args.abiertas, cfg) if args.abiertas else None
            marca = {"modelo": modelo, **({"variante": variante} if variante else {}), **condicion}
            for r in registros:
                f.write(json.dumps({**marca, **r}, ensure_ascii=False) + "\n")
            for r in repeticion:
                f.write(json.dumps({**marca, "repeticion": True, **r}, ensure_ascii=False) + "\n")
            f.flush()
            if variante is None:
                informe(modelo, personas, registros, segundos, repeticion, agrupar)
            filas.append((variante, registros, segundos, abiertas))
            if abiertas:
                hechas, pedidas, tardo = abiertas
                print(f"\nAbiertas{f' de {variante}' if variante else ''}: {hechas}/{pedidas} en {tardo:.1f} s")

    if politicas[0][0] is not None:
        print(f"\n=== {modelo} · {len(personas)} personas por variante ===")
        print("variante  válidas  personas/s        índice  p1 de acuerdo  p1 en desacuerdo")
        for variante, registros, segundos, _ in filas:
            validas = sum(1 for r in registros if r["valida"])
            cifras = resumen(registros, pesos)
            texto = f"{cifras[0]:12.2f}  {cifras[1]:11.1f} %  {cifras[2]:14.1f} %" if cifras else ""
            print(f"{variante:<8}  {validas:>7}  {len(registros) / segundos:>10.2f}  {texto}")
        print(f"\nCompara las variantes con: uv run python -I scripts/comparar_variantes.py {args.personas} {salida}")
    print(f"\nResultados en {salida}")


if __name__ == "__main__":
    main()
