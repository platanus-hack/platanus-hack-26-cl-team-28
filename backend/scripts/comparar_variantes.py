#!/usr/bin/env python3
"""Compara las variantes de una política a partir de los resultados de scripts/probar_modelo.py.

Uso:
    uv run python -I scripts/comparar_variantes.py PERSONAS RESULTADOS [RESULTADOS ...]

Cada archivo de resultados es una corrida (un modelo y una redacción). Para cada una imprime:
  - la aceptación nacional de cada variante, ponderada por "peso";
  - el ranking, y entre variantes vecinas si la diferencia se distingue de cero;
  - el efecto de cada atributo, comparando las variantes que solo difieren en él;
  - qué variante gana en cada región y en cada grupo de personas.
Con varias corridas, dice al final si el ranking se mantiene entre ellas.

Un archivo sin variantes (un solo texto) se trata como corrida de validación y se compara
con las encuestas reales de benchmarks.json. Lo mismo un archivo con una pregunta de
alternativas.

Nada de esto depende del tema. Lo propio de cada caso se lee de su carpeta, que por defecto
es la del primer archivo de resultados (ver data/pruebas/README.md):
  benchmarks.json          cifras reales para validar
  variantes/atributos.json qué atributos tiene cada variante

Las diferencias son pareadas: las mismas personas contestaron todas las variantes con la
misma semilla. El intervalo es un bootstrap de personas dentro de cada región.

Si las respuestas vienen de subagentes por lotes (campo "lote"), las de un mismo lote no son
independientes: el intervalo remuestrea lotes completos, y se informa cuánto varía el índice
de un lote a otro. Con pocos lotes el intervalo es ancho, y así debe ser.

Si p1 se preguntó primero, su porcentaje de acuerdo sale de las probabilidades del modelo
(logprobs) y no de la respuesta sorteada: es la misma cifra sin el ruido del sorteo.

Opciones:
    --grupos ATRIBUTO    atributos de "grupos" para desagregar; se puede repetir
    --caso CARPETA       carpeta del caso; por defecto, la del primer archivo de resultados
    --benchmarks RUTA    por defecto, benchmarks.json en la carpeta del caso
    --atributos RUTA     por defecto, variantes/atributos.json en la carpeta del caso
    --remuestreos N      repeticiones del bootstrap (por defecto 2000)
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

# Preguntas que forman el índice de aceptación: apoyo, justicia, confianza y efectividad.
INDICE = ["p1", "p2", "p3", "p4"]
GRUPOS = ["Edad", "Género", "Tramo socioeconómico", "Situación laboral", "Menores en el hogar", "Posición política"]
MINIMO_GRUPO = 30


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(linea) for linea in f if linea.strip()]


def medidas(r):
    """Lo que se compara de cada respuesta. Las cifras *_lp vienen de los logprobs de p1."""
    resp = r["respuestas"]
    m = {
        "indice": sum(resp[c] for c in INDICE) / len(INDICE),
        "acuerdo": 100.0 * (resp["p1"] >= 5),
        "desacuerdo": 100.0 * (resp["p1"] <= 3),
        **{c: float(v) for c, v in resp.items()},
    }
    dist = r.get("distribuciones")
    # Solo la primera respuesta tiene una distribución que no depende de las respuestas anteriores.
    if dist and (r.get("orden") or "1").split(",")[0] == "1":
        m["acuerdo_lp"] = 100 * sum(dist[0][4:])
        m["desacuerdo_lp"] = 100 * sum(dist[0][:3])
    return m


class Corrida:
    """Una corrida: para cada variante, las medidas de las personas que contestaron todas."""

    def __init__(self, ruta, personas):
        registros = [r for r in leer(ruta) if r.get("valida") and not r.get("repeticion")]
        self.nombre = Path(ruta).name
        self.modelo = registros[0].get("modelo", "?") if registros else "?"
        self.redaccion = registros[0].get("redaccion") if registros else None
        self.politica = registros[0].get("politica") if registros else None
        por_variante = defaultdict(dict)
        lote_de = {}
        for r in registros:
            por_variante[r.get("variante")][r["id"]] = medidas(r)
            if "lote" in r:
                lote_de[r["id"]] = r["lote"]
        self.variantes = list(por_variante)
        comunes = set.intersection(*(set(v) for v in por_variante.values())) if por_variante else set()
        self.personas = [p for p in personas if p["id"] in comunes]
        self.pesos = np.array([p.get("peso", 1) for p in self.personas], dtype=float)
        self.regiones = np.array([p.get("grupos", {}).get("Región", "") for p in self.personas])
        # Lote del subagente que contestó por cada persona; None si cada respuesta fue una llamada aparte.
        self.lotes = np.array([lote_de[p["id"]] for p in self.personas]) if lote_de else None
        self.datos = {
            v: {m: np.array([por_variante[v][p["id"]].get(m, np.nan) for p in self.personas]) for m in self.claves(por_variante[v])}
            for v in self.variantes
        }
        self.con_logprobs = all("acuerdo_lp" in self.datos[v] for v in self.variantes)

    @staticmethod
    def claves(por_id):
        return list(dict.fromkeys(m for medidas_ in por_id.values() for m in medidas_))

    def media(self, variante, medida, filtro=None):
        x, w = self.datos[variante][medida], self.pesos
        if filtro is not None:
            x, w = x[filtro], w[filtro]
        return float((x * w).sum() / w.sum())

    def acuerdo(self, variante, filtro=None):
        return self.media(variante, "acuerdo_lp" if self.con_logprobs else "acuerdo", filtro)

    def desacuerdo(self, variante, filtro=None):
        return self.media(variante, "desacuerdo_lp" if self.con_logprobs else "desacuerdo", filtro)

    def diferencia(self, a, b, medida, remuestreos, rng):
        """Media pareada de a - b con intervalo de 95 %.

        Remuestrea personas dentro de cada región o, si hay lotes de subagentes, lotes completos."""
        d, w = self.datos[a][medida] - self.datos[b][medida], self.pesos
        if self.lotes is not None:
            lotes = sorted(set(self.lotes))
            sumas = np.array([[(d * w)[self.lotes == k].sum(), w[self.lotes == k].sum()] for k in lotes])
            elegidos = rng.integers(0, len(lotes), (remuestreos, len(lotes)))
            bajo, alto = np.percentile(sumas[elegidos, 0].sum(axis=1) / sumas[elegidos, 1].sum(axis=1), [2.5, 97.5])
            return float((d * w).sum() / w.sum()), float(bajo), float(alto)
        bloques = [np.flatnonzero(self.regiones == r) for r in dict.fromkeys(self.regiones)]
        numerador, denominador = np.zeros(remuestreos), np.zeros(remuestreos)
        for bloque in bloques:
            elegidos = bloque[rng.integers(0, len(bloque), (remuestreos, len(bloque)))]
            numerador += (d[elegidos] * w[elegidos]).sum(axis=1)
            denominador += w[elegidos].sum(axis=1)
        bajo, alto = np.percentile(numerador / denominador, [2.5, 97.5])
        return float((d * w).sum() / w.sum()), float(bajo), float(alto)

    def ranking(self, filtro=None):
        return sorted(self.variantes, key=lambda v: -self.media(v, "indice", filtro))


def referencia_de(benchmarks, tipo, nombre):
    """La cifra real de este texto o pregunta; si el archivo no dice cuál es y hay una sola, esa."""
    candidatas = (benchmarks or {}).get(tipo, {})
    if nombre in candidatas:
        return candidatas[nombre]
    return next(iter(candidatas.values())) if nombre is None and len(candidatas) == 1 else None


def validar(corrida, benchmarks):
    v = corrida.variantes[0]
    fuente = "logprobs de p1" if corrida.con_logprobs else "respuestas sorteadas"
    acuerdo, desacuerdo = corrida.acuerdo(v), corrida.desacuerdo(v)
    print(f"Validación con {len(corrida.personas)} personas ({fuente}):")
    print(f"  p1 de acuerdo {acuerdo:.1f} %   en desacuerdo {desacuerdo:.1f} %   índice ({', '.join(INDICE)}) {corrida.media(v, 'indice'):.2f}")
    referencia = referencia_de(benchmarks, "cerradas", corrida.politica)
    if not referencia:
        print("  Sin cifra real con que comparar en benchmarks.json.")
        return
    bajo, alto = referencia["acuerdo"]
    print(f"  Encuestas reales: {bajo} a {alto} % de acuerdo y {referencia['desacuerdo']} % en desacuerdo")
    distancia = bajo - acuerdo if acuerdo < bajo else acuerdo - alto if acuerdo > alto else 0
    sanidad = benchmarks.get("rango_sanidad", {})
    if acuerdo > sanidad.get("tope_sospechoso", 100):
        print(f"  NO PASA: sobre {sanidad['tope_sospechoso']} % el modelo está sesgado hacia el acuerdo.")
    elif distancia <= 5:
        print(f"  PASA: el acuerdo queda a {distancia:.1f} puntos del rango real.")
    else:
        print(f"  NO PASA: el acuerdo queda a {distancia:.1f} puntos del rango real ({'bajo' if acuerdo < bajo else 'sobre'} él).")
    print(f"  Desacuerdo: {desacuerdo - referencia['desacuerdo']:+.1f} puntos respecto de la encuesta.")


def validar_alternativas(registros, personas, benchmarks):
    """Reparto ponderado de una pregunta de alternativas, frente a la encuesta real si las claves coinciden."""
    pesos = {p["id"]: p.get("peso", 1) for p in personas}
    validos = [r for r in registros if r.get("valida") and r["id"] in pesos]
    total = sum(pesos[r["id"]] for r in validos)
    usa_logprobs = all(r.get("probabilidades") for r in validos)
    reparto = defaultdict(float)
    for r in validos:
        if usa_logprobs:
            for clave, p in r["probabilidades"].items():
                reparto[clave] += 100 * p * pesos[r["id"]] / total
        else:
            reparto[r["eleccion"]] += 100 * pesos[r["id"]] / total
    referencia = referencia_de(benchmarks, "alternativas", registros[0].get("pregunta")) or {}
    print(f"Pregunta de alternativas con {len(validos)} personas ({'logprobs' if usa_logprobs else 'respuestas elegidas'}):")
    for clave, valor in sorted(reparto.items(), key=lambda x: -x[1]):
        real = f"   encuesta real: {referencia[clave]} %" if clave in referencia else ""
        print(f"  {clave:<32} {valor:5.1f} %{real}")
    reales = {c: v for c, v in referencia.items() if c in reparto}
    if len(reales) == 2:
        (a, va), (b, vb) = reales.items()
        print(f"  Entre quienes eligen una de las dos: {a} {100 * reparto[a] / (reparto[a] + reparto[b]):.0f} % en la simulación y {100 * va / (va + vb):.0f} % en la encuesta.")


def contrastes(atributos):
    """Pares de variantes que difieren en un solo atributo, y los atributos que nunca se separan."""
    letras = list(atributos)
    nombres = [n for n in atributos[letras[0]] if n != "nombre"]
    pares = []
    for i, a in enumerate(letras):
        for b in letras[i + 1 :]:
            distintos = [n for n in nombres if atributos[a][n] != atributos[b][n]]
            if len(distintos) == 1:
                n = distintos[0]
                pares.append((n, a, b, f"{atributos[a][n]} -> {atributos[b][n]}"))
    confundidos = []
    for i, n in enumerate(nombres):
        for m in nombres[i + 1 :]:
            juntos = {(atributos[v][n], atributos[v][m]) for v in letras}
            if len(juntos) == len({atributos[v][n] for v in letras}) == len({atributos[v][m] for v in letras}):
                confundidos.append((n, m))
    return pares, confundidos


def comparar(corrida, atributos, grupos, benchmarks, remuestreos, rng):
    variantes = corrida.ranking()
    pesos = corrida.pesos
    efectivo = pesos.sum() ** 2 / (pesos**2).sum()
    print(f"{len(corrida.personas)} personas contestaron las {len(variantes)} variantes (tamaño efectivo nacional: {efectivo:.0f}).")
    fuente = "logprobs" if corrida.con_logprobs else "respuestas sorteadas"
    if corrida.lotes is not None:
        lotes = sorted(set(corrida.lotes))
        entre = [np.std([corrida.datos[v]["indice"][corrida.lotes == k].mean() for k in lotes], ddof=1) for v in variantes]
        print(f"Respuestas de subagentes en {len(lotes)} lotes: el índice de una misma variante cambia {np.mean(entre):.2f} puntos (desviación) de un lote a otro.")
        print("Los intervalos remuestrean lotes completos.")

    print(f"\nAceptación nacional, de mayor a menor índice (p1 de acuerdo y en desacuerdo según {fuente}):")
    preguntas = sorted(c for c in corrida.datos[variantes[0]] if c[0] == "p" and c[1:].isdigit())
    print("  variante                índice   p1 acuerdo  p1 desacuerdo   media de " + "  ".join(f"{c:>5}" for c in preguntas))
    sanidad = (benchmarks or {}).get("rango_sanidad", {})
    for v in variantes:
        nombre = f"{v} · {atributos[v]['nombre']}" if atributos and v in atributos else v
        fila = " " * 9 + "  ".join(f"{corrida.media(v, c):>5.2f}" for c in preguntas)
        aviso = "  <- sobre el tope de sanidad" if corrida.acuerdo(v) > sanidad.get("tope_sospechoso", 100) else ""
        print(f"  {nombre:<22}  {corrida.media(v, 'indice'):>6.2f}  {corrida.acuerdo(v):>9.1f} %  {corrida.desacuerdo(v):>11.1f} %  {fila}{aviso}")

    print("\nRanking por índice (> si la diferencia pareada se distingue de cero al 95 %; ≈ si no):")
    partes = [variantes[0]]
    for a, b in zip(variantes, variantes[1:]):
        _, bajo, alto = corrida.diferencia(a, b, "indice", remuestreos, rng)
        partes += [">" if bajo > 0 or alto < 0 else "≈", b]
    print("  " + " ".join(partes))
    mejor, peor = variantes[0], variantes[-1]
    d, bajo, alto = corrida.diferencia(mejor, peor, "indice", remuestreos, rng)
    print(f"  {mejor} - {peor}: {d:+.2f} puntos de índice (IC 95 %: {bajo:+.2f} a {alto:+.2f})")

    if atributos:
        pares, confundidos = contrastes({v: atributos[v] for v in corrida.variantes if v in atributos})
        print("\nEfecto de cada atributo (variantes que solo difieren en él; diferencia de la segunda menos la primera):")
        medida_acuerdo = "acuerdo_lp" if corrida.con_logprobs else "acuerdo"
        for atributo, a, b, cambio in pares:
            d, bajo, alto = corrida.diferencia(b, a, "indice", remuestreos, rng)
            da, bajo_a, alto_a = corrida.diferencia(b, a, medida_acuerdo, remuestreos, rng)
            print(f"  {atributo:<14} {a}->{b}  {cambio:<26} índice {d:+.2f} ({bajo:+.2f} a {alto:+.2f})   p1 acuerdo {da:+.1f} pts ({bajo_a:+.1f} a {alto_a:+.1f})")
        for n, m in confundidos:
            print(f"  AVISO: {n} y {m} cambian siempre juntos en estas variantes; su efecto no se puede separar.")

    print("\nPor región (índice de cada variante; n sin ponderar):")
    print(f"  {'región':<42} {'n':>4}  " + "  ".join(f"{v:>5}" for v in variantes) + "   gana")
    gana, mantiene = defaultdict(int), 0
    for region in dict.fromkeys(corrida.regiones):
        filtro = corrida.regiones == region
        orden = corrida.ranking(filtro)
        gana[orden[0]] += 1
        mantiene += corrida.media(mejor, "indice", filtro) > corrida.media(peor, "indice", filtro)
        fila = "  ".join(f"{corrida.media(v, 'indice', filtro):>5.2f}" for v in variantes)
        print(f"  {region[:42]:<42} {int(filtro.sum()):>4}  {fila}   {orden[0]}")
    n_regiones = len(set(corrida.regiones))
    print("  Regiones que gana cada variante: " + ", ".join(f"{v} {n}" for v, n in sorted(gana.items(), key=lambda x: -x[1])))
    print(f"  {mejor} supera a {peor} en {mantiene} de {n_regiones} regiones.")

    for atributo in grupos:
        valores = np.array([p.get("grupos", {}).get(atributo, "(sin dato)") for p in corrida.personas])
        if len(set(valores)) < 2:
            continue
        print(f"\nPor «{atributo}» (índice de cada variante; grupos con al menos {MINIMO_GRUPO} personas):")
        print(f"  {'':<36} {'n':>4}  " + "  ".join(f"{v:>5}" for v in variantes) + "   gana   mejor - peor")
        for valor in sorted(set(valores)):
            filtro = valores == valor
            if filtro.sum() < MINIMO_GRUPO:
                continue
            medias = {v: corrida.media(v, "indice", filtro) for v in variantes}
            orden = sorted(medias, key=lambda v: -medias[v])
            fila = "  ".join(f"{medias[v]:>5.2f}" for v in variantes)
            print(f"  {valor[:36]:<36} {int(filtro.sum()):>4}  {fila}   {orden[0]:<5}  {medias[orden[0]] - medias[orden[-1]]:.2f}")
    return variantes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("personas", type=Path)
    ap.add_argument("resultados", type=Path, nargs="+")
    ap.add_argument("--grupos", action="append")
    ap.add_argument("--benchmarks", type=Path)
    ap.add_argument("--atributos", type=Path)
    ap.add_argument("--caso", type=Path)
    ap.add_argument("--remuestreos", type=int, default=2000)
    args = ap.parse_args()

    personas = leer(args.personas)
    caso = args.caso or args.resultados[0].parent
    ruta_benchmarks = args.benchmarks or caso / "benchmarks.json"
    benchmarks = json.loads(ruta_benchmarks.read_text(encoding="utf-8")) if ruta_benchmarks.exists() else None
    ruta_atributos = args.atributos or caso / "variantes" / "atributos.json"
    atributos = json.loads(ruta_atributos.read_text(encoding="utf-8")) if ruta_atributos.exists() else None
    rng = np.random.default_rng(2024)

    rankings = {}
    for ruta in args.resultados:
        crudos = leer(ruta)
        if any("eleccion" in r for r in crudos):
            print(f"\n===== {Path(ruta).name} ({crudos[0].get('modelo', '?')}) =====")
            validar_alternativas(crudos, personas, benchmarks)
            continue
        corrida = Corrida(ruta, personas)
        redaccion = f", redacción {corrida.redaccion}" if corrida.redaccion else ""
        print(f"\n===== {corrida.nombre} ({corrida.modelo}{redaccion}) =====")
        if not corrida.personas:
            print("Sin respuestas válidas para estas personas.")
        elif corrida.variantes == [None]:
            validar(corrida, benchmarks)
        else:
            rankings[corrida.nombre] = comparar(corrida, atributos, args.grupos or GRUPOS, benchmarks, args.remuestreos, rng)

    if len(rankings) > 1:
        print("\n===== ¿Se mantiene el ranking entre corridas? =====")
        for nombre, orden in rankings.items():
            print(f"  {' > '.join(orden):<24} {nombre}")
        ordenes = list(rankings.values())
        if all(o == ordenes[0] for o in ordenes):
            print("  Sí: el orden completo es el mismo en todas.")
        else:
            primeras, ultimas = {o[0] for o in ordenes}, {o[-1] for o in ordenes}
            print(f"  No: el orden completo cambia. La primera es {'siempre ' + next(iter(primeras)) if len(primeras) == 1 else 'distinta según la corrida'}"
                  f" y la última es {'siempre ' + next(iter(ultimas)) if len(ultimas) == 1 else 'distinta según la corrida'}.")
            print("  Según la regla de la sección 6.2, solo se reporta lo que coincide.")


if __name__ == "__main__":
    main()
