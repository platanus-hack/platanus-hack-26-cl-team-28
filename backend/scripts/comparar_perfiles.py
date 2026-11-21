#!/usr/bin/env python3
"""Compara el perfil completo con el perfil filtrado: mismas personas, mismos textos, mismo modelo.

Uso:
    uv run python scripts/comparar_perfiles.py correr SALIDA.jsonl TEXTO_O_CARPETA [...] [--personas 200]
    uv run python scripts/comparar_perfiles.py informe SALIDA.jsonl

Sirve para saber si el filtro de scripts/filtro_perfil.py cambia lo que responde el modelo.
Pregunta por el camino del sitio (servidor/motor.py: Claude Haiku por la CLI, en lotes, con
las mismas instrucciones) a las mismas personas de la tabla de agentes, tres veces:

  completo     con el perfil completo
  completo_b   otra vez con el perfil completo: cuánto cambian las respuestas sin cambiar nada
  tematico     con el núcleo más los datos de los temas que el filtro detecta en cada texto

La repetición es la vara: una diferencia entre completo y tematico solo dice algo si es mayor
que la que hay entre completo y completo_b. Los lotes tienen las mismas personas en los tres
brazos, y los intervalos remuestrean lotes completos, porque las respuestas de un lote no son
independientes (ver CLAUDE.md).

`correr` gasta: cada texto son 3 llamadas por lote. Guarda cada lote apenas responde y, si se
corta, al repetir la orden sigue desde donde quedó. Deja SALIDA.jsonl (una respuesta por
línea, más una línea por llamada con sus tokens) y SALIDA_personas.jsonl (los atributos de
cada persona, para desagregar). TEXTO_O_CARPETA es un .md o una carpeta de .md (variantes).

Opciones de `correr`:
    --personas N       personas de la muestra sin filtros de la tabla de agentes (por defecto 200)
    --lote K           personas por llamada (por defecto 20, como el sitio)
    --concurrencia K   llamadas simultáneas (por defecto 10)
    --modelo NOMBRE    modelo de la CLI (por defecto haiku)
"""

import argparse
import json
import random
import statistics
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

BRAZOS = ("completo", "completo_b", "tematico")
INDICE = 4  # el índice de aceptación es la media de las cuatro primeras preguntas
A_DESAGREGAR = ["Posición política", "Evaluación del gobierno", "Menores en el hogar", "Situación laboral", "Edad", "Género", "Tramo socioeconómico", "Nivel educacional"]
REMUESTREOS = 2000


def textos_de(rutas):
    """[(nombre, texto)]: cada .md de una carpeta, o el archivo."""
    salida = []
    for ruta in rutas:
        archivos = sorted(ruta.glob("*.md")) if ruta.is_dir() else [ruta]
        if not archivos:
            sys.exit(f"No hay archivos .md en {ruta}")
        salida += [(a.stem, a.read_text(encoding="utf-8")) for a in archivos]
    if len({nombre for nombre, _ in salida}) < len(salida):
        sys.exit("Hay dos textos con el mismo nombre")
    return salida


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


# ---------------------------------------------------------------- correr


