"""Compara grupos censales de tamaño fijo y permite exportar un catálogo de tríos."""

import argparse
import json
from itertools import combinations
from pathlib import Path
from time import perf_counter

import duckdb
import numpy as np

# Los últimos dos criterios solo se evalúan entre ocupados.
CAMPOS = (
    ("edad_quinquenal", 5, "case when p.edad = 14 then 1 else (p.edad_quinquenal - 15) // 5 + 2 end"),
    ("educacion", 4, "case when p.cine11 between 1 and 12 then p.cine11 else 0 end"),
    ("tipo_hogar", 3, "coalesce(h.tipologia_hogar, 0)"),
    ("tamano_hogar", 3, "coalesce(least(h.tamano, 5), 0)"),
    ("internet", 2, """case when 1 in (h.p15d_serv_internet_fija, h.p15e_serv_internet_movil,
                   h.p15f_serv_internet_satelital) then 1 when h.p15d_serv_internet_fija = 2
                   and h.p15e_serv_internet_movil = 2 and h.p15f_serv_internet_satelital = 2 then 2 else 0 end"""),
    ("dependencia_economica", 2, "case when p.depend_econ_deficit_hab in (1, 2) then p.depend_econ_deficit_hab else 0 end"),
    ("sector_economico", 5, "case when regexp_full_match(p.cod_caenes, '[A-U]') then ascii(p.cod_caenes) - 64 else 0 end"),
    ("movilidad_laboral", 4, "case when p.p44_lug_trab = 1 then 8 when p.p45_medio_transporte between 1 and 7 then p.p45_medio_transporte else 0 end"),
)
COMUNES = len(CAMPOS) - 2
PRIORIDAD = (0, 1, 2, 3, 5, 6, 4, 7)
ANCHOS = [ancho for _, ancho, _ in CAMPOS]
DESPLAZAMIENTOS = [sum(ANCHOS[:i]) for i in range(len(CAMPOS))]
ANCHO = sum(ANCHOS)
MASCARAS = [(2**a - 1) << d for a, d in zip(ANCHOS, DESPLAZAMIENTOS)]
BLOQUE = 30_000
TAMANOS = (10, 5, 3)
ELEGIBLE = "p.edad >= 14 or p.edad_quinquenal >= 15"


def preparar(con, personas, hogares):
    con.read_parquet(str(personas)).create_view("personas")
    con.read_parquet(str(hogares)).create_view("hogares")
    con.execute("""
        create temp table composicion as
        select id_vivienda, id_hogar, count(*) as tamano,
               count(*) filter (where edad_quinquenal >= 65) as mayores_65
        from personas where tipo_operativo = 2 group by 1, 2
    """)
    atributos = " | ".join(f"(({sql})::ubigint << {bit})" for (_, _, sql), bit in zip(CAMPOS, DESPLAZAMIENTOS))
    laboral = "case when p.edad = 14 then 4 when p.sit_fuerza_trabajo in (1, 2, 3) then p.sit_fuerza_trabajo else 0 end"
    ocupacion = "case when p.sit_fuerza_trabajo = 1 and p.cod_ciuo between 0 and 9 then p.cod_ciuo else 10 end"
    con.execute(f"""
        create temp view firmas as
        select p.id_vivienda, p.id_hogar, p.id_persona, p.region,
               (((((p.comuna * 3 + p.area) * 4 + p.tipo_operativo) * 5 + ({laboral})) * 11
                   + ({ocupacion}))::ubigint << {ANCHO}) | ({atributos}) as firma
        from personas p
        left join (select h.*, c.tamano from hogares h join composicion c using (id_vivienda, id_hogar)
                   where h.tipo_operativo = 2) h using (id_vivienda, id_hogar)
        where {ELEGIBLE}
    """)
    filas = con.execute("select firma, count(*)::integer as n from firmas group by firma order by firma").fetchnumpy()
    return filas["firma"], filas["n"]


def territorio(firmas):
    e = firmas >> ANCHO
    return e // 660, e // 220 % 3, e // 55 % 4, e // 11 % 5, e % 11


