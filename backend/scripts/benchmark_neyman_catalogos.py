"""Contrasta tres catálogos de 10.000 y tres diseños estratificados a 5.000."""

import argparse
import csv
import heapq
import json
from pathlib import Path
from time import perf_counter

import duckdb
import numpy as np

from correr_benchmark_luna import agregado
from preparar_benchmark_catalogos import (
    MARGENES, SEMILLA, TEXTO_TAG, armar_perfiles, asignar, diagnostico, distribuciones, estrato, ipf, leer, ordenar,
)

CATALOGOS = ("bloques", "medoides", "medoides_transporte")
K = 10_000
MUESTRA = 5_000
MINIMO_AUTO_RM = 500
# región × zona × categoría de viaje en RM. La categoría 1 es auto particular.
ESTRATOS_AUTO_RM = {13 * 9 + zona * 3 + 1 for zona in (0, 1, 2)}


def viajes_rm(d):
    return np.where(d["region"] == 13, np.select([d["viaje"] == 1, d["viaje"] == 2], [1, 2]), 0)


def grupos_politica(d):
    return estrato(d) * 3 + viajes_rm(d)


def medoid(d, miembros):
    # Distancia aditiva en datos mixtos. El costo categórico de pertenecer
    # a un nivel es el número de integrantes que tienen otro nivel.
    n = len(miembros)
    costo = np.zeros(n, dtype=float)
    for campo in ("comuna", "sexo", "laboral", "ocupacion", "viaje", "hogar"):
        v = d[campo][miembros]
        _, codigos, cantidad = np.unique(v, return_inverse=True, return_counts=True)
        costo += n - cantidad[codigos]
    edad = d["edad_fina"][miembros].astype(np.int64)
    orden = np.argsort(edad, kind="stable")
    x = edad[orden]
    suma = np.cumsum(x)
    paso = np.arange(n)
    costo[orden] += (x * (2 * paso + 2 - n) + suma[-1] - 2 * suma) / 70
    # Desempate por cercanía al centro ordinal del bloque.
    minimo = np.flatnonzero(costo == costo.min())
    return miembros[minimo[np.argmin(np.abs(2 * minimo - n + 1))]]


