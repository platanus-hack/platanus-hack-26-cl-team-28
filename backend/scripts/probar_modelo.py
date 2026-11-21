#!/usr/bin/env python3
"""Banco de pruebas: aplica la encuesta a cada persona con el modelo que sirve llama-server.

Uso:
    scripts/servir_modelo.sh qwen9        # en otra terminal
    uv run python -I scripts/probar_modelo.py data/pruebas/personas.jsonl data/pruebas/politica_ejemplo.md

Hace una llamada por persona, con la salida restringida por gramática a "[d,d,d,d,d]",
guarda las respuestas en data/pruebas/resultados_<modelo>.jsonl e imprime un
informe de velocidad, validez, dispersión, coherencia entre preguntas y
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
    --mostrar-prompt     imprime el prompt de la primera persona y termina
    --sin-logprobs       no pide la distribución de probabilidades de cada respuesta
    --exportar-prompts RUTA  escribe en JSON el prompt de cada persona y termina (sin servidor)
    --solo-informe RUTA      imprime el informe de un archivo de resultados ya existente (sin servidor)
"""

import argparse
import json
import math
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
]
CLAVES = [f"p{i}" for i in range(1, len(PREGUNTAS) + 1)]
ESCALA = list(range(1, 8))

SISTEMA = (
    "Vas a contestar una encuesta poniéndote en el lugar de una persona real que vive en Chile. "
    "Responde como lo haría esa persona según su perfil (su situación, sus intereses y su forma "
    "de pensar), no como un asistente ni como un experto neutral. Las personas reales difieren "
    "entre sí: usa toda la escala cuando el perfil lo justifique.\n\n"
    "Todas las preguntas usan una escala de 1 a 7, donde 1 es totalmente en desacuerdo y 7 es "
    "totalmente de acuerdo.\n"
    "Responde solo con cinco enteros de 1 a 7, uno por pregunta y en el mismo orden, "
    "con el formato [p1,p2,p3,p4,p5]."
)

# La gramática obliga a responder exactamente "[d,d,d,d,d]": 11 tokens de salida.
# Un objeto JSON con claves daba las mismas respuestas con ~47 tokens y el triple de tiempo.
GRAMATICA = 'root ::= "[" d "," d "," d "," d "," d "]"\nd ::= [1-7]'


def atributos(persona):
    """Lo que se le muestra al modelo."""
    return persona.get("atributos") or {**persona.get("censo", {}), **persona.get("relleno_aleatorio", {})}


def grupos(persona):
    """Categorías para comparar medias en el informe."""
    return persona.get("grupos") or atributos(persona)


def mensajes(politica, persona):
    """Todo lo que es igual para todos va en el mensaje de sistema y queda en caché;
    el mensaje de usuario lleva solo el perfil, que es lo único que cambia."""
    preguntas = "\n".join(f"{i}. {texto}" for i, texto in enumerate(PREGUNTAS, start=1))
    perfil = "\n".join(f"- {clave}: {valor}" for clave, valor in atributos(persona).items())
    sistema = f"{SISTEMA}\n\n# Política\n\n{politica.strip()}\n\n# Preguntas\n\n{preguntas}"
    usuario = f"# Tu perfil\n\n{perfil}\n\nResponde las cinco preguntas como esta persona."
    return [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]


def pedir(url, cuerpo=None, espera=300):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    solicitud = urllib.request.Request(url, data=datos, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(solicitud, timeout=espera) as r:
        return json.load(r)


def distribuciones(logprobs):
    """Probabilidad de cada valor 1..7 en cada respuesta, según los logprobs del modelo."""
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
    return salida if len(salida) == len(CLAVES) else None


def encuestar(url, politica, persona, semilla, temperatura, logprobs=True):
    cuerpo = {
        "messages": mensajes(politica, persona),
        "temperature": temperatura,
        "seed": semilla,
        "max_tokens": 16,
        "cache_prompt": True,
        "chat_template_kwargs": {"enable_thinking": False},
        "grammar": GRAMATICA,
    }
    if logprobs:
        cuerpo |= {"logprobs": True, "top_logprobs": 10}
    registro = {"id": persona["id"], "semilla": semilla, "respuestas": None, "valida": False}
    inicio = time.perf_counter()
    try:
        r = pedir(f"{url}/v1/chat/completions", cuerpo)
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
        if len(respuestas) == len(CLAVES) and all(type(v) is int and 1 <= v <= 7 for v in respuestas):
            registro["respuestas"] = dict(zip(CLAVES, respuestas))
            registro["valida"] = True
    except (TypeError, ValueError):
        pass
    registro["distribuciones"] = distribuciones(eleccion.get("logprobs"))
    return registro


def correr(url, politica, personas, semilla_base, temperatura, concurrencia, logprobs=True):
    def una(par):
        i, persona = par
        return encuestar(url, politica, persona, semilla_base * 1_000_003 + i, temperatura, logprobs)

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrencia) as grupo:
        registros = list(grupo.map(una, enumerate(personas)))
    return registros, time.perf_counter() - inicio


