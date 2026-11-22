"""Ejecuta un piloto controlado de Luna sobre catálogos reducidos, por lotes reanudables."""

import argparse
import hashlib
import json
import math
import random
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from preparar_benchmark_catalogos import TEXTO_TAG

MODELO = "gpt-6-luna"
PUBLICADO = [55.0, 40.0, 5.0]
INSTRUCCIONES = """Encuesta de opinión simulada en Chile. Cada línea del listado describe a una
persona ficticia e independiente a la que le hacemos la misma pregunta. Responde en su lugar
según el perfil y el contexto dado, dejando que personas similares puedan diferir. No busques
datos externos ni intentes reproducir cifras publicadas. No uses herramientas ni hagas
cálculos globales sobre el listado. 1 significa de acuerdo, 2 en desacuerdo y 3 no responde
(si el perfil no tomaría una posición). Devuelve únicamente {"r":[...]} con un entero por
línea, en orden estricto. Incluye a todas las personas y conserva el orden aun si ves perfiles
parecidos. No incluyas explicaciones."""


def armar_lotes(catalogo, n, tamano, *, pregunta=TEXTO_TAG):
    rng = random.Random(20261121)
    anteriores = set()
    primera = True
    for k in sorted(int(k) for k in catalogo["muestras"] if int(k) <= n):
        muestra = catalogo["muestras"][str(k)]
        actuales = set(muestra["ids"])
        if not anteriores <= actuales:
            raise ValueError(f"La muestra de {k} no contiene la anterior.")
        nuevos = muestra["ids"].copy() if primera else sorted(actuales - anteriores)
        rng.shuffle(nuevos)
        # Cada ampliación agrega lotes y conserva los prompts ya consultados.
        for inicio in range(0, len(nuevos), tamano):
            ids = nuevos[inicio:inicio + tamano]
            fichas = [f"{i+1}. {muestra['perfil'][id_]}" for i, id_ in enumerate(ids)]
            prompt = (INSTRUCCIONES + "\n\n" + pregunta + "\n\n"
                      + f"El listado tiene {len(fichas)} personas.\n" + "\n".join(fichas))
            yield ids, prompt
        anteriores, primera = actuales, False


def leer_json_respuesta(salida):
    mensajes, uso = [], {}
    for linea in salida.splitlines():
        try:
            evento = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if evento.get("type") == "turn.completed":
            uso = evento.get("usage", {})
        if evento.get("type") == "item.completed" and evento.get("item", {}).get("type") == "agent_message":
            mensajes.append(evento["item"]["text"])
    if not mensajes:
        raise ValueError("Luna no devolvió un mensaje final.")
    limpio = re.sub(r"^ *```(?:json)?\s*|\s*``` *$", "", mensajes[-1].strip())
    return json.loads(limpio), uso


def leer_respuesta(salida, n):
    datos, uso = leer_json_respuesta(salida)
    r = datos["r"]
    if not isinstance(r, list) or len(r) != n or any(type(x) is not int or x not in (1, 2, 3) for x in r):
        raise ValueError(f"Se esperaban {n} decisiones codificadas.")
    return r, uso


def inferir(ids, prompt, carpeta, trabajo, max_intentos, *, interpretar=leer_respuesta, esquema_salida=None):
    llave = hashlib.sha256(json.dumps([MODELO, ids, prompt], ensure_ascii=False).encode()).hexdigest()
    archivo = carpeta / f"{llave}.json"
    if archivo.exists():
        return json.loads(archivo.read_text()), True
    inicio = perf_counter()
    intentos = []
    comando = ["codex", "exec"]
    if esquema_salida is not None:
        comando.extend(["--output-schema", str(esquema_salida)])
    comando.extend([
        "--ephemeral", "--skip-git-repo-check", "-s", "read-only", "-m", MODELO,
        "-c", 'model_reasoning_effort="low"', "--json", "-",
    ])
    for _ in range(max_intentos):
        try:
            r = subprocess.run(
                comando,
                input=prompt, capture_output=True, text=True, cwd=trabajo, timeout=150,
            )
            if r.returncode:
                codigos = [json.loads(l).get("message") for l in r.stdout.splitlines()
                           if l.startswith('{"type":"error"')]
                raise ValueError(str(codigos[-1] if codigos else r.stderr.strip())[:500])
            respuestas, uso = interpretar(r.stdout, len(ids))
        except (ValueError, KeyError, subprocess.TimeoutExpired) as error:
            intentos.append(str(error))
            if any(x in str(error).lower() for x in ("usage limit", "rate limit", "quota", "401", "429")):
                break
            continue
        datos = {"modelo": MODELO, "ids": ids, "r": respuestas, "segundos": perf_counter()-inicio,
                 "uso": uso, "intentos_previos_fallidos": intentos, "huella_prompt": llave}
        temporal = archivo.with_suffix(".tmp")
        temporal.write_text(json.dumps(datos, ensure_ascii=False))
        temporal.replace(archivo)
        return datos, False
    raise RuntimeError(" | ".join(intentos))


