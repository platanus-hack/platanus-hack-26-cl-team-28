#!/usr/bin/env python3
"""Análisis del contraste entre el pipeline del sitio y las encuestas reales.

Uso:
    uv run python scripts/contraste_analisis.py > data/pruebas/realidad_1000/analisis.txt

Lee lo que dejó `contraste_realidad.py correr` (1.000 agentes, 1 por cada 1.000) y lo compara con:
el porcentaje nacional publicado de cada caso, los cortes publicados por segmento
(../datos-pruebas/segmentacion.jsonl) y los microdatos de la CEP 96 (data/cep96), que permiten
abrir diez preguntas por sexo, edad, educación, zona, posición política, voto y más.
No llama a ningún modelo.
"""

import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "scripts"))
CARPETA = RAIZ / "data" / "pruebas" / "realidad_1000"
BANCO = RAIZ.parent / "datos-pruebas"

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 40)
pd.set_option("display.float_format", lambda v: f"{v:.1f}")

MACROZONA = {15: "Norte", 1: "Norte", 2: "Norte", 3: "Norte", 4: "Norte", 5: "Centro", 6: "Centro", 7: "Centro", 16: "Centro", 8: "Centro",
             13: "RM", 9: "Sur", 14: "Sur", 10: "Sur", 11: "Sur", 12: "Sur"}


def titulo(texto):
    print(f"\n\n{'=' * 100}\n{texto}\n{'=' * 100}")


def tramo_edad(e):
    return "18-29" if e < 30 else "30-44" if e < 45 else "45-59" if e < 60 else "60+"


def politica3(pos):
    """Posición en la escala de 1 a 10 como la agrupa el sitio: 1 a 4, 5 y 6, 7 a 10, o no se ubica."""
    if pos is None or (isinstance(pos, float) and math.isnan(pos)) or pos <= 0:
        return "No se ubica"
    return "Izquierda (1-4)" if pos <= 4 else "Centro (5-6)" if pos <= 6 else "Derecha (7-10)"


def metricas(real, sim):
    real, sim = np.asarray(real, float), np.asarray(sim, float)
    d = sim - real
    r = float(np.corrcoef(real, sim)[0, 1]) if len(d) > 2 and sim.std() > 0 and real.std() > 0 else float("nan")
    return {"n": len(d), "EAM": abs(d).mean(), "sesgo": d.mean(), "RECM": (d ** 2).mean() ** 0.5, "r": r,
            "a10": 100 * (abs(d) <= 10).mean(), "a5": 100 * (abs(d) <= 5).mean(), "lado": 100 * ((real >= 50) == (sim >= 50)).mean()}


def fila(nombre, m):
    return (f"{nombre:<44} n={m['n']:<4} EAM {m['EAM']:5.1f}  sesgo {m['sesgo']:+6.1f}  RECM {m['RECM']:5.1f}  r {m['r']:5.2f}  "
            f"a ≤5 pts {m['a5']:3.0f} %  a ≤10 pts {m['a10']:3.0f} %  mismo lado {m['lado']:3.0f} %")


# ---------------------------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------------------------
casos = {c["id"]: c for c in json.loads((CARPETA / "casos.json").read_text(encoding="utf-8"))}
fuentes = json.loads((BANCO / "fuentes.json").read_text(encoding="utf-8"))
rasgos = {}
ruta_rasgos = RAIZ / "data" / "pruebas" / "banco" / "rasgos.jsonl"
if ruta_rasgos.exists():
    rasgos = {f["caso"]: f for f in map(json.loads, ruta_rasgos.read_text(encoding="utf-8").splitlines())}

personas = []
for linea in (CARPETA / "personas.jsonl").read_text(encoding="utf-8").splitlines():
    f = json.loads(linea)
    g, x = f["grupos"], f["fila"]
    personas.append({
        "agente": f["agente"], "orden": f["orden"], "edad_n": f["edad"],
        "sexo": "Mujeres" if f["genero"] == 0 else "Hombres",
        "edad": tramo_edad(f["edad"]),
        "educacion": g.get("Nivel educacional") or "Sin dato",
        "quintil": f"Quintil {f['quintil'] + 1}",
        "gse3": "Bajo (Q1-2)" if f["quintil"] <= 1 else "Medio (Q3-4)" if f["quintil"] <= 3 else "Alto (Q5)",
        "zona": g.get("Zona"),
        "macrozona": MACROZONA.get(x["region"]),
        "region": g.get("Región"),
        "politica": politica3(x.get("posicion_politica")),
        "gobierno": {1: "Aprueba a Kast", 2: "Desaprueba a Kast", 3: "Ni aprueba ni desaprueba"}.get(x.get("aprueba_gobierno"), "No sabe"),
        "voto": {1: "Votó Jara", 2: "Votó Kast", 3: "Blanco o nulo", 4: "Blanco o nulo"}.get(x.get("voto_segunda_vuelta_2025"), "No votó o no responde"),
        "religion": g.get("Religión"),
        "trabajo": {1: "Trabaja", 2: "Busca trabajo", 3: "No trabaja ni busca"}.get(x.get("sit_fuerza_trabajo"), "Sin dato"),
        "menores": "Sin dato" if g.get("Menores en el hogar") in (None, "Sin dato") else "Sin menores" if g.get("Menores en el hogar") == "Sin menores" else "Con menores de 18",
        "salud": g.get("Previsión de salud"),
        "vivienda": g.get("Tenencia de la vivienda"),
        "interes": {1: "Interés alto", 2: "Interés alto", 3: "Interés medio", 4: "Interés bajo o nulo", 5: "Interés bajo o nulo"}.get(x.get("interes_politica"), "Sin dato"),
        "nacionalidad": "Extranjera" if x.get("p27_nacionalidad") == 3 else "Chilena",
        **{k: x.get(k) for k in ("menos_estado_economia", "estado_burocracia", "reducir_gasto_publico", "inmigrantes_criminalidad", "inmigrantes_aporte", "posicion_politica")},
    })
