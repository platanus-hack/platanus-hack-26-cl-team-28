"""Compara perfiles base y con restricciones económicas imputadas desde EBS 2023."""

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from math import ceil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from benchmark_neyman_catalogos import leer_votos
from correr_benchmark_luna import correr

BRAZOS = ("base", "asociado", "asociado_justicia", "completo", "completo_justicia")
CASOS = (
    "c629-regularizacion-empleo", "c638-seia", "c638-empresas",
    "c663-cae-convenio", "c577-congreso", "c625-contribuciones", "c543-marihuana",
)
JUSTICIA = (
    "Al repartir beneficios públicos, suele priorizar que guarden proporción con lo aportado por cada persona",
    "Al repartir beneficios públicos, suele priorizar reducir las diferencias de acceso entre personas",
)
MES = ("con mucha dificultad", "con dificultad", "sin especial dificultad ni facilidad",
       "con facilidad", "con mucha facilidad")
RESERVA = ("con mucha dificultad", "con bastante dificultad", "con algo de dificultad",
           "con poca dificultad", "sin dificultad")
COLUMNAS = ("region", "edad", "educacion", "laboral", "sexo")
CELDAS = ((0, 1, 2, 3, 4), (1, 2, 3, 4), (1, 2, 3), (1, 3), (1,), ())


def leer(ruta):
    return json.loads(ruta.read_text())


