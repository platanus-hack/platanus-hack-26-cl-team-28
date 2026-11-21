"""Reduce los catálogos completos, audita su composición y prepara muestras anidadas."""

import argparse
import json
from collections import Counter
from pathlib import Path
from time import perf_counter

import duckdb
import numpy as np

import personas_muestra as perfiles

CAMPOS = ("region", "zona", "edad", "educacion", "sexo", "laboral", "ocupacion", "viaje", "hogar")
MARGENES = ("region", "zona", "edad", "educacion", "sexo", "laboral")
SEMILLA = 20261121
TEXTO_TAG = (
    "El Gobierno anunció un acuerdo para reducir las tarifas del TAG de Autopista Central "
    "entre un 10% y un 25%, a partir de enero de 2027 a cambio de extender la concesión de "
    "la autopista por 20 meses. ¿Ud. está de acuerdo o en desacuerdo con esta decisión?"
)


def leer(con, personas, hogares=None):
    origen = "read_parquet(?)"
    union = "left join read_parquet(?) h on p.id_vivienda = h.id_vivienda and p.id_hogar = h.id_hogar and h.tipo_operativo = 2" if hogares else ""
    id_ = "0" if hogares else "id_persona_muestra"
    tipo = "h.tipologia_hogar" if hogares else "p.tipologia_hogar"
    filtro = "(p.edad >= 18 or p.edad_quinquenal >= 20)" if hogares else "p.edad >= 18"
    return con.execute(f"""
        select {id_} as id, p.region::utinyint as region, p.comuna::usmallint as comuna,
               case when p.area in (1,2) then p.area else 0 end::utinyint as zona,
               case when p.edad_quinquenal < 30 then 0 when p.edad_quinquenal < 45 then 1
                    when p.edad_quinquenal < 60 then 2 else 3 end::utinyint as edad,
               p.edad_quinquenal::utinyint as edad_fina,
               case when p.cine11 between 1 and 5 then 1 when p.cine11 in (6,7) then 2
                    when p.cine11 between 8 and 11 then 3 else 0 end::utinyint as educacion,
               p.sexo::utinyint as sexo,
               case when p.sit_fuerza_trabajo in (1,2,3) then p.sit_fuerza_trabajo else 0 end::utinyint as laboral,
               coalesce(case when p.cod_ciuo between 0 and 9 then p.cod_ciuo + 1 end, 0)::utinyint as ocupacion,
               case when p.p44_lug_trab = 1 then 8 when p.p45_medio_transporte between 1 and 7 then p.p45_medio_transporte
                    else 0 end::utinyint as viaje,
               coalesce({tipo}, 0)::utinyint as hogar
        from {origen} p {union} where {filtro}
    """, [str(personas), *([str(hogares)] if hogares else [])]).fetchnumpy()


def asignar(k, masa, capacidad):
    if capacidad.sum() < k or k < np.count_nonzero(capacidad):
        raise ValueError("El tamaño solicitado es incompatible con la cobertura de estratos.")
    cuotas = (capacidad > 0).astype(int)
    while cuotas.sum() < k:
        libres = capacidad - cuotas
        prioridad = masa * (libres > 0)
        ideal = (k - cuotas.sum()) * prioridad / prioridad.sum()
        incremento = np.minimum(libres, ideal.astype(int))
        candidatos = np.argsort(-np.where(libres > incremento, ideal % 1, -1), kind="stable")
        faltan = min(int(k - (cuotas + incremento).sum()), int((libres > incremento).sum()))
        incremento[candidatos[:faltan]] += 1
        cuotas += incremento
    return cuotas


def estrato(d):
    return d["region"].astype(np.int16) * 3 + d["zona"]


def ordenar(d):
    # Identidades estables desempatan perfiles con la misma firma demográfica.
    return np.lexsort(tuple(d[k] for k in ("id", "sexo", "hogar", "viaje", "ocupacion", "laboral",
                                           "edad_fina", "comuna", "educacion", "edad")) + (estrato(d),))