P = pd.DataFrame(personas).set_index("agente")
DIMENSIONES = ["sexo", "edad", "educacion", "gse3", "zona", "macrozona", "politica", "gobierno", "voto", "religion", "trabajo", "menores", "salud", "vivienda", "interes", "nacionalidad"]

filas, llamadas = [], []
for linea in (CARPETA / "respuestas.jsonl").read_text(encoding="utf-8").splitlines():
    f = json.loads(linea)
    if "notas" in f:
        filas.append({"caso": f["caso"], "agente": f["agente"], "lote": f["lote"], **{f"p{i + 1}": v for i, v in enumerate(f["notas"])}})
    elif f.get("llamada"):
        llamadas.append(f)
R = pd.DataFrame(filas).drop_duplicates(["caso", "agente"])
R = R[R.caso.isin(casos)]
R["a"] = (R.p1 >= 5) * 100.0
R["d"] = (R.p1 <= 3) * 100.0
R["n4"] = (R.p1 == 4) * 100.0
R = R.join(P, on="agente")

titulo("0. LA CORRIDA")
L = pd.DataFrame(llamadas)
print(f"Casos con respuestas: {R.caso.nunique()} de {len(casos)}. Respuestas: {len(R)} ({len(R) / (len(casos) * len(P)) * 100:.2f} % de {len(casos)} x {len(P)}).")
print(f"Llamadas: {len(L)}, media {L.segundos.mean():.1f} s, tokens de entrada {L.tokens_entrada.sum() / 1e6:.1f} M, de salida {L.tokens_salida.sum() / 1e6:.1f} M, costo informado por la CLI US$ {L.costo_usd.sum():.2f}")
incompletos = R.groupby("caso").size()
print("Casos con menos de 990 respuestas:", incompletos[incompletos < 990].to_dict())
print(f"Distribución de la nota de p1 en todas las respuestas (%): {(R.p1.value_counts(normalize=True).sort_index() * 100).round(1).to_dict()}")

titulo("0.1 LA MUESTRA: 1.000 agentes a 1 por cada 1.000, contra la CEP 96 ponderada")
cep = pd.read_parquet(RAIZ / "data" / "cep96" / "cep96.parquet")
C = pd.DataFrame({
    "w": cep.pond,
    "sexo": cep.sexo.map({1: "Hombres", 2: "Mujeres"}),
    "edad": cep.edad.map(tramo_edad),
    "educacion": cep.esc_nivel_1_c.map(lambda v: "Básica o menos" if v <= 3 else "Superior" if v in (6, 8, 9, 10) else "Media"),
    "gse3": cep.gse.map({1: "Alto (ABC1-C2)", 2: "Alto (ABC1-C2)", 3: "Medio (C3)", 4: "Bajo (D-E)", 5: "Bajo (D-E)"}),
    "zona": cep.zona_u_r.map({1: "Urbana", 2: "Rural"}),
    "macrozona": cep.region_3.map(MACROZONA),
    "politica": cep.iden_pol_2.map(politica3),
    "gobierno": cep.eval_gob_1.map({1: "Aprueba a Kast", 2: "Desaprueba a Kast", 3: "Ni aprueba ni desaprueba"}).fillna("No sabe"),
    "voto": cep.elec_pres_155.map({1: "Votó Jara", 2: "Votó Kast", 3: "Blanco o nulo", 4: "Blanco o nulo"}).fillna("No votó o no responde"),
    "religion": cep.religion_82.map(lambda v: "Católica" if v == 1 else "Evangélica" if v == 2 else "Ninguna" if v in (9, 10, 11) else "Otra"),
    "trabajo": cep.info_enc_35.map({1: "Trabaja", 2: "Busca trabajo", 3: "No trabaja ni busca"}).fillna("Sin dato"),
    "interes": cep.interes_pol_1_b.map({1: "Interés alto", 2: "Interés alto", 3: "Interés medio", 4: "Interés bajo o nulo", 5: "Interés bajo o nulo"}).fillna("Sin dato"),
})
P["religion3"] = P.religion.map(lambda v: v if v in ("Católica", "Evangélica", "Ninguna") else "Otra")
for dim in ["sexo", "edad", "educacion", "zona", "macrozona", "politica", "gobierno", "voto", "trabajo", "interes"]:
    m = (P[dim].value_counts(normalize=True) * 100).rename("muestra")
    c = (C.groupby(dim).w.sum() / C.w.sum() * 100).rename("CEP")
    print(f"\n{dim}:\n{pd.concat([m, c], axis=1).round(1).to_string()}")