def agregado(muestra, respuestas, clave, *, referencia=PUBLICADO):
    pesos = muestra[clave]
    if pesos is None:
        return None
    z = [0.0] * 3
    masa, n = 0.0, 0
    for id_, w in zip(muestra["ids"], pesos):
        if id_ in respuestas:
            z[respuestas[id_]-1] += w
            masa += w
            n += 1
    if not masa or n != len(muestra["ids"]):
        return {"validas": n, "cobertura_peso_pct": 100*masa/sum(pesos)}
    pct = [100*x/masa for x in z]
    if referencia is None:
        return {"validas": n, "pct": pct, "cobertura_peso_pct": 100.0}
    delta = [x-y for x, y in zip(pct, referencia)]
    return {"validas": n, "pct": pct, "error_pp": delta, "mae_pp": (abs(delta[0])+abs(delta[1]))/2,
            "rmse_pp": math.sqrt((delta[0]**2+delta[1]**2)/2), "cobertura_peso_pct": 100.0}


def correr(plan, k, n, carpeta, lote, concurrencia, intentos, *, pregunta=TEXTO_TAG, referencia=PUBLICADO):
    catalogo = plan["catalogos"][str(k)]
    tareas = list(armar_lotes(catalogo, n, lote, pregunta=pregunta))
    carpeta.mkdir(parents=True, exist_ok=True)
    respuestas, registros, errores = {}, [], []
    nuevo = 0
    inicio = perf_counter()
    with TemporaryDirectory(prefix="luna-benchmark-") as trabajo, ThreadPoolExecutor(max_workers=concurrencia) as pool:
        pendientes = {pool.submit(inferir, ids, prompt, carpeta, trabajo, intentos): j
                      for j, (ids, prompt) in enumerate(tareas, 1)}
        for tarea in as_completed(pendientes):
            j = pendientes[tarea]
            try:
                r, cache = tarea.result()
            except RuntimeError as error:
                errores.append({"lote": j, "error": str(error)})
                print(f"Lote {j}: {error}", flush=True)
                if any(x in str(error).lower() for x in ("usage limit", "rate limit", "quota", "401", "429")):
                    for p in pendientes:
                        p.cancel()
                    break
                continue
            registros.append(r)
            respuestas.update(zip(r["ids"], r["r"]))
            nuevo += not cache
            if not cache:
                print(f"Lote {j}/{len(tareas)}: {len(r['r'])} decisiones · {r['segundos']:.1f} s · {len(respuestas)}/{n} acumuladas", flush=True)
    muestras = {}
    for m in sorted(int(k) for k in catalogo["muestras"] if int(k) <= n):
        muestra = catalogo["muestras"][str(m)]
        muestras[m] = {"diseno": agregado(muestra, respuestas, "peso", referencia=referencia),
                       "ipf": agregado(muestra, respuestas, "peso_ipf", referencia=referencia),
                       "estado_ipf": muestra["ipf"],
                       "composicion": muestra["composicion"], "composicion_ipf": muestra["composicion_ipf"]}
    return {"base": plan["base"], "tamano_catalogo": catalogo["fichas"], "k": n, "lote": lote,
            "concurrencia": concurrencia, "lotes_nuevos": nuevo, "lotes_validos": len(registros),
            "segundos": perf_counter()-inicio, "modelo": MODELO, "referencia": referencia,
            "caso": plan["caso"], "pregunta": pregunta, "resultados": muestras, "errores": errores}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan", type=Path)
    ap.add_argument("--catalogo", type=int, required=True)
    ap.add_argument("--muestra", type=int, required=True)
    ap.add_argument("--lote", type=int, default=50)
    ap.add_argument("--concurrencia", type=int, default=6)
    ap.add_argument("--intentos", type=int, default=2)
    ap.add_argument("--salida", type=Path, required=True)
    args = ap.parse_args()
    if args.lote < 1 or args.concurrencia < 1 or args.intentos < 1:
        ap.error("Lote, concurrencia e intentos deben ser positivos.")
    plan = json.loads(args.plan.read_text())
    catalogo = plan["catalogos"].get(str(args.catalogo))
    if catalogo is None or str(args.muestra) not in catalogo["muestras"]:
        ap.error("La combinación de catálogo y muestra debe existir en el plan.")
    args.salida.mkdir(parents=True, exist_ok=True)
    d = correr(plan, args.catalogo, args.muestra, args.salida / f"lotes-{plan['base']}-{args.catalogo}",
               args.lote, args.concurrencia, args.intentos)
    (args.salida / f"resultado-{plan['base']}-{args.catalogo}-{args.muestra}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2))
    print(json.dumps(d, ensure_ascii=False), flush=True)
    if d["lotes_validos"] < sum(1 for _ in armar_lotes(plan["catalogos"][str(args.catalogo)], args.muestra, args.lote)):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
