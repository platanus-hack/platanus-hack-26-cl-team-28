#!/usr/bin/env python3
"""Ficha de validación: cuántas encuestas reales se revisaron y a cuántos puntos queda el motor.

Uso: uv run python scripts/contraste_ficha.py
Cuenta las preguntas y las entrevistas detrás de cada fuente (cada encuesta una vez) y mide el motor
integrado (agentes Haiku, pregunta directa, perfil sin etiquetas, ancla de Opus repartida por lotes)
en los 82 casos que no se usaron para ajustar nada. No llama a ningún modelo.
"""
import json, random, sys
from pathlib import Path
import numpy as np, pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / "scripts"))
import contraste_experimentos as ex  # noqa: E402
from servidor.ancla import Reparto  # noqa: E402

BANCO = RAIZ.parent / "datos-pruebas"
fuentes = json.loads((BANCO / "fuentes.json").read_text())
rai = json.loads((BANCO / "benchmark-politicas-chile.json").read_text())["casos"]
for c in rai.values():
    fuentes.setdefault(c["fuente_id"], c["fuente"])
banco = ex.cargar_casos()
nuevos = ex.elegir_casos("rai")
usados = {c["fuente_id"] for c in banco.values()} | {c["fuente_id"] for c in nuevos.values()}
votos = {"servel-2022", "servel-2023"}
encuestas = sorted(f for f in usados | {"servel-2022", "servel-2023"} if f not in votos)
n = {f: fuentes[f].get("n_total") for f in encuestas}
print(f"Preguntas con resultado real: {len(banco)} del banco + 4 aparte (2 plebiscitos con {6_000_000:,}+ votos cada uno, 2 de paneles) + {len(nuevos)} del benchmark de Rai = {len(banco) + 4 + len(nuevos)}")
print(f"Encuestas distintas: {len(encuestas)} de {len({fuentes[f]['entidad'] for f in encuestas})} entidades; entrevistas sumadas (cada encuesta una vez): {sum(v for v in n.values() if v):,} "
      f"(sin tamaño transcrito: {[f for f, v in n.items() if not v]})")
print("Por entidad:", pd.Series({f: fuentes[f]["entidad"] for f in encuestas}).value_counts().to_dict())
print("Período:", min(str(fuentes[f].get("periodo"))[:4] for f in encuestas), "a", max(str(fuentes[f].get("periodo"))[:4] for f in encuestas))
print("Microdatos individuales: CEP 96, 1.466 entrevistas (370 cortes por segmento en 10 preguntas)")

# Errores del motor integrado en los casos de validación.
ids = ex.ids_agentes()
orden = {json.loads(l)["agente"]: json.loads(l)["orden"] for l in (ex.CARPETA / "personas.jsonl").read_text().splitlines()}
ancla = {}
for ruta in (RAIZ / "data" / "pruebas" / "banco" / "pronostico_opus.jsonl", ex.SALIDA / "ancla_pronostico_opus.jsonl"):
    for f in map(json.loads, ruta.read_text().splitlines()):
        ancla.setdefault(f["caso"], f["prob"])
filas = []
for conjunto, variante, viejo in (("prueba", "directa_sin_identidad", "base"), ("rai", "integrado", "sitio")):
    casos = {k: c for k, c in ex.elegir_casos(conjunto).items() if k not in ex.DUDOSOS}
    R, V = ex.leer(variante, ids), ex.leer(viejo, ids)
    for k, c in casos.items():
        g = R[R.caso == k].assign(o=lambda d: d.agente.map(orden)).sort_values("o")
        fs = list(g.itertuples(index=False))
        lotes = [fs[i:i + 2] for i in range(0, 24, 2)] + [fs[i:i + 5] for i in range(24, 64, 5)]
        resto = [fs[i:i + 20] for i in range(64, len(fs), 20)]
        random.Random(k).shuffle(resto)
        rp, notas = Reparto(*ancla[k]), []
        for lote in lotes + resto:
            notas += rp.repartir([(f.agente, [f.p1, f.p2, f.p3, f.p4, f.p5]) for f in lote])
        notas = np.array(notas)
        v = V[V.caso == k].p1
        filas.append({"caso": k, "conjunto": conjunto, "real": c["real_acuerdo"], "real_d": c["real_desacuerdo"],
                      "sim": 100 * (notas >= 5).mean(), "sim_d": 100 * (notas <= 3).mean(), "antes": 100 * (v >= 5).mean()})
T = pd.DataFrame(filas).set_index("caso")
T["err"], T["err_antes"] = abs(T.sim - T.real), abs(T.antes - T.real)


def resumen(e, real, sim):
    azar = np.random.default_rng(1)
    boot = [np.mean(e[azar.integers(0, len(e), len(e))]) for _ in range(4000)]
    return {"preguntas": len(e), "error medio": e.mean(), "IC 95 %": f"{np.percentile(boot, 2.5):.1f} a {np.percentile(boot, 97.5):.1f}", "mediana": np.median(e),
            "8 de cada 10 a ±": np.percentile(e, 80), "9 de cada 10 a ±": np.percentile(e, 90), "a ±5": 100 * (e <= 5).mean(), "a ±10": 100 * (e <= 10).mean(),
            "mismo lado %": 100 * ((real >= 50) == (sim >= 50)).mean()}


pd.set_option("display.width", 250)
out = {}
for nombre, g in (("prueba", T[T.conjunto == "prueba"]), ("rai", T[T.conjunto == "rai"]), ("las 82", T)):
    out[f"{nombre}, motor actual"] = resumen(g.err.to_numpy(), g.real, g.sim)
    out[f"{nombre}, motor anterior"] = resumen(g.err_antes.to_numpy(), g.real, g.antes)
print("\nError en puntos porcentuales del % de acuerdo, casos no usados para ajustar (200 agentes):")
print(pd.DataFrame(out).T.round(1).to_string())
d = T.dropna(subset=["real_d"])
print(f"\n% en desacuerdo ({len(d)} preguntas que lo publican): error medio {abs(d.sim_d - d.real_d).mean():.1f}, mediana {np.median(abs(d.sim_d - d.real_d)):.1f}")
T.round(1).to_csv(ex.CARPETA / "ficha_validacion.csv")