print("\nReligión de los agentes:", (P.religion.value_counts(normalize=True) * 100).round(1).to_dict())
print("Quintil de los agentes:", (P.quintil.value_counts(normalize=True).sort_index() * 100).round(1).to_dict())

# ---------------------------------------------------------------------------------------------
# 1. Nacional
# ---------------------------------------------------------------------------------------------
T = R.groupby("caso").agg(n=("a", "size"), sim=("a", "mean"), sim_d=("d", "mean"), sim_4=("n4", "mean"),
                          p1=("p1", "mean"), p2=("p2", "mean"), p3=("p3", "mean"), p4=("p4", "mean"), p5=("p5", "mean"))
for campo in ("real_acuerdo", "real_desacuerdo", "area", "familia", "fuente_id", "tipo", "parte", "grupo", "enunciado"):
    T[campo] = [casos[c].get(campo) for c in T.index]
T = T.rename(columns={"real_acuerdo": "real", "real_desacuerdo": "real_d"})
T["real_d"] = T.real_d.astype(float)
T["dif"] = T.sim - T.real
T["dif_d"] = T.sim_d - T.real_d
T["real_neto"] = 100 * T.real / (T.real + T.real_d)
T["sim_neto"] = 100 * T.sim / (T.sim + T.sim_d)
T["dif_neto"] = T.sim_neto - T.real_neto
T["anio"] = [str(fuentes.get(f, {}).get("periodo") or "")[:4] or "s/f" for f in T.fuente_id]
T["metodo_fuente"] = [("Telefónica" if "telef" in (fuentes.get(f, {}).get("metodo") or "").lower() else
                       "Panel web" if "panel" in (fuentes.get(f, {}).get("metodo") or "").lower() or "línea" in (fuentes.get(f, {}).get("metodo") or "").lower() else
                       "Cara a cara" if "cara" in (fuentes.get(f, {}).get("metodo") or "").lower() else "Otro") for f in T.fuente_id]
T["rasgo"] = [rasgos.get(c, {}).get("tipo", "s/d") for c in T.index]
T["transversal"] = [rasgos.get(c, {}).get("transversal", np.nan) for c in T.index]
T["sello"] = [rasgos.get(c, {}).get("sello") for c in T.index]
T["banda"] = pd.cut(T.real, [0, 35, 50, 65, 80, 100], labels=["0-35", "35-50", "50-65", "65-80", "80-100"])
T.to_csv(CARPETA / "casos_resultado.csv")
K = T[T.grupo == "comparable"]  # los 120 del banco

titulo("1. NIVEL NACIONAL: % de acuerdo simulado (p1 de 5 a 7) contra el publicado")
print(fila("Los 120 casos comparables", metricas(K.real, K.sim)))
print(fila("  sin c704-bloqueo (cifra dudosa)", metricas(K.drop("c704-bloqueo", errors="ignore").real, K.drop("c704-bloqueo", errors="ignore").sim)))
print(fila("  parte desarrollo", metricas(K[K.parte == "desarrollo"].real, K[K.parte == "desarrollo"].sim)))
print(fila("  parte prueba", metricas(K[K.parte == "prueba"].real, K[K.parte == "prueba"].sim)))
print(fila("Constante 60 %", metricas(K.real, np.full(len(K), 60.0))))
print(fila("Constante = media real", metricas(K.real, np.full(len(K), K.real.mean()))))
con_d = K[K.real_d.notna()]
print(fila("% en desacuerdo (casos que lo publican)", metricas(con_d.real_d, con_d.sim_d)))
print(fila("Sin indecisos: a/(a+d)", metricas(con_d.real_neto, con_d.sim_neto)))
print(f"Media real de acuerdo {K.real.mean():.1f}, simulada {K.sim.mean():.1f}. Desviación estándar entre casos: real {K.real.std():.1f}, simulada {K.sim.std():.1f}")
print(f"Nota 4 (indecisos) simulada: media {K.sim_4.mean():.2f} %, máximo {K.sim_4.max():.1f} %. En las encuestas, lo que no es acuerdo ni desacuerdo: media {(100 - con_d.real - con_d.real_d).mean():.1f} %")

# Intervalo por remuestreo de familias completas.
azar = random.Random(5)
familias = sorted(K.familia.unique())
muestras = []
for _ in range(2000):
    elegidas = [azar.choice(familias) for _ in familias]
    partes = pd.concat([K[K.familia == f] for f in elegidas])
    muestras.append((abs(partes.dif).mean(), partes.dif.mean()))
eam_b, sesgo_b = np.array(muestras).T
print(f"Intervalo de 95 % remuestreando familias: EAM {np.percentile(eam_b, 2.5):.1f} a {np.percentile(eam_b, 97.5):.1f}; sesgo {np.percentile(sesgo_b, 2.5):+.1f} a {np.percentile(sesgo_b, 97.5):+.1f}")

# Ruido propio de la simulación: efecto del lote.
deff = []
for caso, g in R.groupby("caso"):
    p = g.a.mean() / 100
    if 0.05 < p < 0.95:
        medias = g.groupby("lote").a.mean() / 100
        tam = g.groupby("lote").size().mean()
        deff.append(medias.var(ddof=1) / (p * (1 - p) / tam))