def correr(args):
    from servidor import metodo, motor
    from servidor.poblacion import TablaAgentes

    textos = textos_de(args.textos)
    agentes = TablaAgentes().muestra(None, args.personas).agentes
    lotes = [agentes[k:k + args.lote] for k in range(0, len(agentes), args.lote)]
    claude = motor.ClaudeCodigo(modelo=args.modelo)
    filtro = metodo.filtro

    personas = args.salida.with_name(args.salida.stem + "_personas.jsonl")
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with open(personas, "w", encoding="utf-8") as f:
        for numero, lote in enumerate(lotes):
            for a in lote:
                f.write(json.dumps({"id": a.id, "lote": numero, "edad": a.edad, "atributos": a.atributos}, ensure_ascii=False) + "\n")

    hechas = {(r["brazo"], r["texto"], r["id"]) for r in leer(args.salida) if "id" in r} if args.salida.exists() else set()
    tareas = []
    for nombre, texto in textos:
        datos_del_tema = filtro.datos_para(texto, "tematico")
        print(f"{nombre}: temas {filtro.temas_de(texto) or '(ninguno)'}, {len(datos_del_tema)} datos de {len(filtro.DATOS)}")
        for brazo in BRAZOS:
            datos = datos_del_tema if brazo == "tematico" else None
            for numero, lote in enumerate(lotes):
                faltan = [a for a in lote if (brazo, nombre, a.id) not in hechas]
                if faltan:
                    tareas.append((brazo, nombre, texto, datos, numero, faltan))
    # Mezcladas: que ningún brazo corra entero antes que otro.
    random.Random(1).shuffle(tareas)
    print(f"{len(agentes)} personas en {len(lotes)} lotes · {len(textos)} textos · {len(tareas)} llamadas pendientes ({len(hechas)} respuestas ya guardadas)")

    cerrojo, avance = threading.Lock(), [0]

    def una(tarea):
        brazo, nombre, texto, datos, numero, pendientes = tarea
        sistema = metodo.sistema_con_politica(texto)
        for intento in range(3):
            if not pendientes:
                break
            inicio = time.perf_counter()
            try:
                crudo, consumo = claude._llamar(claude._modelo, sistema, motor.prompt_lote(pendientes, datos), motor.ESQUEMA_LOTE)
            except Exception as error:  # se reintenta; lo que falte se informa al final
                print(f"  falló {brazo} {nombre} lote {numero} (intento {intento + 1}): {str(error)[:120]}", flush=True)
                continue
            respuestas = motor.leer_lote(crudo, [_con_indice(a, k) for k, a in enumerate(pendientes)])
            respondieron = {r.agente for r in respuestas}
            with cerrojo, open(args.salida, "a", encoding="utf-8") as f:
                f.write(json.dumps({"llamada": True, "brazo": brazo, "texto": nombre, "lote": numero, "personas": len(pendientes),
                                    "tokens_entrada": consumo.tokens_entrada, "tokens_salida": consumo.tokens_salida,
                                    "costo_usd": round(consumo.costo_usd, 5), "segundos": round(time.perf_counter() - inicio, 1)}) + "\n")
                for r in respuestas:
                    f.write(json.dumps({"modelo": claude.modelo, "brazo": brazo, "texto": nombre, "lote": numero, "id": pendientes[r.agente].id,
                                        "respuestas": {f"p{i}": v for i, v in enumerate(r.respuestas, start=1)}, "valida": True}, ensure_ascii=False) + "\n")
            pendientes = [a for k, a in enumerate(pendientes) if k not in respondieron]
        with cerrojo:
            avance[0] += 1
            if avance[0] % 10 == 0 or avance[0] == len(tareas):
                print(f"  {avance[0]}/{len(tareas)} llamadas", flush=True)
        return len(pendientes)

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrencia) as grupo:
        sin_respuesta = sum(grupo.map(una, tareas))
    print(f"Listo en {time.perf_counter() - inicio:.0f} s. Sin respuesta: {sin_respuesta}. Resultados en {args.salida}")


def _con_indice(agente, k):
    """El agente con su lugar en esta llamada como índice, que es lo que devuelve `leer_lote`."""
    import dataclasses

    return dataclasses.replace(agente, indice=k)


# ---------------------------------------------------------------- informe


def indice(respuestas):
    return statistics.mean(respuestas[f"p{i}"] for i in range(1, INDICE + 1))


def postura(p1):
    return "favor" if p1 >= 5 else "contra" if p1 <= 3 else "indecisa"


def intervalo(por_lote):
    """Media de las diferencias por persona e intervalo de 95 % remuestreando lotes completos."""
    lotes = [valores for valores in por_lote.values() if valores]
    todos = [v for valores in lotes for v in valores]
    azar = random.Random(7)
    medias = []
    for _ in range(REMUESTREOS):
        muestra = [v for valores in azar.choices(lotes, k=len(lotes)) for v in valores]
        medias.append(statistics.mean(muestra))
    medias.sort()
    return statistics.mean(todos), medias[int(0.025 * REMUESTREOS)], medias[int(0.975 * REMUESTREOS) - 1]