def grupos(d, metodo):
    base = (estrato(d) * 4 + d["edad"]) * 4 + d["educacion"]
    orden = ordenar(d)
    claves = base if metodo != "medoides_transporte" else base * 3 + viajes_rm(d)
    if metodo == "medoides_transporte":
        orden = orden[np.argsort(claves[orden], kind="stable")]
    cortes = np.r_[0, np.flatnonzero(np.diff(claves[orden])) + 1, len(orden)]
    capacidad = np.diff(cortes)
    cupos = asignar(K, capacidad, capacidad)
    bordes = np.r_[0, np.concatenate([i + np.arange(1, c + 1, dtype=np.int64) * n // c
                                     for i, n, c in zip(cortes, capacidad, cupos)])]
    if metodo == "bloques":
        ids = orden[(bordes[:-1] + bordes[1:] - 1) // 2]
    else:
        ids = np.array([medoid(d, orden[a:b]) for a, b in zip(bordes[:-1], bordes[1:])])
    personas = np.diff(bordes) * 3
    assert len(ids) == len(np.unique(ids)) == K and personas.sum() == 3 * len(orden)
    diag = {"celdas_protegidas": len(capacidad), "personas": int(personas.sum()),
            "percentiles_personas_por_ficha": np.percentile(personas, [0, 25, 50, 75, 100]).tolist()}
    for k in ("comuna", "sexo", "viaje", "hogar"):
        diag[f"coincidencia_{k}_pct"] = float(100*np.mean(d[k][orden] == np.repeat(d[k][ids], np.diff(bordes))))
    return ids, personas, orden, bordes, diag


def leer_votos(directorio):
    votos = {}
    for archivo in directorio.glob("*.json"):
        lote = json.loads(archivo.read_text())
        for k, v in zip(lote["ids"], lote["r"], strict=True):
            if k in votos or v not in (1, 2, 3):
                raise ValueError(f"Registro duplicado o inválido en {archivo}")
            votos[k] = v
    return votos


def piloto(d, origen, excluidos):
    orden = np.argsort(d["id"])
    ids_ordenados = d["id"][orden]
    por_estrato = grupos_politica(d)
    ps, hs, pesos = [], [], []
    for carpeta in (origen, origen / "semilla-20261122"):
        p = json.loads((carpeta / "plan-3.json").read_text())
        m = p["catalogos"]["1000000"]["muestras"]["2000"]
        votos = leer_votos(carpeta / "lotes-3-1000000")
        for id_, w in zip(m["ids"], m["peso"], strict=True):
            if id_ in excluidos:
                continue
            pos = np.searchsorted(ids_ordenados, int(id_))
            if pos >= len(orden) or ids_ordenados[pos] != int(id_):
                raise ValueError("El piloto y el catálogo actual deben usar la misma base de tríos.")
            hs.append(int(por_estrato[orden[pos]]))
            pesos.append(w)
            ps.append(votos[id_] == 1)
    y, w, h = np.array(ps), np.array(pesos), np.array(hs)
    global_ = float(np.average(y, weights=w))
    grupos = {}
    for k in np.unique(h):
        loc = h == k
        wl = w[loc]
        n_ef = wl.sum()**2 / (wl @ wl)
        prop = float(np.average(y[loc], weights=wl))
        # Suaviza estratos pequeños hacia el apoyo del piloto nacional.
        p = (n_ef * prop + 30 * global_) / (n_ef + 30)
        grupos[int(k)] = {"n": int(loc.sum()), "apoyo_piloto": prop, "sigma": float(np.sqrt(p*(1-p)))}
    return {"n": len(y), "apoyo": global_, "grupos": grupos}


def repartir(tamano, capacidad, prioridad, piso):
    """Minimiza suma de prioridad² / cuota, respetando mínimos y disponibilidad."""
    cuota = np.minimum(piso, capacidad).copy()
    if cuota.sum() > tamano or capacidad.sum() < tamano:
        raise ValueError("Las cuotas son incompatibles con el tamaño solicitado.")
    p2 = prioridad.astype(float)**2
    def mejora(i):
        return -p2[i] / (cuota[i] * (cuota[i] + 1))
    cola = [(mejora(i), i) for i in range(len(cuota)) if cuota[i] < capacidad[i]]
    heapq.heapify(cola)
    for _ in range(tamano - int(cuota.sum())):
        _, j = heapq.heappop(cola)
        cuota[j] += 1
        if cuota[j] < capacidad[j]:
            heapq.heappush(cola, (mejora(j), j))
    return cuota


def disenos(estratos, personas, previo):
    grupos = np.unique(estratos)
    miembros = [np.flatnonzero(estratos == h) for h in grupos]
    cap = np.array([len(m) for m in miembros])
    masa = np.array([personas[m].sum() for m in miembros])
    afectados = np.isin(grupos, list(ESTRATOS_AUTO_RM))
    piso = np.ones_like(cap)
    disponibles = min(MINIMO_AUTO_RM, int(cap[afectados].sum()))
    if disponibles:
        piso[afectados] = asignar(disponibles, masa[afectados], cap[afectados])
    cuotas = {
        "proporcional": repartir(MUESTRA, cap, masa, np.ones_like(cap)),
        "proporcional_minimo": repartir(MUESTRA, cap, masa, piso),
    }
    if previo is not None:
        p = previo["apoyo"]
        sigma = np.array([previo["grupos"].get(int(h), {}).get("sigma", np.sqrt(p * (1 - p))) for h in grupos])
        cuotas["neyman_minimo"] = repartir(MUESTRA, cap, masa * sigma, piso)
    return grupos, miembros, cap, masa, afectados, cuotas


def preparar(args):
    t = perf_counter()
    args.salida.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(config={"threads": 4, "memory_limit": "1500MB"}) as con:
        ref = leer(con, args.personas, args.hogares)
        metas = distribuciones(ref)
        del ref
        d = leer(con, args.datos / "agentes_trios/region_*.parquet")
    # Al usar un plan común el mismo perfil recibe una sola decisión aunque
    # aparezca en varios catálogos. Conserva todos los ids y pesos por método.
    inventario = {}
    metadatos = {}
    for metodo in dict.fromkeys(args.agrupaciones):
        ids, masas, orden, bordes, diag = grupos(d, metodo)
        metadatos[metodo] = (ids, masas)
        np.savez(args.salida / f"catalogo-{metodo}.npz", id=d["id"][ids],
                 personas=masas, miembros=d["id"][orden], bordes=bordes)
        inventario[metodo] = diag
    union = np.unique(np.concatenate([ids for ids, _ in metadatos.values()]))
    personas = armar_perfiles(d, union)
    lista = sorted(personas, key=int)
    previo = piloto(d, args.piloto, set(lista)) if args.piloto else None
    for metodo, (ids, w) in metadatos.items():
        h = grupos_politica(d)[ids]
        g, _, cap, masa, afectados, cuotas = disenos(h, w, previo)
        inventario[metodo].update(id=[str(x) for x in d["id"][ids]], peso=w.tolist(), estrato=h.tolist(),
                                  composicion=diagnostico(d, ids, w, metas),
                                  cuotas={name: q.tolist() for name,q in cuotas.items()},
                                  estratos=g.tolist(), capacidades=cap.tolist(), masas=masa.tolist(),
                                  afectados=afectados.tolist())
        print(f"{metodo}: {len(ids):,} arquetipos · {int(cap[afectados].sum())} de auto en RM · cuotas " +
              ", ".join(f"{x}={int(q[afectados].sum())}" for x,q in cuotas.items()), flush=True)
    # El corredor compartido solo recoge decisiones de la unión. El análisis
    # usa los pesos y catálogos reales guardados aparte.
    n = len(lista)
    ficha = {"perfil": personas, "ids": lista, "peso": [1] * n, "peso_ipf": None,
             "ipf": "aplicar por catálogo", "composicion": None, "composicion_ipf": None}
    plan = {"base": 3, "caso": "c698-tag", "pregunta": TEXTO_TAG,
            "catalogos": {n: {"fichas": n, "muestras": {n: ficha}}}}
    (args.salida / "plan-luna.json").write_text(json.dumps(plan, ensure_ascii=False))
    for metodo,(ids,w) in metadatos.items():
        vars_ = {k: v[ids] for k, v in d.items()}
        np.savez(args.salida / f"variables-{metodo}.npz", **vars_)
    json_meta = {"catalogos":inventario, "union":n, "piloto":previo, "metas":{k:v.tolist() for k,v in metas.items()},
                 "preparacion_segundos":perf_counter()-t}
    (args.salida / "diseno.json").write_text(json.dumps(json_meta, ensure_ascii=False))
    detalle = f" · piloto de {previo['n']:,} respuestas" if previo else ""
    print(f"Unión de los catálogos: {n:,} fichas distintas{detalle}.", flush=True)


def evaluar(d, ids, pesos, votos, metas, afectados):
    m = {"ids": [str(i) for i in d["id"][ids]], "peso": pesos}
    calibrados, estado = ipf(d, ids, pesos, metas)
    m["peso_ipf"] = calibrados
    ponderados_tag, estado_tag = ipf(d, ids, pesos, metas, (*MARGENES, "tag_rm"))
    m["peso_ipf_tag"] = ponderados_tag
    postura = np.array([votos[i] for i in m["ids"]])
    if not afectados.any():
        raise ValueError("El diseño perdió el grupo de interés.")
    return {
        "sin_ipf": agregado(m, votos, "peso"), "con_ipf": agregado(m, votos, "peso_ipf"),
        "con_ipf_tag": agregado(m, votos, "peso_ipf_tag"), "ipf_tag": estado_tag,
        "ipf": estado, "composicion": diagnostico(d, ids, pesos, metas),
        "composicion_ipf": diagnostico(d, ids, calibrados, metas) if calibrados is not None else None,
        "composicion_ipf_tag": diagnostico(d, ids, ponderados_tag, metas) if ponderados_tag is not None else None,
        "auto_rm": {"n": int(afectados.sum()), "apoyo_pct": float(100*np.average(postura[afectados]==1, weights=pesos[afectados]))},
    }


def resumir(runs, ref):
    def stats(v, objetivo):
        a = np.asarray(v)
        return {"media": float(a.mean()), "sd": float(a.std(ddof=1)) if len(a) > 1 else None,
                "rmse_vs_completo": float(np.sqrt(np.mean((a - objetivo)**2)))}
    return {
        "semillas": len(runs), "agentes_auto": [min(r["auto_rm"]["n"] for r in runs), max(r["auto_rm"]["n"] for r in runs)],
        "apoyo_nacional": stats([r["sin_ipf"]["pct"][0] for r in runs], ref["sin_ipf"]["pct"][0]),
        "apoyo_auto_rm": stats([r["auto_rm"]["apoyo_pct"] for r in runs], ref["auto_rm"]["apoyo_pct"]),
        "mae_cadem_sin_ipf": float(np.mean([r["sin_ipf"]["mae_pp"] for r in runs])),
        "mae_cadem_con_ipf": float(np.mean([r["con_ipf"]["mae_pp"] for r in runs])) if all(r["con_ipf"] for r in runs) else None,
        "posturas_ipf_pct": np.mean([r["con_ipf"]["pct"] for r in runs], axis=0).tolist() if all(r["con_ipf"] for r in runs) else None,
        "mae_cadem_ipf_tag": float(np.mean([r["con_ipf_tag"]["mae_pp"] for r in runs])) if all(r["con_ipf_tag"] for r in runs) else None,
        "n_efectivo_media": float(np.mean([r["composicion"]["n_efectivo"] for r in runs])),
        "tv_edad_educacion_media": float(np.mean([r["composicion"]["tv_pp"]["edad_educacion"] for r in runs])),
    }


def puntuar(args):
    datos = json.loads((args.salida / "diseno.json").read_text())
    previo = datos["piloto"]
    if previo is not None:
        previo["grupos"] = {int(k):v for k,v in previo["grupos"].items()}
    votos = leer_votos(args.salida / f"lotes-3-{datos['union']}")
    if len(votos) != datos["union"]:
        raise ValueError(f"Hay {len(votos)} de {datos['union']} decisiones válidas. Completa los lotes antes de puntuar.")
    metas = {k:np.array(v) for k,v in datos["metas"].items()}
    auto, transporte = metas["region_viaje"][[13 * 9 + 1, 13 * 9 + 2]]
    rm = metas["region"][13]
    metas["tag_rm"] = np.array([1 - rm, auto, transporte, rm - auto - transporte])
    informe = {"modelo":"gpt-6-luna", "caso":"c698-tag", "piloto":previo,"decisiones":len(votos),
               "minimo_auto_rm":MINIMO_AUTO_RM, "catalogos":{}, "referencia_cadem":[55,40,5]}
    filas = []
    for metodo, c in datos["catalogos"].items():
        with np.load(args.salida / f"variables-{metodo}.npz") as f:
            d = dict(f)
        viaje = viajes_rm(d)
        d["tag_rm"] = np.where(d["region"] == 13, np.where(viaje > 0, viaje, 3), 0)
        w = np.asarray(c["peso"], dtype=float)
        h = grupos_politica(d)
        g, miembros, cap, masa, tipo, cuotas = disenos(h,w,previo)
        todos = np.arange(K)
        completo = evaluar(d, todos, w, votos, metas, np.isin(h, list(ESTRATOS_AUTO_RM)))
        pruebas = {nombre: [] for nombre in cuotas}
        for rep in range(args.repeticiones):
            rng = np.random.default_rng(SEMILLA+rep)
            # Las tres alternativas comparten el orden aleatorio dentro de cada estrato.
            ordenes = [rng.permutation(m) for m in miembros]
            for nombre,q in cuotas.items():
                ids = np.concatenate([orden[:n] for orden,n in zip(ordenes,q)])
                pesos = w[ids] * np.repeat(cap / q, q)
                eval_ = evaluar(d, ids, pesos, votos, metas, np.repeat(tipo,q))
                eval_["semilla"] = SEMILLA+rep
                pruebas[nombre].append(eval_)
        resumen = {nombre: resumir(r,completo) for nombre,r in pruebas.items()}
        informe["catalogos"][metodo] = {"auditoria": {k:v for k,v in c.items() if k not in ("id","peso","estrato")},
                                         "agentes_10000":completo, "muestras_5000":pruebas, "resumen_5000":resumen}
        mae_ipf = completo["con_ipf"]["mae_pp"] if completo["con_ipf"] else None
        mae_tag = completo["con_ipf_tag"]["mae_pp"] if completo["con_ipf_tag"] else None
        posturas = completo["con_ipf"]["pct"] if completo["con_ipf"] else [None] * 3
        filas.append([metodo,"catálogo completo",K,completo["sin_ipf"]["mae_pp"],mae_ipf,mae_tag,"",
                      "",completo["auto_rm"]["n"],completo["composicion"]["n_efectivo"], *posturas])
        for nombre, s in resumen.items():
            filas.append([metodo,nombre,MUESTRA,s["mae_cadem_sin_ipf"],s["mae_cadem_con_ipf"],s["mae_cadem_ipf_tag"],
                          s["apoyo_nacional"]["rmse_vs_completo"],s["apoyo_auto_rm"]["rmse_vs_completo"],
                          s["agentes_auto"][0],s["n_efectivo_media"], *(s["posturas_ipf_pct"] or [None] * 3)])
    args.informe.write_text(json.dumps(informe,ensure_ascii=False,indent=2)+"\n")
    with args.informe.with_suffix(".csv").open("w",encoding="utf-8-sig",newline="") as f:
        csv_ = csv.writer(f)
        csv_.writerow(["agrupacion","muestreo","agentes","mae_cadem_diseno_pp","mae_cadem_ipf_pp","mae_cadem_ipf_tag_pp",
                       "rmse_apoyo_nacional_vs_catalogo_pp","rmse_apoyo_auto_rm_vs_catalogo_pp",
                       "agentes_auto_rm","n_efectivo","acuerdo_ipf_pct","desacuerdo_ipf_pct","sin_posicion_ipf_pct"])
        csv_.writerows(filas)
    print(*filas,sep="\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="paso",required=True)
    pre = sub.add_parser("preparar")
    pre.add_argument("--personas",type=Path,required=True)
    pre.add_argument("--hogares",type=Path,required=True)
    pre.add_argument("--datos",type=Path,default=Path("backend/data"))
    pre.add_argument("--piloto",type=Path,help="Resultados previos para habilitar Neyman.")
    pre.add_argument("--agrupaciones",nargs="+",choices=CATALOGOS,default=CATALOGOS)
    pre.add_argument("--salida",type=Path,required=True)
    eval_ = sub.add_parser("puntuar")
    eval_.add_argument("--salida",type=Path,required=True)
    eval_.add_argument("--informe",type=Path,required=True)
    eval_.add_argument("--repeticiones",type=int,default=100)
    args = ap.parse_args()
    if args.paso=="preparar":
        preparar(args)
    else:
        if args.repeticiones < 1:
            ap.error("--repeticiones debe ser positivo.")
        puntuar(args)


if __name__=="__main__":
    main()