print(f"Efecto de diseño por lote (varianza entre lotes / binomial): mediana {np.median(deff):.2f}, media {np.mean(deff):.2f}")
de = float(np.mean(deff))
ee = (K.sim / 100 * (1 - K.sim / 100) / K.n * max(1, de)) ** 0.5 * 100
print(f"Error estándar típico del % simulado con 1.000 agentes (con ese efecto): {ee.mean():.1f} pts. Margen de una encuesta de 700 casos: ±3,7 pts al 95 %")
piso = []
for _ in range(300):
    for c in K.index:
        p = K.real[c] / 100
        piso.append(abs(np.random.binomial(1000, p) / 1000 - np.random.binomial(700, p) / 700) * 100)
print(f"Piso de ruido (simulación perfecta con 1.000 agentes contra encuesta de 700): EAM {np.mean(piso):.1f}")

a, b = np.polyfit(K.sim, K.real, 1)[::-1]
print(f"Recta real = {a:.1f} + {b:.2f} x simulado. Si se corrige con esa recta dejando fuera la familia de cada caso:")
corr = []
for c in K.index:
    otros = K[K.familia != K.familia[c]]
    b1, a1 = np.polyfit(otros.sim, otros.real, 1)
    corr.append(min(100, max(0, a1 + b1 * K.sim[c])))
print(fila("  simulado corregido", metricas(K.real, corr)))

titulo("1.1 CONTRA LOS MÉTODOS YA PROBADOS (mismos casos; ojo: otra muestra y otro n)")
import validar_banco as vb

for metodo, nota in [("sitio", "pipeline anterior de 6 preguntas, 100 agentes 1:10"), ("probabilidad", "probabilidades, Haiku"), ("pronostico_haiku", "pronóstico directo Haiku"),
                     ("pronostico_opus", "pronóstico directo Opus")]:
    sim = vb.simulado(vb.leer(metodo))
    comunes = [c for c in K.index if c in sim]
    if comunes:
        print(fila(f"{metodo} ({nota})"[:44], metricas(K.real[comunes], [sim[c][0] for c in comunes])))
        print(fila("   este contraste en esos mismos casos", metricas(K.real[comunes], K.sim[comunes])))
        if metodo in ("sitio", "probabilidad", "pronostico_opus"):
            otro = pd.Series({c: sim[c][0] for c in comunes})
            print(f"   correlación entre ambos simulados {np.corrcoef(otro, K.sim[comunes])[0, 1]:.2f}; diferencia media absoluta {abs(otro - K.sim[comunes]).mean():.1f} pts; "
                  f"correlación de los errores {np.corrcoef(otro - K.real[comunes], K.dif[comunes])[0, 1]:.2f}")

titulo("1.2 CUÁNTOS AGENTES HACEN FALTA (submuestras al azar de los 1.000)")
piv = R[R.caso.isin(K.index)].pivot(index="agente", columns="caso", values="a")
completos = piv.dropna()
print(f"Agentes con respuesta en los {piv.shape[1]} casos: {len(completos)}")
arr, reales = completos.to_numpy(), K.real[completos.columns].to_numpy()
todos = arr.mean(axis=0)
rng = np.random.default_rng(3)
for n in (10, 25, 50, 100, 200, 500, 1000):
    if n > len(arr):
        continue
    e, dist = [], []
    for _ in range(300):
        sub = arr[rng.choice(len(arr), n, replace=False)].mean(axis=0)
        e.append(abs(sub - reales).mean())
        dist.append(abs(sub - todos).mean())
    print(f"  n={n:<5} EAM contra encuestas {np.mean(e):5.2f} ± {np.std(e):.2f}   distancia al resultado con todos {np.mean(dist):5.2f}")

titulo("1.3 DÓNDE SE CONCENTRA EL ERROR NACIONAL")
for campo, nombre in [("area", "Área"), ("banda", "Apoyo real (%)"), ("rasgo", "Tipo de pregunta (clasificación previa)"), ("transversal", "Transversalidad esperada (1 divide, 5 transversal)"),
                      ("sello", "Con sello de gobierno o sector"), ("tipo", "Tipo de ítem"), ("anio", "Año de la encuesta"), ("metodo_fuente", "Método de la fuente"), ("fuente_id", "Fuente")]:
    print(f"\n{nombre}:")
    for valor, g in K.groupby(campo, observed=True, dropna=False):
        if len(g):
            m = metricas(g.real, g.sim)
            print(f"  {str(valor):<28} n={m['n']:<3} EAM {m['EAM']:5.1f}  sesgo {m['sesgo']:+6.1f}  real {g.real.mean():5.1f}  sim {g.sim.mean():5.1f}  mismo lado {m['lado']:3.0f} %")

titulo("1.4 CASO POR CASO (ordenado por diferencia)")
ver = T.sort_values("dif")[["grupo", "area", "real", "sim", "dif", "real_d", "sim_d", "sim_4", "p1", "p2", "p3", "p4", "p5", "n", "enunciado"]].copy()
ver["enunciado"] = ver.enunciado.str[:80]
print(ver.to_string())

titulo("1.5 CASOS EXTRA (fuera de los 120): votaciones y paneles")
print(T[T.grupo == "extra"][["real", "sim", "dif", "real_d", "sim_d", "enunciado"]].to_string())