def guardar(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n")


def donantes(ruta):
    import pandas as pd

    campos = ["region_casen", "tramoebs2", "educ_recat_casen", "l7", "l8", "l9", "l10",
              "sg01", "fexp", "yy2", "yy4", "yy5"]
    ebs = pd.read_stata(ruta, columns=campos, convert_categoricals=False)
    ebs = ebs[ebs.yy2.between(1, 5) & ebs.yy4.between(1, 5) & ebs.yy5.isin([1, 2]) & (ebs.fexp > 0)]
    edad = np.minimum(ebs.tramoebs2.to_numpy() - 1, 3)
    ocupado = (ebs[["l7", "l8", "l9"]] == 1).any(axis=1)
    actividad = np.where(ocupado, 1, np.where(ebs.l10 == 1, 2, 3))
    datos = np.column_stack((ebs.region_casen, edad, ebs.educ_recat_casen, actividad, ebs.sg01)).astype(int)
    valores = ebs[["yy2", "yy4", "yy5"]].to_numpy(dtype=int)
    pesos = ebs.fexp.to_numpy(dtype=float)
    grupos = []
    for columnas in CELDAS:
        celdas = defaultdict(list)
        for i, fila in enumerate(datos):
            celdas[tuple(fila[j] for j in columnas)].append(i)
        grupos.append({
            k: (m, np.cumsum(pesos[m]))
            for k, m in celdas.items()
            if (pesos[m].sum() ** 2 / np.square(pesos[m]).sum()) >= 15
        })
    return grupos, valores, len(ebs)


def actitudes_cmf(ruta):
    grupos = defaultdict(list)
    with ruta.open(encoding="latin1", newline="") as archivo:
        for fila in csv.DictReader(archivo, delimiter=";"):
            sexo = next((i for i in (1, 2) if fila[f"D01{i}"] == "Yes"), None)
            estudio = next((i for i in range(1, 9) if fila[f"D09{i}"] == "Yes"), None)
            presente = next((i for i in range(1, 6) if fila[f"S03_6_Rp{i}"] == "Yes"), None)
            riesgo = next((i for i in range(1, 6) if fila[f"S01_2_Rp{i}"] == "Yes"), None)
            if None in (sexo, estudio, presente, riesgo):
                continue
            educacion = 1 if estudio <= 2 else 2 if estudio == 3 else 3
            for clave in ((sexo, educacion), (sexo, 0), (0, 0)):
                grupos[clave].append((presente, riesgo))
    return grupos


def preparar(origen, ebs, salida, cmf=None):
    plan = leer(origen / "plan-luna.json")
    diseno = leer(origen / "diseno.json")["catalogos"]["medoides_transporte"]
    pesos = dict(zip(diseno["id"], diseno["peso"], strict=True))
    n = len(pesos)
    ficha = plan["catalogos"][str(n)]["muestras"][str(n)]
    if set(ficha["ids"]) != pesos.keys() or len(ficha["ids"]) != n:
        raise ValueError("El plan y los pesos del catálogo deben tener los mismos IDs.")
    ficha["peso"] = [pesos[i] for i in ficha["ids"]]
    base = ficha["perfil"]
    observado = {}
    with np.load(origen / "variables-medoides_transporte.npz") as d:
        for id_, *fila in zip(d["id"], *(d[k] for k in COLUMNAS), strict=True):
            observado[str(id_)] = fila

    planes, asignacion = perfiles_asociados(base, observado, pesos, ebs, cmf)
    for brazo, perfiles in zip(BRAZOS[:len(planes)], planes, strict=True):
        ficha["perfil"] = perfiles
        guardar(salida / f"plan-{brazo}.json", plan)
    guardar(salida / "asignacion.json", asignacion)
    print(f"{n} arquetipos · {asignacion['donantes_validos']} donantes EBS · misma masa y pesos en {len(planes)} brazos", flush=True)


def perfiles_asociados(base, observado, pesos, ebs, cmf=None):
    grupos, valores, total = donantes(ebs)
    asignacion = {}
    financieros, justicia, completos, completos_justicia = {}, {}, {}, {}
    actitudes = actitudes_cmf(cmf) if cmf else None
    conteos = Counter()
    for id_, texto in base.items():
        semilla = int.from_bytes(hashlib.sha256(f"20261123:{id_}".encode()).digest()[:8], "little")
        rng = np.random.default_rng(semilla)
        fila = observado[id_]
        for nivel, (columnas, celdas) in enumerate(zip(CELDAS, grupos, strict=True)):
            celda = celdas.get(tuple(fila[j] for j in columnas))
            if celda is not None:
                miembros, acumulado = celda
                indice = miembros[np.searchsorted(acumulado, rng.random() * acumulado[-1], side="right")]
                break
        mes, reserva, deuda = map(int, valores[indice])
        preferencia = int(rng.integers(2))
        asignacion[id_] = {"mes": mes, "reserva_3_meses": reserva, "deuda": deuda, "justicia": preferencia,
                           "nivel_emparejamiento": nivel, "peso": pesos[id_]}
        conteos[nivel] += pesos[id_]
        financieros[id_] = (f"{texto}; el hogar llega a fin de mes {MES[mes - 1]}; "
                            f"si perdiera sus ingresos, cubriría necesidades básicas por tres meses "
                            f"{RESERVA[reserva - 1]}; {'tiene' if deuda == 1 else 'no tiene'} deuda no hipotecaria")
        justicia[id_] = financieros[id_] + "; " + JUSTICIA[preferencia]
        if actitudes:
            sexo, educacion = int(fila[4]), int(fila[2])
            opciones = actitudes.get((sexo, educacion)) or actitudes.get((sexo, 0)) or actitudes[(0, 0)]
            presente, riesgo = opciones[int(rng.integers(len(opciones)))]
            asignacion[id_].update(presente=presente, riesgo_financiero=riesgo)
            grados = ("muy en desacuerdo", "en desacuerdo", "neutral", "de acuerdo", "muy de acuerdo")
            completos[id_] = (financieros[id_] + f"; se declara {grados[presente - 1]} con que vive al día "
                              f"y presta poca atención al futuro; se declara {grados[riesgo - 1]} con que "
                              "está dispuesto a arriesgar parte de su dinero al invertir")
            completos_justicia[id_] = completos[id_] + "; " + JUSTICIA[preferencia]
    planes = [base, financieros, justicia]
    if actitudes:
        planes.extend([completos, completos_justicia])
    return planes, {"donantes_validos": total, "pesos_por_nivel": conteos, "fichas": asignacion}


def ejecutar(args, panel):
    n = len(leer(args.salida / "asignacion.json")["fichas"])
    planes = {b: leer(args.salida / f"plan-{b}.json") for b in args.brazos}

    def tarea(par):
        caso, brazo = par
        ruta = args.salida / caso["id"] / brazo
        datos = correr({**planes[brazo], "caso": caso["id"]}, n, n, ruta / "lotes",
                       args.lote, args.concurrencia, 2, pregunta=caso["pregunta"], referencia=None)
        guardar(ruta / "resultado.json", datos)
        print(f"{caso['id']} {brazo}: {datos['lotes_validos']}/{ceil(n / args.lote)} lotes · {datos['segundos']:.1f} s", flush=True)

    with ThreadPoolExecutor(max_workers=args.paralelo) as pool:
        list(pool.map(tarea, [(caso, brazo) for caso in panel for brazo in args.brazos]))


def resumir(args, panel):
    anterior = {r["id"]: r for r in leer(args.referencia)["casos"]}
    asignacion = leer(args.salida / "asignacion.json")["fichas"]
    n = len(asignacion)
    w = np.array([f["peso"] for f in asignacion.values()])
    j = np.array([f["justicia"] for f in asignacion.values()])
    resumen = []
    incompletos = []
    for caso in panel:
        id_ = caso["id"]
        r = anterior[id_]
        fila = {"id": id_, "nombre": r["nombre"], "cadem": r["cadem_pct"], "brazos": {}}
        for brazo in args.brazos:
            ruta = args.salida / id_ / brazo
            if brazo == "base" and n == 1000 and args.lote == 50:
                pct, segundos = r["luna_pct"], None
            else:
                archivo = ruta / "resultado.json"
                datos = leer(archivo) if archivo.is_file() else None
                if datos is None or (datos["lote"] != args.lote or datos["lotes_validos"] != ceil(n / args.lote)) or datos["pregunta"] != caso["pregunta"]:
                    incompletos.append((id_, brazo))
                    continue
                pct = datos["resultados"][str(n)]["diseno"]["pct"]
                segundos = datos["segundos"]
            delta = np.array(pct) - r["cadem_pct"]
            fila["brazos"][brazo] = {"pct": pct, "delta": delta.tolist(),
                                     "mae_2_pp": float(abs(delta[:2]).mean()), "segundos": segundos}
        for par in (("asociado", "asociado_justicia"), ("completo", "completo_justicia")):
            if not all(b in fila["brazos"] for b in par):
                continue
            a, b = (leer_votos(args.salida / id_ / k / "lotes") for k in par)
            cambios = np.eye(3)[np.array([b[i] for i in asignacion]) - 1] - np.eye(3)[np.array([a[i] for i in asignacion]) - 1]
            fila.setdefault("cambio_justicia_pp_por_criterio", {})[par[0]] = [
                (100 * np.average(cambios[j == k], axis=0, weights=w[j == k])).tolist() for k in (0, 1)
            ]
            votos_justicia = np.eye(3)[np.array([b[i] for i in asignacion]) - 1]
            por_criterio = [np.average(votos_justicia[j == k], axis=0, weights=w[j == k]) for k in (0, 1)]
            fila.setdefault("sensibilidad_justicia_pct", {})[par[0]] = {
                str(p): (100 * np.average(por_criterio, axis=0, weights=[p, 100 - p])).tolist()
                for p in (25, 50, 75)
            }
        resumen.append(fila)
    agregados = {}
    comparables = [f for f in resumen if all(b in f["brazos"] for b in args.brazos)]
    for brazo in args.brazos:
        x = [f["brazos"][brazo] for f in comparables]
        if x:
            agregados[brazo] = {"mae_2_pp": float(np.mean([r["mae_2_pp"] for r in x])),
                                "pct": np.mean([r["pct"] for r in x], axis=0).tolist(),
                                "delta": np.mean([r["delta"] for r in x], axis=0).tolist()}
    pesos = {}
    for k in ("mes", "reserva_3_meses", "deuda", "justicia", "presente", "riesgo_financiero"):
        if k not in next(iter(asignacion.values())):
            continue
        codigos = [f[k] for f in asignacion.values()]
        pesos[k] = (100 * np.bincount(codigos, weights=w) / w.sum()).tolist()
    datos = {"n": n, "casos": resumen, "incompletos": incompletos, "agregados": agregados,
             "pesos_pct_por_nivel": pesos, "masa": int(w.sum()), "n_efectivo": float(w.sum() ** 2 / (w @ w))}
    guardar(args.salida / "resumen.json", datos)
    print(json.dumps(datos, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paso", choices=("preparar", "ejecutar", "resumir"))
    p.add_argument("--origen", type=Path)
    p.add_argument("--ebs", type=Path)
    p.add_argument("--cmf", type=Path)
    p.add_argument("--salida", type=Path, required=True)
    p.add_argument("--panel", type=Path, default=Path("datos-pruebas/panel-cadem-perfil-base.json"))
    p.add_argument("--referencia", type=Path, default=Path("backend/data/cache/validacion-cadem-perfil-base/comparacion.json"))
    p.add_argument("--casos", nargs="+", default=CASOS)
    p.add_argument("--brazos", nargs="+", choices=BRAZOS)
    p.add_argument("--lote", type=int, default=50)
    p.add_argument("--concurrencia", type=int, default=6)
    p.add_argument("--paralelo", type=int, default=4)
    args = p.parse_args()
    if min(args.lote, args.concurrencia, args.paralelo) < 1:
        p.error("El lote, la concurrencia y el paralelismo deben ser positivos.")
    if args.paso == "preparar":
        if args.origen is None or args.ebs is None:
            p.error("Preparar requiere --origen y --ebs.")
        preparar(args.origen, args.ebs, args.salida, args.cmf)
        return
    disponibles = [b for b in BRAZOS if (args.salida / f"plan-{b}.json").is_file()]
    if args.brazos is None:
        args.brazos = disponibles
    if not args.brazos or set(args.brazos) - set(disponibles):
        p.error("Prepara los planes solicitados en el directorio de salida.")
    por_id = {c["id"]: c for c in leer(args.panel)}
    panel = [por_id[c] for c in args.casos]
    if args.paso == "ejecutar":
        ejecutar(args, panel)
    else:
        resumir(args, panel)


if __name__ == "__main__":
    main()