def formar(claves, indices, pendientes, n):
    if not len(indices):
        return np.empty((0, n), dtype=np.int32)
    orden = np.argsort(claves[indices], kind="stable")
    indices = indices[orden]
    ordenadas = claves[indices]
    comienzos = np.r_[0, np.flatnonzero(ordenadas[1:] != ordenadas[:-1]) + 1]
    largos = np.diff(np.r_[comienzos, len(indices)])
    acumulado = np.cumsum(pendientes[indices], dtype=np.int32)
    previos = np.r_[0, acumulado[comienzos[1:] - 1]]
    totales = acumulado[comienzos + largos - 1] - previos
    posiciones = acumulado - pendientes[indices] - np.repeat(previos, largos)
    consumidos = np.clip(np.repeat(totales // n * n, largos) - posiciones, 0, pendientes[indices])
    pendientes[indices] -= consumidos
    return np.repeat(indices.astype(np.int32), consumidos).reshape(-1, n)


def estricto(firmas, pendientes, n, ocupados, valido):
    presentes = np.zeros(len(firmas), dtype=np.uint8)
    for i, mascara in enumerate(MASCARAS):
        presentes |= ((firmas & mascara) != 0).astype(np.uint8) << i
    bloques = []
    etapas = {}
    for nombre, ambito, criterios in (("ocupados", valido & ocupados, len(CAMPOS)),
                                      ("resto", valido & ~ocupados, COMUNES)):
        minimo = (4 * criterios + 4) // 5
        indices = np.flatnonzero(ambito)
        for omisiones in range(criterios - minimo + 1):
            total = 0
            for omitir in combinations([i for i in reversed(PRIORIDAD) if i < criterios], omisiones):
                usar = [i for i in range(criterios) if i not in omitir]
                requerido = sum(1 << i for i in usar)
                activos = indices[(pendientes[indices] > 0) & ((presentes[indices] & requerido) == requerido)]
                mascara = ~np.uint64((2**ANCHO - 1) ^ sum(MASCARAS[i] for i in usar))
                grupos = formar(firmas & mascara, activos, pendientes, n)
                if len(grupos):
                    bloques.append(grupos)
                    total += len(grupos)
            etapas[f"{nombre}_{criterios-omisiones}_de_{criterios}"] = total
    return bloques, etapas


def completar(firmas, pendientes, n):
    comuna, area, _, laboral, _ = territorio(firmas)
    region = comuna // 1000
    for nombre, clave in (
        ("estrato_original", firmas >> ANCHO), ("comuna_zona_laboral", (comuna * 3 + area) * 5 + laboral),
        ("comuna_zona", comuna * 3 + area), ("region_zona", region * 3 + area),
        ("misma_zona", area), ("nacional", np.zeros_like(area)),
    ):
        grupos = formar(clave, np.flatnonzero(pendientes), pendientes, n)
        if len(grupos):
            yield nombre, grupos


def coincidencias(firma, otras, campos):
    aciertos = np.zeros(otras.shape, dtype=np.uint8)
    for m in campos:
        aciertos += ((firma & m) != 0) & (((firma ^ otras) & m) == 0)
    return aciertos


def distancia_a_miembros(firmas, grupos, ocupados):
    valores = firmas[grupos]
    n = grupos.shape[1]
    suma = np.zeros(grupos.shape, dtype=float)
    validos = np.ones(len(grupos), dtype=bool)
    for a, b in combinations(range(n), 2):
        ambos = ocupados[grupos[:, a]] & ocupados[grupos[:, b]]
        comunes = coincidencias(valores[:, a], valores[:, b], MASCARAS[:COMUNES])
        extra = coincidencias(valores[:, a], valores[:, b], MASCARAS[COMUNES:])
        aciertos = comunes + ambos * extra
        criterios = COMUNES + 2 * ambos
        distancia = 1 - aciertos / criterios
        suma[:, a] += distancia
        suma[:, b] += distancia
        validos &= aciertos * 5 >= criterios * 4
    return suma, validos


def composicion(firmas, original, representantes, n):
    comuna, zona, _, trabajo, ocupacion = territorio(firmas)
    edad, educacion, hogar = ((firmas & m) >> d for m, d in zip(MASCARAS[:3], DESPLAZAMIENTOS))
    return {nombre: variacion(codigo, original, representantes * n) for nombre, codigo in {
        "comuna_zona": comuna * 3 + zona, "region_zona": comuna // 1000 * 3 + zona,
        "edad_educacion": edad * 16 + educacion, "edad_hogar": edad * 8 + hogar,
        "laboral_ocupacion": trabajo * 11 + ocupacion,
    }.items()}


def variacion(codigo, original, estimado):
    codigo = codigo.astype(np.int64)
    a, b = np.bincount(codigo, weights=original), np.bincount(codigo, weights=estimado)
    return float(50 * np.abs(a / a.sum() - b / b.sum()).sum()) if b.sum() else None


def silueta(firmas, grupos, n, ocupados):
    if not grupos:
        return {"muestra": 0, "evaluadas": 0, "media": None, "negativas_pct": None}
    miembros = np.concatenate(grupos)
    claves = firmas[miembros[:, 0]] >> ANCHO
    orden = np.argsort(claves, kind="stable")
    miembros, claves = miembros[orden], claves[orden]
    rng = np.random.default_rng(2024)
    posiciones = rng.choice(miembros.size, min(2_000, miembros.size), replace=False)
    valores = []
    for pos in posiciones:
        fila, col = divmod(int(pos), n)
        izq = np.searchsorted(claves, claves[fila], side="left")
        der = np.searchsorted(claves, claves[fila], side="right")
        if der - izq < 2:
            continue
        origen = miembros[fila, col]
        campos = MASCARAS if ocupados[origen] else MASCARAS[:COMUNES]
        d = 1 - coincidencias(firmas[origen], firmas[miembros[izq:der]], campos) / len(campos)
        a = (d[fila-izq].sum() - d[fila-izq, col]) / (n - 1)
        d[fila-izq] = np.inf
        b = d.mean(axis=1).min()
        valores.append((b - a) / max(a, b) if max(a, b) else 0.0)
    return {"muestra": len(posiciones), "evaluadas": len(valores),
            "media": float(np.mean(valores)) if valores else None,
            "negativas_pct": float(100 * np.mean(np.array(valores) < 0)) if valores else None}


def comparar(firmas, original, n):
    inicio = perf_counter()
    pendientes = original.copy()
    _, zona, operativo, laboral, ocupacion = territorio(firmas)
    ocupados = laboral == 1
    valido = (operativo == 2) & np.isin(zona, (1, 2)) & (laboral != 0) & (~ocupados | (ocupacion != 10))
    estrictos, etapas = estricto(firmas, pendientes, n, ocupados, valido)
    masa_estricta = np.zeros(len(firmas), dtype=np.int32)
    masa_total = np.zeros_like(masa_estricta)
    cohesion = cohesion_estricta = 0.0
    cubiertas = 0
    for nombre, bloques in (("estricto", estrictos), ("relajado", completar(firmas, pendientes, n))):
        for item in bloques:
            etapa, grupos = (nombre, item) if nombre == "estricto" else item
            if nombre != "estricto":
                etapas[etapa] = len(grupos)
            for i in range(0, len(grupos), BLOQUE):
                g = grupos[i:i+BLOQUE]
                d, cumple = distancia_a_miembros(firmas, g, ocupados)
                medias = 1 - d.sum(axis=1) / (n * (n - 1))
                elegidos = g[np.arange(len(g)), d.argmin(axis=1)]
                np.add.at(masa_total, elegidos, 1)
                cohesion += float(medias.sum())
                if nombre == "estricto":
                    if not cumple.all():
                        raise AssertionError("Un grupo estricto bajó del 80%.")
                    cohesion_estricta += float(medias.sum())
                    np.add.at(masa_estricta, elegidos, 1)
                estratos = firmas[g] >> ANCHO
                aceptado = cumple & valido[g].all(axis=1) & (estratos == estratos[:, :1]).all(axis=1)
                cubiertas += int(aceptado.sum())
    total, strict, resto = int(masa_total.sum()), int(masa_estricta.sum()), int(pendientes.sum())
    poblacion = int(original.sum())
    assert total * n + resto == poblacion and 0 <= resto < n
    assert (masa_total <= original).all()
    metricas = {
        "tamano": n, "grupos": total, "personas_representadas": total * n, "remanente": resto,
        "grupos_etapa_estricta": strict, "grupos_que_cumplen_80_y_estrato": cubiertas,
        "cobertura_valida_pct": 100 * cubiertas * n / poblacion,
        "cohesion_pct": 100 * cohesion / total if total else None,
        "cohesion_estricta_pct": 100 * cohesion_estricta / strict if strict else None,
        "silueta": silueta(firmas, estrictos, n, ocupados),
        "distancia_variacion_total_pp": composicion(firmas, original, masa_total, n),
        "etapas": etapas, "segundos": perf_counter() - inicio,
    }
    return metricas, masa_total, masa_estricta


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("personas", type=Path)
    ap.add_argument("hogares", type=Path)
    ap.add_argument("--informe", type=Path, required=True)
    args = ap.parse_args()
    t = perf_counter()
    with duckdb.connect(config={"threads": 4, "memory_limit": "1600MB", "preserve_insertion_order": False}) as con:
        firmas, original = preparar(con, args.personas, args.hogares)
        informe = {"poblacion": int(original.sum()), "edad_minima": 14, "firmas": len(firmas),
                   "atributos": [c[0] for c in CAMPOS], "escenarios": {}}
        for n in TAMANOS:
            resultados, _, _ = comparar(firmas, original, n)
            informe["escenarios"][str(n)] = resultados
            print(f"{n}: {resultados['grupos']:,} grupos, {resultados['cobertura_valida_pct']:.2f}% cobertura válida", flush=True)
        informe["segundos"] = perf_counter() - t
        with args.informe.open("x", encoding="utf-8") as f:
            json.dump(informe, f, ensure_ascii=False, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