titulo("1.6 LAS OTRAS PREGUNTAS (p2 justicia, p3 confianza en el Estado, p4 efectividad, p5 influencia)")
print("Media por pregunta en los 120 casos:", K[["p1", "p2", "p3", "p4", "p5"]].mean().round(2).to_dict())
print("Desviación entre casos:", K[["p1", "p2", "p3", "p4", "p5"]].std().round(2).to_dict())
print("Correlación entre casos de cada media con la de p1:", {p: round(K.p1.corr(K[p]), 2) for p in ("p2", "p3", "p4", "p5")})
print("Correlación del error en acuerdo (sim - real) con la media de cada pregunta:", {p: round(K.dif.corr(K[p]), 2) for p in ("p1", "p2", "p3", "p4", "p5")})
print("Correlación persona a persona de p1 con cada una (todas las respuestas):", {p: round(R.p1.corr(R[p]), 2) for p in ("p2", "p3", "p4", "p5")})

# ---------------------------------------------------------------------------------------------
# 2. Cortes publicados
# ---------------------------------------------------------------------------------------------
titulo("2. CORTES PUBLICADOS POR SEGMENTO (segmentacion.jsonl)")
ACUERDO = vb.DE_ACUERDO


def dentro_de(dim, seg):
    if dim == "edad":
        desde, hasta = (int(x) for x in seg.replace("+", "–200").replace("-", "–").split("–"))
        return (P.edad_n >= desde) & (P.edad_n <= hasta)
    if dim == "gse":
        return P.gse3.str.startswith(seg)
    if dim == "sexo":
        return P.sexo == seg
    if dim == "zona":
        return P.macrozona == {"Santiago (RM)": "RM"}.get(seg, seg)
    if dim == "region":
        nombres = P.region.fillna("")
        return nombres.str.contains(seg.replace("Región de ", "").replace("Metropolitana", "Metropolitana"), regex=False)
    return None


pares = []
for linea in (BANCO / "segmentacion.jsonl").read_text(encoding="utf-8").splitlines():
    corte = json.loads(linea)
    real = next((corte["respuestas"][k] for k in ACUERDO if k in corte["respuestas"]), None)
    if corte["caso_id"] not in T.index or real is None:
        continue
    mascara = dentro_de(corte["dimension"], corte["segmento"])
    ids = set(P.index[mascara]) if mascara is not None else set()
    g = R[(R.caso == corte["caso_id"]) & R.agente.isin(ids)]
    if len(g) < 15:
        print(f"  (sin base) {corte['caso_id']} {corte['dimension']} {corte['segmento']} n={len(g)}")
        continue
    total_real, total_sim = T.real[corte["caso_id"]], T.sim[corte["caso_id"]]
    pares.append({"caso": corte["caso_id"], "dim": corte["dimension"], "segmento": corte["segmento"], "n": len(g), "real": real, "sim": g.a.mean(),
                  "d_real": real - total_real, "d_sim": g.a.mean() - total_sim})
S = pd.DataFrame(pares)
S["error_nivel"] = S.sim - S.real
S["error_delta"] = S.d_sim - S.d_real
print(S.to_string())
for dim, g in list(S.groupby("dim")) + [("todos", S), ("sin región", S[S.dim != "region"])]:
    lejos = g[abs(g.d_real) >= 3]
    r = g.d_real.corr(g.d_sim) if len(g) > 2 and g.d_real.std() > 0 else float("nan")
    print(f"  {dim:<10} cortes {len(g):<3} error de nivel medio {abs(g.error_nivel).mean():5.1f}  correlación de las diferencias con el total {r:5.2f}  "
          f"misma dirección (cortes a ≥3 pts) {100 * ((lejos.d_real > 0) == (lejos.d_sim > 0)).mean() if len(lejos) else float('nan'):3.0f} % de {len(lejos)}  "
          f"tamaño medio real {abs(g.d_real).mean():.1f} vs simulado {abs(g.d_sim).mean():.1f}")

# ---------------------------------------------------------------------------------------------
# 3. CEP 96: microdatos reales por segmento
# ---------------------------------------------------------------------------------------------
titulo("3. CEP 96: DIEZ PREGUNTAS ABIERTAS POR SEGMENTO CON MICRODATOS REALES")
VARIABLES = {"cep96-criminalidad": "iden_nacional_8_a", "cep96-trabajo": "iden_nacional_8_c", "cep96-gasto": "iden_nacional_8_e", "cep96-educacion": "iden_nacional_8_i",
             "cep96-aporte-economico": "iden_nacional_8_l", "cep96-seleccion-educacion": "iden_nacional_8_m", "cep96-tomas": "educacion_84_a",
             "cep96-estado-economia": "democracia_33_a", "cep96-burocracia": "democracia_33_d", "cep96-recorte": "rol_gobierno_31"}