def eta2(grupos, valores):
    """Parte de la varianza de los valores que explican los grupos, ajustada por su número."""
    media = statistics.mean(valores)
    total = sum((v - media) ** 2 for v in valores)
    por_grupo = defaultdict(list)
    for g, v in zip(grupos, valores):
        por_grupo[g].append(v)
    entre = sum(len(vs) * (statistics.mean(vs) - media) ** 2 for vs in por_grupo.values())
    if total == 0 or len(valores) <= len(por_grupo):
        return 0.0
    return max(0.0, 1 - (1 - entre / total) * (len(valores) - 1) / (len(valores) - len(por_grupo)))


def informe(args):
    filas = leer(args.salida)
    personas = {p["id"]: p for p in leer(args.salida.with_name(args.salida.stem + "_personas.jsonl"))}
    llamadas = [f for f in filas if f.get("llamada")]
    datos = defaultdict(lambda: defaultdict(dict))  # brazo -> texto -> id -> respuestas
    for f in filas:
        if "id" in f:
            datos[f["brazo"]][f["texto"]][f["id"]] = f["respuestas"]
    textos = list(dict.fromkeys(f["texto"] for f in filas if "id" in f))
    textos.sort()
    claves = sorted(next(iter(datos["completo"][textos[0]].values())))
    # Solo quienes respondieron en los tres brazos: la comparación es persona a persona.
    comunes = {t: sorted(set.intersection(*(set(datos[b][t]) for b in BRAZOS))) for t in textos}
    modelo = next(f["modelo"] for f in filas if "id" in f)
    print(f"=== {modelo} · {len(personas)} personas · textos: {', '.join(textos)} ===")
    print("Respuestas por brazo y texto (en los tres brazos):")
    for t in textos:
        print(f"  {t:<12} " + "  ".join(f"{b} {len(datos[b][t])}" for b in BRAZOS) + f"   ({len(comunes[t])})")

    if llamadas:
        print("\nConsumo por brazo:")
        for b in BRAZOS:
            suyas = [c for c in llamadas if c["brazo"] == b]
            n = sum(c["personas"] for c in suyas)
            if suyas:
                print(f"  {b:<11} {len(suyas):>3} llamadas  {sum(c['tokens_entrada'] for c in suyas) / n:6.0f} tokens de entrada por persona  "
                      f"{statistics.mean(c['segundos'] for c in suyas):5.1f} s por llamada  ${sum(c['costo_usd'] for c in suyas):.3f}")

    print("\nÍndice de aceptación (media de p1 a p4) y diferencia con el perfil completo [IC 95 %, por lotes]:")
    print(f"  {'texto':<12} completo  repetición  temático    repetición − completo        temático − completo")
    medias = {b: {} for b in BRAZOS}
    for t in textos:
        for b in BRAZOS:
            medias[b][t] = statistics.mean(indice(datos[b][t][i]) for i in comunes[t])
        difs = {}
        for b in ("completo_b", "tematico"):
            por_lote = defaultdict(list)
            for i in comunes[t]:
                por_lote[personas[i]["lote"]].append(indice(datos[b][t][i]) - indice(datos["completo"][t][i]))
            difs[b] = intervalo(por_lote)
        print(f"  {t:<12} {medias['completo'][t]:8.2f}  {medias['completo_b'][t]:10.2f}  {medias['tematico'][t]:8.2f}    "
              + "    ".join(f"{d:+.2f} [{lo:+.2f}, {hi:+.2f}]" for d, lo, hi in (difs["completo_b"], difs["tematico"])))
    print("\nOrden de los textos por índice, de mayor a menor:")
    for b in BRAZOS:
        print(f"  {b:<11} " + " > ".join(f"{t} {medias[b][t]:.2f}" for t in sorted(textos, key=lambda t: -medias[b][t])))

    print("\nDe acuerdo en p1 (5 a 7), en %:")
    for t in textos:
        print(f"  {t:<12} " + "  ".join(f"{b} {100 * statistics.mean(datos[b][t][i]['p1'] >= 5 for i in comunes[t]):5.1f}" for b in BRAZOS))

    print("\nMedia por pregunta, todos los textos juntos:")
    for b in BRAZOS:
        print(f"  {b:<11} " + "  ".join(f"{c} {statistics.mean(datos[b][t][i][c] for t in textos for i in comunes[t]):.2f}" for c in claves))
    print("Desviación estándar por pregunta (cuánto se diferencian las personas):")
    for b in BRAZOS:
        print(f"  {b:<11} " + "  ".join(f"{c} {statistics.pstdev([datos[b][t][i][c] for t in textos for i in comunes[t]]):.2f}" for c in claves))

    print("\nCoincidencia persona a persona con el perfil completo, todos los textos juntos:")
    pares = [(t, i) for t in textos for i in comunes[t]]
    for b, nombre in (("completo_b", "repetición"), ("tematico", "temático")):
        base_i = [indice(datos["completo"][t][i]) for t, i in pares]
        otro_i = [indice(datos[b][t][i]) for t, i in pares]
        base_1 = [datos["completo"][t][i]["p1"] for t, i in pares]
        otro_1 = [datos[b][t][i]["p1"] for t, i in pares]
        print(f"  {nombre:<11} correlación del índice {statistics.correlation(base_i, otro_i):.2f}   de p1 {statistics.correlation(base_1, otro_1):.2f}   "
              f"diferencia media en p1 {statistics.mean(abs(x - y) for x, y in zip(base_1, otro_1)):.2f}   "
              f"misma postura {100 * statistics.mean(postura(x) == postura(y) for x, y in zip(base_1, otro_1)):.0f} %")

    # Por persona: su índice promedio en todos los textos que respondió en los tres brazos.
    en_todos = sorted(set.intersection(*(set(comunes[t]) for t in textos)))
    propio = {b: {i: statistics.mean(indice(datos[b][t][i]) for t in textos) for i in en_todos} for b in BRAZOS}

    def grupo(i, atributo):
        if atributo == "Edad":
            edad = personas[i]["edad"]
            return "14 a 17" if edad < 18 else "18 a 29" if edad < 30 else "30 a 44" if edad < 45 else "45 a 59" if edad < 60 else "60 o más"
        return personas[i]["atributos"].get(atributo, "(sin dato)")

    print(f"\nCuánto del índice de cada persona explica cada atributo (eta² ajustado, %; {len(en_todos)} personas):")
    print(f"  {'atributo':<26} " + "  ".join(f"{b:>10}" for b in BRAZOS))
    for atributo in A_DESAGREGAR:
        grupos = [grupo(i, atributo) for i in en_todos]
        print(f"  {atributo:<26} " + "  ".join(f"{100 * eta2(grupos, [propio[b][i] for i in en_todos]):>10.1f}" for b in BRAZOS))
    for atributo in ("Posición política", "Menores en el hogar", "Situación laboral"):
        print(f"\nÍndice medio por «{atributo}»:")
        por_grupo = defaultdict(list)
        for i in en_todos:
            por_grupo[grupo(i, atributo)].append(i)
        for nombre, ids in sorted(por_grupo.items(), key=lambda par: -len(par[1])):
            print(f"  {nombre[:34]:<34} n={len(ids):<4} " + "  ".join(f"{b} {statistics.mean(propio[b][i] for i in ids):.2f}" for b in BRAZOS))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="orden", required=True)
    c = sub.add_parser("correr")
    c.add_argument("salida", type=Path)
    c.add_argument("textos", type=Path, nargs="+")
    c.add_argument("--personas", type=int, default=200)
    c.add_argument("--lote", type=int, default=20)
    c.add_argument("--concurrencia", type=int, default=10)
    c.add_argument("--modelo", default="haiku")
    i = sub.add_parser("informe")
    i.add_argument("salida", type=Path)
    args = ap.parse_args()
    (correr if args.orden == "correr" else informe)(args)


if __name__ == "__main__":
    main()