def reducir(d, orden, k, base):
    # Celdas exactas de territorio × edad × educación. Dentro de cada celda se
    # forman bloques contiguos con todos sus integrantes y se toma la ficha central.
    e = estrato(d)
    claves = (e * 4 + d["edad"].astype(np.int16)) * 4 + d["educacion"]
    cortes = np.r_[0, np.flatnonzero(np.diff(claves[orden])) + 1, len(orden)]
    cantidades = np.diff(cortes)
    cupos = asignar(k, cantidades, cantidades)
    reps, pesos, bordes = [], [], []
    for inicio, n, cuota in zip(cortes, cantidades, cupos):
        limites = inicio + np.arange(cuota + 1, dtype=np.int64) * n // cuota
        reps.append(orden[(limites[:-1] + limites[1:] - 1) // 2])
        pesos.append(np.diff(limites) * base)
        bordes.append(limites[1:])
    r, p = np.concatenate(reps), np.concatenate(pesos)
    assert len(r) == k and len(np.unique(r)) == k and p.sum() == len(orden) * base
    return r, p, np.r_[0, np.concatenate(bordes)]


def distribuciones(d, indices=None, peso=None):
    columnas = {k: d[k] if indices is None else d[k][indices] for k in CAMPOS if k != "ocupacion"}
    if "tag_rm" in d:
        columnas["tag_rm"] = d["tag_rm"] if indices is None else d["tag_rm"][indices]
    columnas["region_zona"] = columnas["region"].astype(np.int16) * 3 + columnas["zona"]
    columnas["edad_educacion"] = columnas["edad"] * 4 + columnas["educacion"]
    columnas["region_viaje"] = columnas["region"] * 9 + columnas["viaje"]
    columnas["region_comuna"] = d["comuna"] if indices is None else d["comuna"][indices]
    return {k: np.bincount(v, weights=peso) / len(v) if peso is None else np.bincount(v, weights=peso) / peso.sum()
            for k, v in columnas.items()}


def variaciones(a, b):
    rv = {}
    for k in a:
        n = max(len(a[k]), len(b[k]))
        rv[k] = float(50 * np.abs(np.pad(a[k], (0, n-len(a[k]))) - np.pad(b[k], (0, n-len(b[k])))).sum())
    return rv


def muestrear(d, indices, pesos, k, semilla):
    e = estrato(d)[indices]
    orden = np.argsort(e, kind="stable")
    cortes = np.r_[0, np.flatnonzero(np.diff(e[orden])) + 1, len(e)]
    capacidad = np.diff(cortes)
    masa = np.add.reduceat(pesos[orden], cortes[:-1])
    cuotas = asignar(k, masa, capacidad)
    rng = np.random.default_rng(semilla)
    elegidos, pesos_muestra = [], []
    for inicio, fin, q, n in zip(cortes[:-1], cortes[1:], cuotas, capacidad):
        # Se permuta igual para ambos tamaños, para que 1.000 se pueda reutilizar.
        seleccion = orden[inicio + rng.permutation(n)[:q]]
        elegidos.extend(seleccion)
        pesos_muestra.extend(pesos[seleccion] * (n / q))
    return indices[elegidos], np.asarray(pesos_muestra)


def ipf(d, indices, pesos, metas, margenes=MARGENES):
    w = pesos / pesos.sum()
    base = w.copy()
    for k in margenes:
        v = d[k][indices]
        n = max(len(metas[k]), int(v.max()) + 1)
        fuente = np.bincount(v, minlength=n)
        objetivo = np.pad(metas[k], (0, n-len(metas[k])))
        if np.any((fuente == 0) & (objetivo > 0)) or np.any((fuente > 0) & (objetivo == 0)):
            return None, f"sin soporte en {k}"
    for _ in range(150):
        for k in margenes:
            v = d[k][indices]
            meta = metas[k]
            obs = np.bincount(v, weights=w, minlength=len(meta))
            ajuste = np.divide(meta, obs, out=np.ones_like(meta), where=obs > 0)
            w = np.clip(w * ajuste[v], base * .2, base * 5)
        delta = max(np.abs(np.bincount(d[k][indices], weights=w, minlength=len(metas[k])) - metas[k]).max() for k in margenes)
        if delta < .0005 and abs(w.sum()-1) < .0005:
            return w / w.sum() * pesos.sum(), "convergió"
    return None, "límite de peso o iteraciones"


def diagnostico(d, indices, pesos, metas):
    return {"tv_pp": variaciones(metas, distribuciones(d, indices, pesos)),
            "n_efectivo": float(pesos.sum()**2 / np.square(pesos).sum()),
            "peso_maximo_relativo": float(pesos.max() / pesos.mean())}


def etiqueta(dic, valor, defecto=""):
    return dic.get(int(valor), defecto)


def armar_perfiles(d, indices):
    et = perfiles.cargar_etiquetas()
    retorno = {}
    for i in indices:
        identificador = str(d["id"][i])
        comuna = et["territorios"].get(("comuna", int(d["comuna"][i])), "")
        region = et["territorios"].get(("region", int(d["region"][i])), "")
        edad = int(d["edad_fina"][i])
        textos = [("85+" if edad >= 85 else f"{max(18,edad)}–{edad+4}") + " años",
                  etiqueta({1:"hombre",2:"mujer"}, d["sexo"][i]),
                  ", ".join(v for v in (comuna, region, etiqueta({1:"urbana",2:"rural"}, d["zona"][i])) if v),
                  etiqueta({1:"educación básica o menos",2:"educación media",3:"educación superior"}, d["educacion"][i]),
                  etiqueta({1:"trabaja",2:"busca empleo",3:"fuera de la fuerza laboral"}, d["laboral"][i]),
                  perfiles.OCUPACION.get(int(d["ocupacion"][i])-1,""),
                  etiqueta({1:"automóvil",2:"transporte público",3:"a pie",4:"bicicleta",5:"moto",6:"otro medio",7:"otro medio",8:"trabaja en casa"}, d["viaje"][i]),
                  etiqueta(et["censo"]["tipologia_hogar"], d["hogar"][i])]
        retorno[identificador] = "; ".join(x for x in textos if x)
    return retorno


def main():
    t = perf_counter()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--personas", type=Path, required=True)
    ap.add_argument("--hogares", type=Path, required=True)
    ap.add_argument("--datos", type=Path, default=Path("backend/data"))
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--bases", nargs="+", type=int, choices=(3, 5), default=[3, 5])
    ap.add_argument("--semilla", type=int, default=SEMILLA)
    ap.add_argument("--catalogos", nargs="+", type=int, default=[0, 500_000, 100_000])
    ap.add_argument("--muestras", nargs="+", type=int, default=[1000, 2000])
    args = ap.parse_args()
    tamanos_muestra = sorted(set(args.muestras))
    if min(tamanos_muestra) < 1 or any(k < 0 or 0 < k < tamanos_muestra[-1] for k in args.catalogos):
        ap.error("Cada catálogo debe poder contener la muestra más grande.")
    args.salida.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(config={"threads": 4, "memory_limit": "1500MB"}) as con:
        ref = leer(con, args.personas, args.hogares)
        metas = distribuciones(ref)
        adultos = len(ref["id"])
        del ref
        for base in args.bases:
            origen = "agentes_trios" if base == 3 else "agentes_grupos_5"
            d = leer(con, args.datos / origen / "region_*.parquet")
            orden = ordenar(d)
            np.save(args.salida / f"miembros-ordenados-{base}.npy", d["id"][orden])
            flujo = {}
            for k in dict.fromkeys(args.catalogos):
                if k:
                    ids, pesos, bordes = reducir(d, orden, k, base)
                    np.savez(args.salida / f"catalogo-{base}-{k}.npz", id=d["id"][ids], personas=pesos, bordes=bordes)
                else:
                    ids, pesos = orden, np.full(len(orden), base, dtype=np.int16)
                cat = {"fichas": len(ids), "personas_estimadas": int(pesos.sum()), "composicion": diagnostico(d, ids, pesos, metas)}
                muestras = {}
                anteriores = set()
                for n in tamanos_muestra:
                    i, w = muestrear(d, ids, pesos, n, args.semilla)
                    actuales = {str(x) for x in d["id"][i]}
                    if not anteriores <= actuales:
                        raise ValueError(f"Las cuotas de {n} no contienen la muestra anterior en el catálogo de {len(ids)}.")
                    anteriores = actuales
                    w_ipf, estado = ipf(d, i, w, metas)
                    muestras[n] = {"perfil": armar_perfiles(d, i), "ids": [str(x) for x in d["id"][i]],
                                   "peso": w.tolist(), "peso_ipf": w_ipf.tolist() if w_ipf is not None else None,
                                   "ipf": estado, "composicion": diagnostico(d, i, w, metas),
                                   "composicion_ipf": diagnostico(d, i, w_ipf, metas) if w_ipf is not None else None}
                cat["muestras"] = muestras
                flujo[k] = cat
                print(f"Base {base} · {len(ids):,} fichas · TV edad × educación: {cat['composicion']['tv_pp']['edad_educacion']:.3f} pp", flush=True)
            doc = {"base": base, "adultos_referencia": adultos, "semilla": args.semilla, "caso": "c698-tag",
                   "pregunta": TEXTO_TAG, "catalogos": flujo, "segundos": perf_counter()-t}
            temporal = args.salida / f".plan-{base}.tmp"
            temporal.write_text(json.dumps(doc, ensure_ascii=False))
            temporal.replace(args.salida / f"plan-{base}.json")
            del d, orden


if __name__ == "__main__":
    main()