DIMS_CEP = ["sexo", "edad", "educacion", "zona", "macrozona", "politica", "gobierno", "voto", "religion", "trabajo", "interes"]
P["religion"] = P.religion3
R["religion"] = R.agente.map(P.religion3)
cortes = []
print("Total nacional recalculado desde los microdatos (control contra lo publicado):")
for caso, var in VARIABLES.items():
    v = cep[var]
    dos = caso == "cep96-tomas"
    C["a"] = ((v == 1) if dos else v.isin([1, 2])) * 100.0
    C["d"] = ((v == 2) if dos else v.isin([4, 5])) * 100.0
    sim_caso = R[R.caso == caso]
    ra, rd = np.average(C.a, weights=C.w), np.average(C.d, weights=C.w)
    print(f"  {caso:<28} microdatos {ra:5.1f} / {rd:5.1f}   publicado {casos[caso]['real_acuerdo']} / {casos[caso]['real_desacuerdo']}   simulado {sim_caso.a.mean():5.1f} / {sim_caso.d.mean():5.1f}")
    for dim in DIMS_CEP:
        for seg, g in C.groupby(dim):
            s = sim_caso[sim_caso[dim] == seg]
            if g.w.sum() / C.w.sum() < 0.03 or len(s) < 25 or len(g) < 40:
                continue
            a_r, d_r = np.average(g.a, weights=g.w), np.average(g.d, weights=g.w)
            cortes.append({"caso": caso, "dim": dim, "segmento": seg, "n_cep": len(g), "n_sim": len(s), "real": a_r, "real_d": d_r, "sim": s.a.mean(), "sim_d": s.d.mean(),
                           "real_neto": 100 * a_r / (a_r + d_r) if a_r + d_r else np.nan, "sim_neto": 100 * s.a.mean() / (s.a.mean() + s.d.mean()),
                           "tot_real": ra, "tot_sim": sim_caso.a.mean(), "tot_real_neto": 100 * ra / (ra + rd), "tot_sim_neto": 100 * sim_caso.a.mean() / (sim_caso.a.mean() + sim_caso.d.mean())})
Q = pd.DataFrame(cortes)
Q["err"] = Q.sim - Q.real
Q["err_neto"] = Q.sim_neto - Q.real_neto
Q["d_real"] = Q.real_neto - Q.tot_real_neto
Q["d_sim"] = Q.sim_neto - Q.tot_sim_neto
Q["err_delta"] = Q.d_sim - Q.d_real
Q.to_csv(CARPETA / "cep_cortes.csv", index=False)
print(f"\n{len(Q)} cortes (segmento x pregunta). La CEP ofrece «ni de acuerdo ni en desacuerdo» (13 a 31 %) y el sitio casi no deja nota 4, así que se compara sobre quienes toman posición: a/(a+d).")
print(f"Diferencia de cada segmento con el total nacional, real contra simulada: correlación {Q.d_real.corr(Q.d_sim):.2f}; "
      f"misma dirección en los cortes que se alejan ≥5 pts: {100 * ((Q[abs(Q.d_real) >= 5].d_real > 0) == (Q[abs(Q.d_real) >= 5].d_sim > 0)).mean():.0f} % de {(abs(Q.d_real) >= 5).sum()}; "
      f"tamaño medio real {abs(Q.d_real).mean():.1f}, simulado {abs(Q.d_sim).mean():.1f}")
print("\nPor dimensión: cuánto separa cada característica a la gente (diferencia absoluta media del segmento con el total, en puntos de acuerdo neto)")
por_dim = Q.groupby("dim").apply(lambda g: pd.Series({"cortes": len(g), "separa_real": abs(g.d_real).mean(), "separa_sim": abs(g.d_sim).mean(),
                                                      "razon_sim_real": abs(g.d_sim).mean() / abs(g.d_real).mean(), "corr": g.d_real.corr(g.d_sim),
                                                      "misma_dir_%": 100 * ((g[abs(g.d_real) >= 5].d_real > 0) == (g[abs(g.d_real) >= 5].d_sim > 0)).mean()}), include_groups=False)
print(por_dim.sort_values("razon_sim_real", ascending=False).to_string())
print("\nPor segmento, promedio de las 10 preguntas: error en acuerdo neto (sim - real), error absoluto, y error en la diferencia con el total")
por_seg = Q.groupby(["dim", "segmento"]).apply(lambda g: pd.Series({"preguntas": len(g), "n_sim": g.n_sim.mean(), "n_cep": g.n_cep.mean(), "EAM_neto": abs(g.err_neto).mean(), "sesgo_neto": g.err_neto.mean(),
                                                                    "EAM_delta": abs(g.err_delta).mean(), "EAM_acuerdo_bruto": abs(g.err).mean()}), include_groups=False)
print(por_seg.to_string())
print("\nLos 25 cortes con mayor error en acuerdo neto:")
print(Q.reindex(Q.err_neto.abs().sort_values(ascending=False).index).head(25)[["caso", "dim", "segmento", "n_sim", "real", "sim", "real_neto", "sim_neto", "err_neto", "d_real", "d_sim"]].to_string())
print("\nPosición política, pregunta por pregunta (acuerdo neto real / simulado):")
print(Q[Q.dim == "politica"].pivot(index="caso", columns="segmento", values=["real_neto", "sim_neto"]).round(0).to_string())
print("\nVoto en segunda vuelta 2025, pregunta por pregunta (acuerdo neto real / simulado):")
print(Q[Q.dim == "voto"].pivot(index="caso", columns="segmento", values=["real_neto", "sim_neto"]).round(0).to_string())
print("\nEdad, pregunta por pregunta (acuerdo neto real / simulado):")
print(Q[Q.dim == "edad"].pivot(index="caso", columns="segmento", values=["real_neto", "sim_neto"]).round(0).to_string())
print("\nEducación, pregunta por pregunta (acuerdo neto real / simulado):")
print(Q[Q.dim == "educacion"].pivot(index="caso", columns="segmento", values=["real_neto", "sim_neto"]).round(0).to_string())

