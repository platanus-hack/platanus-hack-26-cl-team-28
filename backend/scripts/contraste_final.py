#!/usr/bin/env python3
"""Validación del motor integrado en los casos que no se usaron para ajustar nada.

Uso: uv run python scripts/contraste_final.py

Compara, con los mismos 200 agentes: el método anterior del sitio, el motor nuevo sin ancla (pregunta
directa y perfil sin etiquetas políticas) y el motor nuevo con el reparto del ancla tal como lo hace el
servidor (`servidor.ancla.Reparto`, por lotes y en el orden de llegada). No llama a ningún modelo.
"""
import json, random, sys
from pathlib import Path
import numpy as np, pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / "scripts"))
import contraste_experimentos as ex  # noqa: E402
from servidor.ancla import Reparto  # noqa: E402

pd.set_option("display.width", 300); pd.set_option("display.max_columns", 40)
ids = ex.ids_agentes()
P, Q = ex.personas(), ex.cortes_cep()
orden = {json.loads(l)["agente"]: json.loads(l)["orden"] for l in (ex.CARPETA / "personas.jsonl").read_text().splitlines()}


def anclas(nombre):
    juntas = {}
    for ruta in (RAIZ / "data" / "pruebas" / "banco" / f"{nombre}.jsonl", ex.SALIDA / f"ancla_{nombre}.jsonl"):
        if ruta.exists():
            for f in map(json.loads, ruta.read_text().splitlines()):
                juntas.setdefault(f["caso"], []).append(f["prob"])
    return {c: (float(np.mean([p[0] for p in ps])), float(np.mean([p[1] for p in ps]))) for c, ps in juntas.items()}


def repartido(R, ancla):
    """Las respuestas como las entregaría el servidor: por lotes de 20 en orden revuelto, con la escalera al inicio."""
    partes = []
    for caso, g in R.groupby("caso"):
        a, d = ancla[caso]
        g = g.assign(o=g.agente.map(orden)).sort_values("o")
        filas = list(g.itertuples(index=False))
        lotes = [filas[i:i + 2] for i in range(0, 24, 2)] + [filas[i:i + 5] for i in range(24, 64, 5)]
        resto = [filas[i:i + 20] for i in range(64, len(filas), 20)]
        random.Random(caso).shuffle(resto)
        reparto, finales = Reparto(a, d), {}
        for lote in lotes + resto:
            for f, nota in zip(lote, reparto.repartir([(f.agente, [f.p1, f.p2, f.p3, f.p4, f.p5]) for f in lote])):
                finales[f.agente] = nota
        nota = g.agente.map(finales)
        partes.append(g.assign(a=(nota >= 5) * 100.0, d=(nota <= 3) * 100.0))
    return pd.concat(partes)


for nombre, viejo, nuevo in (("prueba (42 casos del banco)", "base", "directa_sin_identidad"), ("rai (40 preguntas nuevas)", "sitio", "integrado")):
    casos = ex.elegir_casos(nombre.split()[0])
    casos = {k: c for k, c in casos.items() if k not in ex.DUDOSOS}
    filas = {}
    Rv, Rn = ex.leer(viejo, ids), ex.leer(nuevo, ids)
    Rv, Rn = Rv[Rv.caso.isin(casos)], Rn[Rn.caso.isin(casos)]
    filas["sitio anterior"], Tv = ex.medir(Rv, casos, P, Q)
    filas["motor nuevo sin ancla"], _ = ex.medir(Rn, casos, P, Q)
    tablas = {}
    for modelo in ("haiku", "opus"):
        filas[f"motor nuevo, ancla {modelo}"], tablas[modelo] = ex.medir(repartido(Rn, anclas(f"pronostico_{modelo}")), casos, P, Q)
    if "luna" in next(iter(casos.values())):
        real = np.array([c["real_acuerdo"] for c in casos.values()]); luna = np.array([c["luna"][0] for c in casos.values()])
        filas["Luna (benchmark de Rai)"] = {"casos": len(real), "EAM": abs(luna - real).mean(), "sesgo": (luna - real).mean(), "lado": 100 * ((real >= 50) == (luna >= 50)).mean(),
                                            "a≤5": 100 * (abs(luna - real) <= 5).mean(), "a≤10": 100 * (abs(luna - real) <= 10).mean()}
    print(f"\n=== {nombre} ===")
    print(pd.DataFrame(filas).T.drop(columns=["n", "sesgo≤45", "EAM≥75", "cep_casos"], errors="ignore").round(1).to_string())
    T = tablas["opus"].join(Tv[["sim"]].rename(columns={"sim": "antes"}))
    antes, ahora = abs(T.antes - T.real), abs(T.dif)
    buenos = antes <= 5
    print(f"Con ancla de Opus: mejoran {(ahora < antes - 1).sum()}, empeoran {(ahora > antes + 1).sum()}, igual {(abs(ahora - antes) <= 1).sum()}. "
          f"De los {buenos.sum()} que antes estaban a 5 puntos o menos: {(ahora[buenos] <= 5).sum()} siguen ahí, {(ahora[buenos] <= 10).sum()} a 10 o menos, {(ahora[buenos] > 10).sum()} peor que 10.")
    T["enunciado"] = [casos[c]["enunciado"][-70:] for c in T.index]
    print(T.assign(error=ahora, error_antes=antes).sort_values("error", ascending=False)[["real", "antes", "sim", "error_antes", "error", "enunciado"]].round(0).to_string())