def correlacion(x, y):
    if len(x) < 3 or statistics.pstdev(x) == 0 or statistics.pstdev(y) == 0:
        return None
    return statistics.correlation(x, y)


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
    razonaron = sum(1 for r in registros if r.get("razono"))
    if razonaron:
        print(f"AVISO: {razonaron} respuestas traen razonamiento; el modelo no lo tiene apagado.")
    if not validos:
        return

    print("\nDistribución por pregunta (muestras):")
    print("       media   de    " + "  ".join(f"{v:>4}" for v in ESCALA))
    for clave in CLAVES:
        valores = [r["respuestas"][clave] for r in validos]
        conteo = "  ".join(f"{valores.count(v):>4}" for v in ESCALA)
        print(f"  {clave}   {statistics.mean(valores):.2f}  {statistics.pstdev(valores):.2f}   {conteo}")

    con_dist = [r for r in validos if r.get("distribuciones")]
    if con_dist:
        print(f"\nDistribución por pregunta según logprobs (promedio de {len(con_dist)} personas, en %):")
        for j, clave in enumerate(CLAVES):
            medias = [statistics.mean(r["distribuciones"][j][k] for r in con_dist) for k in range(7)]
            elegida = statistics.mean(r["distribuciones"][j][r["respuestas"][clave] - 1] for r in con_dist)
            fila = "  ".join(f"{100 * m:>4.0f}" for m in medias)
            print(f"  {clave}                 {fila}   (prob. media del valor elegido: {100 * elegida:.0f} %)")
    else:
        print("\nEl servidor no devolvió logprobs utilizables.")

    print("\nCorrelación entre preguntas:")
    print("       " + "     ".join(CLAVES))
    for a in CLAVES:
        celdas = []
        for b in CLAVES:
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
            medias[nombre] = [statistics.mean(f[c] for f in filas) for c in CLAVES]
            print(f"  {nombre[:38]:<38} n={len(filas):<4} " + "  ".join(f"{m:.2f}" for m in medias[nombre]))
        grandes = [medias[nombre] for nombre, filas in grupos_.items() if len(filas) >= 10]
        if len(grandes) > 1:
            rangos = [max(m[j] for m in grandes) - min(m[j] for m in grandes) for j in range(5)]
            print(f"  {'diferencia máx - mín (grupos con n >= 10)':<45} " + "  ".join(f"{x:.2f}" for x in rangos))

    if repeticion:
        primeras = {r["id"]: r for r in validos}
        pares = [(primeras[r["id"]], r) for r in repeticion if r["valida"] and r["id"] in primeras]
        if pares:
            print(f"\nEstabilidad: {len(pares)} personas repetidas con otra semilla")
            for clave in CLAVES:
                difs = [abs(a["respuestas"][clave] - b["respuestas"][clave]) for a, b in pares]
                iguales = 100 * difs.count(0) / len(difs)
                print(f"  {clave}   diferencia media {statistics.mean(difs):.2f}   iguales {iguales:.0f} %")


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
    ap.add_argument("--mostrar-prompt", action="store_true")
    ap.add_argument("--sin-logprobs", action="store_true")
    ap.add_argument("--exportar-prompts", type=Path)
    ap.add_argument("--solo-informe", type=Path)
    args = ap.parse_args()
    with open(args.personas, encoding="utf-8") as f:
        personas = [json.loads(linea) for linea in f if linea.strip()][: args.limite]
    if args.agrupar:
        agrupar = args.agrupar
    elif "grupos" in personas[0]:
        agrupar = list(dict.fromkeys(clave for p in personas for clave in p["grupos"]))
    else:
        agrupar = ["Tendencia política", "Tramo socioeconómico"]
    politica = args.politica.read_text(encoding="utf-8")

    if args.mostrar_prompt:
        for m in mensajes(politica, personas[0]):
            print(f"--- {m['role']} ---\n{m['content']}\n")
        return

    if args.exportar_prompts:
        prompts = []
        for p in personas:
            sistema, usuario = mensajes(politica, p)
            prompts.append({"id": p["id"], "sistema": sistema["content"], "usuario": usuario["content"]})
        args.exportar_prompts.write_text(json.dumps(prompts, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{len(prompts)} prompts en {args.exportar_prompts}")
        return

    if args.solo_informe:
        with open(args.solo_informe, encoding="utf-8") as f:
            guardados = [json.loads(linea) for linea in f if linea.strip()]
        registros = [r for r in guardados if not r.get("repeticion")]
        repeticion = [r for r in guardados if r.get("repeticion")]
        informe(registros[0].get("modelo", "?"), personas, registros, None, repeticion, agrupar)
        return

    try:
        modelo = pedir(f"{args.url}/v1/models", espera=10)["data"][0]["id"]
    except Exception as e:
        sys.exit(f"No hay servidor en {args.url} ({e}). Levántalo con scripts/servir_modelo.sh")
    modelo = Path(modelo).name.removesuffix(".gguf")

    comunes = (args.temperatura, args.concurrencia, not args.sin_logprobs)
    registros, segundos = correr(args.url, politica, personas, args.semilla, *comunes)
    repeticion = []
    if args.repetir:
        repeticion, _ = correr(args.url, politica, personas[: args.repetir], args.semilla + 1, *comunes)

    salida = args.salida or args.personas.parent / f"resultados_{re.sub(r'[^A-Za-z0-9._-]+', '_', modelo)}.jsonl"
    with open(salida, "w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps({"modelo": modelo, **r}, ensure_ascii=False) + "\n")
        for r in repeticion:
            f.write(json.dumps({"modelo": modelo, "repeticion": True, **r}, ensure_ascii=False) + "\n")

    informe(modelo, personas, registros, segundos, repeticion, agrupar)
    print(f"\nResultados en {salida}")


if __name__ == "__main__":
    main()