titulo("3.1 PERSONA A PERSONA: cinco preguntas cuya respuesta real (la del donante CEP) viene en la fila del agente")
from servidor import metodo as _metodo
import metodos_banco as _mb

OCULTOS = {"cep96-estado-economia": ("menos_estado", "menos_estado_economia"), "cep96-burocracia": ("estado_burocracia", "estado_burocracia"),
           "cep96-recorte": ("reducir_gasto", "reducir_gasto_publico"), "cep96-criminalidad": ("inmigrantes_criminalidad", "inmigrantes_criminalidad"),
           "cep96-aporte-economico": ("inmigrantes_aporte", "inmigrantes_aporte")}
for caso, (dato, columna) in OCULTOS.items():
    g = R[(R.caso == caso) & R[columna].between(1, 5)]
    datos = _metodo.datos_de(_mb.tema_del_caso(casos[caso]))
    visto = datos is None or dato in datos
    si, no, medio = g[g[columna] <= 2].p1, g[g[columna] >= 4].p1, g[g[columna] == 3].p1
    if not len(si) or not len(no):
        continue
    auc = (sum((si.to_numpy()[:, None] > no.to_numpy()[None, :]).ravel()) + 0.5 * sum((si.to_numpy()[:, None] == no.to_numpy()[None, :]).ravel())) / (len(si) * len(no))
    acierto = 100 * ((si >= 5).sum() + (no <= 3).sum()) / (len(si) + len(no))
    print(f"  {caso:<26} el modelo {'SÍ' if visto else 'NO'} leyó ese dato en el perfil | donantes: acuerdo {100 * len(si) / len(g):4.1f} %, ni-ni {100 * len(medio) / len(g):4.1f} %, desacuerdo {100 * len(no) / len(g):4.1f} % | "
          f"simulado: acuerdo {g.a.mean():4.1f} %, desacuerdo {g.d.mean():4.1f} % | AUC {auc:.2f} | acierta el lado {acierto:.0f} % | "
          f"de los «de acuerdo» reales simulan acuerdo {100 * (si >= 5).mean():.0f} %; de los «en desacuerdo» simulan desacuerdo {100 * (no <= 3).mean():.0f} %; los ni-ni simulan acuerdo {100 * (medio >= 5).mean():.0f} %")
    for dim in ("politica", "edad", "educacion"):
        partes = []
        for seg, s in g.groupby(dim):
            toma = s[s[columna] != 3]
            if len(toma) >= 30:
                ok = 100 * (((toma[columna] <= 2) & (toma.p1 >= 5)) | ((toma[columna] >= 4) & (toma.p1 <= 3))).mean()
                partes.append(f"{seg} {ok:.0f} % (n={len(toma)})")
        print(f"       acierto del lado por {dim}: " + "; ".join(partes))

# ---------------------------------------------------------------------------------------------
# 4. Estructura de la simulación en los 120 casos
# ---------------------------------------------------------------------------------------------
titulo("4. QUIÉN SE ALEJA DE LA REALIDAD EN LOS 120 CASOS (sin cortes reales: cotas y contrafactuales)")
RK = R[R.caso.isin(K.index)]
print("4.1 Si el país fuera solo ese grupo de agentes: error de su % de acuerdo contra el % nacional real, y cuánto se separa del total simulado")
resumen = []
tabla_grupos = {}
for dim in DIMENSIONES:
    piv = RK.pivot_table(index="caso", columns=dim, values="a", aggfunc="mean")
    cuenta = P[dim].value_counts()
    for seg in piv.columns:
        if cuenta.get(seg, 0) < 50:
            continue
        s = piv[seg].reindex(K.index)
        m = metricas(K.real, s)
        w = cuenta[seg] / len(P)
        # Cotas: con R % real en el país y el grupo pesando w, el grupo real está entre (R - 100(1-w))/w y R/w.
        bajo = ((K.real - 100 * (1 - w)) / w).clip(lower=0)
        alto = (K.real / w).clip(upper=100)
        fuera = ((s < bajo) * (bajo - s) + (s > alto) * (s - alto))
        alto_c, bajo_c = K.real >= 75, K.real <= 35
        resumen.append({"dim": dim, "segmento": seg, "n": cuenta[seg], "EAM": m["EAM"], "sesgo": m["sesgo"], "r": m["r"], "lado_%": m["lado"],
                        "separa_del_total": abs(s - K.sim).mean(), "dif_con_total": (s - K.sim).mean(),
                        "casos_imposibles": int((fuera > 0).sum()), "error_minimo_medio": fuera[fuera > 0].mean() if (fuera > 0).any() else 0.0,
                        "rechaza_consensos_%": 100 * (s[alto_c] < 50).mean(), "media_en_consensos": s[alto_c].mean(),
                        "apoya_lo_rechazado_%": 100 * (s[bajo_c] > 50).mean(), "media_en_rechazados": s[bajo_c].mean()})
        tabla_grupos[(dim, seg)] = s
