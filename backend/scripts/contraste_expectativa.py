#!/usr/bin/env python3
"""Análisis de la pregunta de expectativa: ¿el % que los agentes creen que apoya acierta mejor que su propia opinión?

Uso: uv run python scripts/contraste_expectativa.py [--casos dev|prueba|rai]
Compara, por caso: la opinión propia de los agentes (notas o probabilidades), su expectativa media, el
pronóstico de Opus (el ancla) y combinaciones. No llama a ningún modelo.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / "scripts"))
import contraste_experimentos as ex  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--casos", default="dev"); args = ap.parse_args()
casos = {k: c for k, c in ex.elegir_casos(args.casos).items() if k not in ex.DUDOSOS}
ids = ex.ids_agentes()
real = pd.Series({k: c["real_acuerdo"] for k, c in casos.items()})


def pron(nombre):
    juntas = {}
    for ruta in (RAIZ / "data" / "pruebas" / "banco" / f"{nombre}.jsonl", ex.SALIDA / f"ancla_{nombre}.jsonl"):
        if ruta.exists():
            for f in map(json.loads, ruta.read_text().splitlines()):
                juntas.setdefault(f["caso"], []).append(f["prob"][0])
    return pd.Series({c: np.mean(v) for c, v in juntas.items()})


E_ = ex.leer("expectativa", ids); E_ = E_[E_.caso.isin(casos)]
B = ex.leer("prob_expectativa", ids); B = B[B.caso.isin(casos)]
I = ex.leer({"prueba": "directa_sin_identidad", "rai": "integrado"}.get(args.casos, "integrado"), ids); I = I[I.caso.isin(casos)]
S = {
    "agentes, notas (motor sin ancla)": I.groupby("caso").p1.apply(lambda s: 100 * (s >= 5).mean()),
    "agentes, notas + expectativa (misma llamada)": E_.groupby("caso").p1.apply(lambda s: 100 * (s >= 5).mean()),
    "agentes, probabilidades": B.groupby("caso").p1.mean(),
    "expectativa media (variante notas)": E_.groupby("caso").e.mean(),
    "expectativa media (variante prob.)": B.groupby("caso").e.mean(),
    "ancla Opus": pron("pronostico_opus"),
    "ancla Haiku": pron("pronostico_haiku"),
}
S["mitad opinión, mitad expectativa"] = (S["agentes, notas + expectativa (misma llamada)"] + S["expectativa media (variante notas)"]) / 2
S["mitad Opus, mitad expectativa"] = (S["ancla Opus"] + S["expectativa media (variante notas)"]) / 2
filas = {}
for n, s in S.items():
    s = s.reindex(real.index)
    d = (s - real).dropna()
    filas[n] = {"casos": len(d), "EAM": abs(d).mean(), "sesgo": d.mean(), "a≤5 %": 100 * (abs(d) <= 5).mean(), "a≤10 %": 100 * (abs(d) <= 10).mean(),
                "mismo lado %": 100 * ((real[d.index] >= 50) == (s[d.index] >= 50)).mean(), "r": real[d.index].corr(s[d.index]),
                "desv. entre casos": s[d.index].std()}
pd.set_option("display.width", 250)
print(f"Casos: {args.casos} ({len(real)}). Desviación real entre casos: {real.std():.1f}\n")
print(pd.DataFrame(filas).T.round(1).to_string())
# ¿Dónde ayuda la expectativa? Casos borde: donde opinión de los agentes y ancla discrepan mucho.
T = pd.DataFrame({"real": real, "opus": S["ancla Opus"], "exp": S["expectativa media (variante notas)"], "agentes": S["agentes, notas + expectativa (misma llamada)"]}).dropna()
T["discrepa"] = abs(T.opus - T.agentes)
for lo, hi in ((0, 10), (10, 20), (20, 101)):
    g = T[(T.discrepa >= lo) & (T.discrepa < hi)]
    if len(g):
        print(f"  |Opus - agentes| {lo}-{hi}: n={len(g):<3} error agentes {abs(g.agentes - g.real).mean():5.1f}  Opus {abs(g.opus - g.real).mean():5.1f}  expectativa {abs(g.exp - g.real).mean():5.1f}  "
              f"mitad Opus y expectativa {abs((g.opus + g.exp) / 2 - g.real).mean():5.1f}")
T["d_opus_exp"] = abs(T.opus - T.exp)
for lo, hi in ((0, 8), (8, 15), (15, 101)):
    g = T[(T.d_opus_exp >= lo) & (T.d_opus_exp < hi)]
    if len(g):
        print(f"  |Opus - expectativa| {lo}-{hi}: n={len(g):<3} error Opus {abs(g.opus - g.real).mean():5.1f}  expectativa {abs(g.exp - g.real).mean():5.1f}  mitad {abs((g.opus + g.exp) / 2 - g.real).mean():5.1f}")
print("\nCaso por caso (real, agentes, expectativa, Opus):")
print(T.sort_values("real")[["real", "agentes", "exp", "opus"]].round(0).to_string())