G = pd.DataFrame(resumen)
G.to_csv(CARPETA / "grupos_resumen.csv", index=False)
print(f"(total simulado: EAM {abs(K.dif).mean():.1f}, sesgo {K.dif.mean():+.1f}. Casos con apoyo real ≥75 %: {(K.real >= 75).sum()}, simulado medio {K.sim[K.real >= 75].mean():.1f}; con apoyo real ≤35 %: {(K.real <= 35).sum()}, simulado medio {K.sim[K.real <= 35].mean():.1f})")
print(G.to_string())

print("\n4.2 Cuánto separa cada característica las respuestas simuladas (desviación entre grupos del % de acuerdo, media de los 120 casos)")
sep = []
for dim in DIMENSIONES:
    piv = RK.pivot_table(index="caso", columns=dim, values="a", aggfunc="mean")
    pesos = P[dim].value_counts(normalize=True).reindex(piv.columns).fillna(0)
    medias = (piv * pesos).sum(axis=1) / pesos.sum()
    de_entre = (((piv.sub(medias, axis=0)) ** 2 * pesos).sum(axis=1) / pesos.sum()) ** 0.5
    sep.append({"dim": dim, "desviacion_entre_grupos": de_entre.mean(), "maxima": de_entre.max(), "corr_con_error_abs": de_entre.reindex(K.index).corr(abs(K.dif))})
print(pd.DataFrame(sep).sort_values("desviacion_entre_grupos", ascending=False).to_string())

print("\n4.3 Polarización simulada por posición política y error")
izq, der = tabla_grupos[("politica", "Izquierda (1-4)")], tabla_grupos[("politica", "Derecha (7-10)")]
cen, nou = tabla_grupos[("politica", "Centro (5-6)")], tabla_grupos[("politica", "No se ubica")]
K = K.assign(izq=izq, der=der, cen=cen, nou=nou, brecha=izq - der)
print(f"Brecha izquierda - derecha simulada: media absoluta {abs(K.brecha).mean():.1f} pts; mediana {abs(K.brecha).median():.1f}; casos con más de 40 pts: {(abs(K.brecha) > 40).sum()}; con menos de 10: {(abs(K.brecha) < 10).sum()}")
print(f"Correlación entre |brecha| y |error|: {abs(K.brecha).corr(abs(K.dif)):.2f}; entre |brecha| y error con signo: {abs(K.brecha).corr(K.dif):.2f}; entre brecha con signo y error con signo: {K.brecha.corr(K.dif):.2f}")
K["tercil"] = pd.qcut(abs(K.brecha), 3, labels=["poco polarizado", "medio", "muy polarizado"])
for t, g in K.groupby("tercil", observed=True):
    print(f"  {t:<16} n={len(g)} |brecha| media {abs(g.brecha).mean():5.1f}  EAM {abs(g.dif).mean():5.1f}  sesgo {g.dif.mean():+5.1f}  real {g.real.mean():.1f}  sim {g.sim.mean():.1f}")
K["sentido"] = np.where(K.brecha > 15, "la izquierda apoya más", np.where(K.brecha < -15, "la derecha apoya más", "transversal en la simulación"))
for t, g in K.groupby("sentido"):
    print(f"  {t:<30} n={len(g):<3} EAM {abs(g.dif).mean():5.1f}  sesgo {g.dif.mean():+5.1f}  real {g.real.mean():5.1f}  sim {g.sim.mean():5.1f} | izquierda {g.izq.mean():5.1f}  centro {g.cen.mean():5.1f}  derecha {g.der.mean():5.1f}  no se ubica {g.nou.mean():5.1f}")
print("\nCasos de consenso real (≥75 %) y cómo respondió cada posición política en la simulación:")
print(K[K.real >= 75].sort_values("dif")[["real", "sim", "dif", "izq", "cen", "der", "nou", "enunciado"]].assign(enunciado=lambda d: d.enunciado.str[:70]).to_string())
print("\nCasos de rechazo real (≤35 %):")
print(K[K.real <= 35].sort_values("dif")[["real", "sim", "dif", "izq", "cen", "der", "nou", "enunciado"]].assign(enunciado=lambda d: d.enunciado.str[:70]).to_string())

print("\n4.4 Todos los casos con cada posición política (para el anexo)")
print(K.sort_values("dif")[["area", "real", "sim", "dif", "izq", "cen", "der", "nou", "brecha"]].to_string())

print("\n4.5 Regresión del error nacional sobre rasgos del caso")
X = pd.DataFrame({"const": 1.0, "real_c": (K.real - K.real.mean()) / 10, "abs_brecha": abs(K.brecha) / 10}).astype(float)
beta, *_ = np.linalg.lstsq(X.to_numpy(), K.dif.to_numpy(), rcond=None)
pred = X.to_numpy() @ beta
print(f"error = {beta[0]:+.1f} {beta[1]:+.2f} x (apoyo real - media)/10 {beta[2]:+.2f} x |brecha|/10 ; R² = {1 - ((K.dif - pred) ** 2).sum() / ((K.dif - K.dif.mean()) ** 2).sum():.2f}")
print(f"Solo con el apoyo real: R² = {np.corrcoef(K.real, K.dif)[0, 1] ** 2:.2f} (pendiente {np.polyfit(K.real, K.dif, 1)[0]:+.2f} pts de error por punto de apoyo real)")

json.dump({"nacional": metricas(K.real, K.sim)}, open(CARPETA / "resumen.json", "w"), ensure_ascii=False, indent=1)
