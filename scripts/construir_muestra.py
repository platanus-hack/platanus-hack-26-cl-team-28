#!/usr/bin/env python3
"""Construye una muestra del 1 % de la población de Chile y la completa con Casen 2024.

Uso:
    uv run python -I scripts/construir_muestra.py data/censo2024 data/casen2024 data/muestra contexto/muestra

1. Sortea 1 de cada 100 hogares del Censo 2024 (muestreo sistemático ordenado por
   región, comuna, área y tamaño del hogar) y 1 de cada 100 personas en viviendas
   colectivas o en situación de calle.
2. Completa la edad exacta donde el censo la suprime y deriva los datos de familia
   que se pueden observar dentro del hogar.
3. Imputa desde Casen 2024, por emparejamiento estadístico, lo que el censo no
   pregunta: ingresos, previsión de salud, hijos de los hombres, y otros.

Escribe personas.parquet y hogares.parquet en la carpeta de salida, y README.md,
validacion.md y etiquetas_casen.csv en la carpeta de contexto. El resultado es
reproducible: depende solo de los datos y de SEMILLA.
"""

import re
import sys
from pathlib import Path

import duckdb
import numpy as np
import openpyxl
import pandas as pd

SEMILLA = 2024
PASO = 100  # se elige 1 de cada PASO
VECINOS = 7  # donantes candidatos en el emparejamiento de hogares

MACROZONA = {15: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 6: 2, 7: 2, 16: 2, 13: 3, 8: 4, 9: 4, 14: 4, 10: 4, 11: 5, 12: 5}

# Variables de Casen que se copian del hogar donante: nombre en Casen -> nombre en la muestra
DEL_HOGAR = {
    "dau": "decil_ingreso",
    "qaut": "quintil_ingreso",
    "ypchautcor": "ingreso_autonomo_pc",
    "ypchtotcor": "ingreso_total_pc",
    "pobreza": "pobreza_ingresos",
    "r14": "tiene_vehiculo",
    "r15": "n_vehiculos",
    "r7a": "red_cuidado_enfermedad",
    "r7b": "red_cuidado_dependientes",
    "r7c": "red_vehiculo",
    "r7d": "red_dinero",
    "r7e": "red_tramites",
    "r7f": "red_tecnologia",
    "r7g": "red_reparaciones",
    "r7h": "red_trabajo",
    "r7i": "red_consejo",
    "r8a": "inseg_alim_preocupacion",
    "r8b": "inseg_alim_no_saludable",
    "r8c": "inseg_alim_poca_variedad",
    "r8d": "inseg_alim_salto_comida",
    "r8e": "inseg_alim_comio_menos",
    "r8f": "inseg_alim_sin_alimentos",
    "r8g": "inseg_alim_hambre",
    "r8h": "inseg_alim_dia_sin_comer",
    "r9a": "discrim_nivel_socioeconomico",
    "r9b": "discrim_nivel_educacional",
    "r9u": "discrim_ocupacion",
    "r9c": "discrim_sexo",
    "r9d": "discrim_estado_civil",
    "r9e": "discrim_ropa",
    "r9f": "discrim_color_piel",
    "r9g": "discrim_extranjero",
    "r9h": "discrim_edad",
    "r9i": "discrim_orientacion_genero",
    "r9j": "discrim_tatuajes",
    "r9k": "discrim_apariencia",
    "r9l": "discrim_religion",
    "r9m": "discrim_politica",
    "r9n": "discrim_sindicato",
    "r9o": "discrim_lugar_residencia",
    "r9p": "discrim_establecimiento",
    "r9q": "discrim_pueblo_indigena",
    "r9r": "discrim_salud_discapacidad",
    "r9s": "discrim_otro",
    "r9t": "discrim_ninguna",
}

# Variables que se copian de la persona donante
DE_LA_PERSONA = {
    "s13": "prevision_salud",
    "s13_fonasa": "fonasa_grupo",
    "o15": "categoria_ocupacional",
    "contrato": "tiene_contrato",
    "cotiza": "cotiza_pension",
    "o26a": "sindicato",
    "r6": "participa_organizacion",
    "depen_grado": "dependencia_grado",
    "cuidador": "es_cuidador",
}
SOLO_OCUPADOS = ["categoria_ocupacional", "tiene_contrato", "sindicato"]

COLUMNAS_CASEN = sorted(
    set(DEL_HOGAR) | set(DE_LA_PERSONA)
    | {"folio", "id_persona", "region", "area", "expr", "expr_osig", "edad", "sexo", "pco1", "ecivil", "esc",
       "activ", "oficio1_08", "lugar_nac", "pueblos_indigenas", "disc_wg", "o28c", "o28a_hr", "o28a_min",
       "s5", "genero", "ten_viv", "v1", "ind_hacina", "r17a", "depen_fun"}
)


# ---------------------------------------------------------------- utilidades


def miles(n):
    return f"{int(round(n)):,}".replace(",", ".")


def dec(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def tabla_md(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    lineas += ["| " + " | ".join(str(c) for c in f) + " |" for f in filas]
    return "\n".join(lineas)


def recodificar(serie, mapa, resto, nulo):
    """Aplica un mapa de códigos; lo no mapeado queda en `resto` y los nulos en `nulo`."""
    return serie.map(mapa).where(serie.notna(), nulo).fillna(resto).astype("int64")


def celdas(don, rec, llaves):
    """Códigos de celda comunes para donantes y receptores según las llaves."""
    if not llaves:
        return np.zeros(len(don), "int64"), np.zeros(len(rec), "int64")
    junto = pd.concat([don[llaves], rec[llaves]], ignore_index=True)
    cod = junto.groupby(llaves, sort=False).ngroup().to_numpy()
    return cod[: len(don)], cod[len(don) :]


def emparejar(rec, don, niveles, peso, rng, min_don=3):
    """Hot-deck aleatorio por celdas con retroceso jerárquico.

    Para cada receptor busca donantes que compartan las llaves del nivel más
    específico con al menos `min_don` donantes, y sortea uno con probabilidad
    proporcional a su peso. Devuelve la posición del donante y el nivel usado.
    """
    elegido = np.full(len(rec), -1, "int64")
    nivel = np.zeros(len(rec), "int64")
    w = don[peso].to_numpy("float64")
    for i, llaves in enumerate(niveles, 1):
        pend = np.flatnonzero(elegido < 0)
        if len(pend) == 0:
            break
        cd, cr = celdas(don, rec.iloc[pend], llaves)
        orden = np.argsort(cd, kind="stable")
        cds, acum = cd[orden], np.cumsum(w[orden])
        ini = np.searchsorted(cds, cr, "left")
        fin = np.searchsorted(cds, cr, "right")
        ok = (fin - ini) >= (min_don if i < len(niveles) else 1)
        ini, fin, sel = ini[ok], fin[ok], pend[ok]
        base = np.where(ini > 0, acum[np.maximum(ini - 1, 0)], 0.0)
        objetivo = base + rng.random(len(sel)) * (acum[fin - 1] - base)
        pos = np.clip(np.searchsorted(acum, objetivo, "right"), ini, fin - 1)
        elegido[sel] = orden[pos]
        nivel[sel] = i
    if (elegido < 0).any():
        raise RuntimeError("quedaron receptores sin donante")
    return elegido, nivel


def emparejar_por_prediccion(rec, don, clases, peso, k, rng, min_don=10):
    """Emparejamiento por posición relativa del valor predicho, dentro de clases.

    Dentro de cada clase ordena a receptores y donantes por su valor predicho y
    le da a cada receptor un donante que ocupe su misma posición relativa en la
    distribución ponderada de donantes, con un margen aleatorio de `k` vecinos.
    Se empareja por posición y no por valor porque censo y Casen no miden igual
    las características del hogar: el censo registra algo menos de empleo y de
    educación, y emparejar por valor desplazaría todos los ingresos hacia abajo.
    """
    elegido = np.full(len(rec), -1, "int64")
    nivel = np.zeros(len(rec), "int64")
    pred_d, pred_r = don["pred"].to_numpy(), rec["pred"].to_numpy()
    w = don[peso].to_numpy("float64")
    for i, llaves in enumerate(clases, 1):
        pend = np.flatnonzero(elegido < 0)
        if len(pend) == 0:
            break
        cd, cr = celdas(don, rec.iloc[pend], llaves)
        for c in np.unique(cr):
            d = np.flatnonzero(cd == c)
            if len(d) < (min_don if i < len(clases) else 1):
                continue
            r = pend[cr == c]
            d = d[np.argsort(pred_d[d], kind="stable")]
            acum = np.cumsum(w[d]) / w[d].sum()
            rango = np.empty(len(r))
            rango[np.argsort(pred_r[r], kind="stable")] = np.arange(len(r))
            cuantil = (rango + rng.random(len(r))) / len(r)
            pos = np.searchsorted(acum, cuantil) + rng.integers(-(k // 2), k // 2 + 1, len(r))
            elegido[r] = d[np.clip(pos, 0, len(d) - 1)]
            nivel[r] = i
    if (elegido < 0).any():
        raise RuntimeError("quedaron hogares sin donante")
    return elegido, nivel


def grupos_persona(df):
    """Agrega las llaves agrupadas que comparten censo y Casen."""
    edad = df["edad"].clip(upper=85)
    df["edad5"] = (edad // 5 * 5).astype("int64")
    df["edad10"] = np.select([edad < 15, edad < 25, edad < 35, edad < 45, edad < 55, edad < 65, edad < 75], [0, 15, 25, 35, 45, 55, 65], 75)
    df["edadb"] = np.select([edad < 15, edad < 65], [0, 15], 65)
    esc = df["esc"]
    df["educ5"] = np.select(
        [df["edad"] < 15, esc.isna(), esc < 8, esc < 12, esc == 12, esc < 17], [0, 9, 1, 2, 3, 4], 5
    )
    df["educ3"] = df["educ5"].map({0: 0, 1: 1, 2: 1, 3: 2, 4: 3, 5: 3, 9: 9}).astype("int64")
    df["macro"] = df["region"].map(MACROZONA).astype("int64")
    return df


def rasgos_hogar(per, hog):
    """Rasgos de cada hogar a partir de sus personas, con la misma definición en ambas fuentes."""
    p = per[~per["sdpa"]]
    g = p.groupby("hk")
    r = pd.DataFrame(
        {
            "tam": g.size(),
            "n_ocup": (p["activ"] == 1).groupby(p["hk"]).sum(),
            "n_men18": (p["edad"] < 18).groupby(p["hk"]).sum(),
            "n_65": (p["edad"] >= 65).groupby(p["hk"]).sum(),
            "n_ocup_alto": (p["ciuo"].isin([1, 2, 3])).groupby(p["hk"]).sum(),
            "max_educ": p["educ5"].where(p["educ5"] != 9, 0).groupby(p["hk"]).max(),
        }
    )
    jefe = per[per["rol"] == 1].drop_duplicates("hk").set_index("hk")
    for c in ("sexo", "edad10", "educ5", "activ", "ciuo", "inmig", "indig"):
        r["j_" + c] = jefe[c]
    r = r.join(hog.set_index("hk")[["region", "area", "ten", "viv", "hacin", "inet"]])
    r["macro"] = r["region"].map(MACROZONA)
    r["tam5"] = r["tam"].clip(upper=5)
    r["tam6"] = r["tam"].clip(upper=6)
    r["n_ocup"] = r["n_ocup"].clip(upper=3)
    r["n_men18"] = r["n_men18"].clip(upper=3)
    r["n_65"] = r["n_65"].clip(upper=2)
    r["n_ocup_alto"] = r["n_ocup_alto"].clip(upper=2)
    return r.reset_index()


PREDICTORES = ["region", "area", "tam6", "j_sexo", "j_edad10", "j_educ5", "j_activ", "j_ciuo", "j_inmig", "j_indig",
               "ten", "viv", "hacin", "inet", "n_ocup", "n_men18", "n_65", "n_ocup_alto", "max_educ"]


def predecir_ingreso(don, rec):
    """Regresión ponderada del log del ingreso per cápita sobre los rasgos del hogar."""
    junto = pd.concat([don[PREDICTORES], rec[PREDICTORES]], ignore_index=True).astype("int64").astype("category")
    X = pd.get_dummies(junto, drop_first=True).to_numpy("float64")
    X = np.hstack([np.ones((len(X), 1)), X])
    Xd, y = X[: len(don)], np.log1p(don["ypchautcor"].to_numpy("float64"))
    raiz = np.sqrt(don["expr"].to_numpy("float64"))
    beta, *_ = np.linalg.lstsq(Xd * raiz[:, None], y * raiz, rcond=None)
    pred = X @ beta
    w = don["expr"].to_numpy("float64")
    media = np.average(y, weights=w)
    r2 = 1 - np.average((y - pred[: len(don)]) ** 2, weights=w) / np.average((y - media) ** 2, weights=w)
    return pred[: len(don)], pred[len(don) :], r2


# ---------------------------------------------------------------- pasos


def sortear(con, censo, rng):
    """Paso 1: muestra sistemática de hogares y de personas fuera de hogares."""
    P, H, V = (f"'{(censo / 'microdatos' / f'{t}_censo2024.parquet').as_posix()}'" for t in ("personas", "hogares", "viviendas"))
    i1, i2 = (int(x) for x in rng.integers(0, PASO, 2))
    con.execute(
        f"""create temp table hog_sel as
            with tam as (select id_vivienda, id_hogar, count(*) as n from {P} where tipo_operativo = 2 group by all)
            select id_vivienda, id_hogar from (
              select h.id_vivienda, h.id_hogar,
                     row_number() over (order by h.region, h.comuna, h.area, t.n, hash(h.id_vivienda, h.id_hogar, {SEMILLA})) as rn
              from {H} h join tam t using (id_vivienda, id_hogar) where h.tipo_operativo = 2)
            where (rn + {i1}) % {PASO} = 0"""
    )
    hogares = con.execute(
        f"""select h.*, v.* exclude (id_vivienda, region, provincia, comuna, comuna_bajo_umbral, area, tipo_operativo)
            from {H} h join hog_sel using (id_vivienda, id_hogar) join {V} v using (id_vivienda)
            order by h.region, h.comuna, h.id_vivienda, h.id_hogar"""
    ).df()
    personas = con.execute(
        f"""select p.* from {P} p join hog_sel using (id_vivienda, id_hogar)
            union all
            select * exclude (rn) from (
              select *, row_number() over (order by tipo_operativo, region, comuna, sexo, edad_quinquenal,
                                           hash(id_vivienda, id_persona, {SEMILLA})) as rn
              from {P} where tipo_operativo <> 2)
            where (rn + {i2}) % {PASO} = 0
            order by region, comuna, id_vivienda, id_hogar, id_persona"""
    ).df()
    edades = con.execute(
        f"select region, sexo, edad_quinquenal, edad, count(*) as n from {P} where edad >= 0 group by all order by all"
    ).df()
    totales = con.execute(
        f"select (select count(*) from {P}), (select count(*) from {H} where tipo_operativo = 2), (select count(*) from {P} where tipo_operativo <> 2)"
    ).fetchall()[0]
    return personas, hogares, edades, totales


def completar_edad(per, edades, rng):
    """Paso 2a: edad exacta para las comunas donde el censo solo entrega el tramo quinquenal."""
    falta = per["edad"] == -66
    per["edad_imputada"] = falta.astype("int8")
    if falta.any():
        llaves = ["region", "sexo", "edad_quinquenal"]
        don, _ = emparejar(per.loc[falta, llaves], edades, [llaves, llaves[1:]], "n", rng, min_don=1)
        per.loc[falta, "edad"] = edades["edad"].to_numpy()[don]
    return per


def derivar_familia(per):
    """Paso 2b: hijos, hermanos y educación de los padres observables dentro del hogar."""
    per["hk"] = np.where(per["tipo_operativo"] == 2, per["id_vivienda"] * 100 + per["id_hogar"], -1)
    en_hogar = per["tipo_operativo"] == 2
    par = per["parentesco"]
    cuenta = lambda cods: per["hk"].map(per.loc[en_hogar & par.isin(cods)].groupby("hk").size()).fillna(0)
    n_hijos, n_hijastros, n_hermanos = cuenta([5]), cuenta([6]), cuenta([7])

    per["hijos_en_hogar"] = np.select([par == 1, par.isin([2, 3, 4])], [n_hijos, n_hijos + n_hijastros], np.nan)
    per["hermanos_en_hogar"] = np.select([par.isin([5, 6]), par.isin([1, 7])], [n_hijos + n_hijastros - 1, n_hermanos], np.nan)
    per.loc[~en_hogar, ["hijos_en_hogar", "hermanos_en_hogar"]] = np.nan

    for c in ("esc_padre", "esc_madre", "cine11_padre", "cine11_madre"):
        per[c] = np.nan
    # (parentesco del hijo, parentesco del padre o madre dentro del mismo hogar)
    for hijos, padres in [([5], [1, 2, 3, 4]), ([6], [2, 3, 4]), ([1, 7], [8]), ([2, 3, 4], [10])]:
        fuente = per.loc[en_hogar & par.isin(padres), ["hk", "sexo", "escolaridad", "cine11"]]
        for sexo, quien in ((1, "padre"), (2, "madre")):
            f = fuente[fuente["sexo"] == sexo].drop_duplicates("hk").set_index("hk")
            m = en_hogar & par.isin(hijos)
            per.loc[m, "esc_" + quien] = per.loc[m, "hk"].map(f["escolaridad"])
            per.loc[m, "cine11_" + quien] = per.loc[m, "hk"].map(f["cine11"])
    per["vive_con_padre"] = per["cine11_padre"].notna().astype("int8")
    per["vive_con_madre"] = per["cine11_madre"].notna().astype("int8")
    for c in ("esc_padre", "esc_madre", "cine11_padre", "cine11_madre"):
        per[c] = per[c].where(per[c] >= 0)  # la no respuesta del padre o madre queda como nulo
    return per


def estandarizar_censo(per, hog):
    p = pd.DataFrame({"hk": per["hk"], "region": per["region"], "area": per["area"], "sexo": per["sexo"], "edad": per["edad"]})
    p["esc"] = per["escolaridad"].where(per["escolaridad"] >= 0).astype("float64")
    p["activ"] = recodificar(per["sit_fuerza_trabajo"], {1: 1, 2: 2, 3: 3}, 9, 0)
    p["ciuo"] = recodificar(per["cod_ciuo"], {i: i for i in range(10)}, 99, -1)
    p["cise"] = recodificar(per["p40_cise_rec"], {1: 1, 2: 2, 3: 3}, 9, -1)
    p["rol"] = recodificar(per["parentesco"], {1: 1, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3}, 4, 4)
    p["inmig"] = recodificar(per["p25_lug_nacimiento"], {1: 0, 2: 0, 3: 1}, 9, 9)
    p["indig"] = recodificar(per["p28_autoid_pueblo"], {1: 1, 2: 0}, 9, 9)
    p["disc"] = recodificar(per["discapacidad"], {1: 1, 2: 0}, 9, 0)
    p["modo"] = recodificar(per["p45_medio_transporte"], {2: 1, 1: 2, 5: 2, 3: 3, 4: 4, 6: 5, 7: 5}, 9, -1)
    p["estciv"] = recodificar(per["p23_est_civil"], {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2}, 9, 0)
    p["sdpa"] = per["parentesco"] == 16
    p["nh"] = per["hijos_en_hogar"].fillna(0).clip(upper=3).astype("int64")
    h = pd.DataFrame({"hk": hog["id_vivienda"] * 100 + hog["id_hogar"], "region": hog["region"], "area": hog["area"]})
    h["ten"] = recodificar(hog["p12_tenencia_viv"], {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4, 8: 4, 9: 4}, 9, 9)
    h["viv"] = recodificar(hog["p2_tipo_vivienda"], {1: 1, 3: 2}, 3, 3)
    h["hacin"] = recodificar(hog["indice_hacinamiento"], {1: 1, 2: 2, 3: 3}, 9, 9)
    h["inet"] = recodificar(hog["p15d_serv_internet_fija"], {1: 1, 2: 0}, 9, 9)
    return grupos_persona(p), h


def estandarizar_casen(c):
    p = pd.DataFrame({"hk": c["folio"].astype("int64"), "region": c["region"].astype("int64"), "area": c["area"].astype("int64"),
                      "sexo": c["sexo"].astype("int64"), "edad": c["edad"].astype("int64")})
    p["esc"] = c["esc"].where(c["esc"] >= 0).astype("float64")
    p["activ"] = recodificar(c["activ"], {1: 1, 2: 2, 3: 3}, 9, 0)
    p["ciuo"] = recodificar(c["oficio1_08"], {i: i for i in range(10)}, 99, -1)
    p["cise"] = recodificar(c["o15"], {1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2, 9: 3}, 9, -1)
    p["rol"] = recodificar(c["pco1"], {1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3}, 4, 4)
    p["inmig"] = recodificar(c["lugar_nac"], {0: 0, 1: 1}, 9, 9)
    p["indig"] = recodificar(c["pueblos_indigenas"], {0: 0, 1: 1}, 9, 9)
    p["disc"] = recodificar(c["disc_wg"], {0: 0, 1: 1}, 9, 0)
    p["modo"] = recodificar(c["o28c"], {1: 1, 2: 2, 6: 2, 3: 3, 4: 4, 5: 5}, 9, -1)
    p["estciv"] = recodificar(c["ecivil"], {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 2, 7: 2, 8: 2}, 9, 0)
    p["sdpa"] = c["pco1"] == 15
    hijos = c["pco1"].isin([4, 5]).groupby(p["hk"]).transform("sum")
    hijastros = (c["pco1"] == 6).groupby(p["hk"]).transform("sum")
    p["nh"] = np.select([p["rol"] == 1, p["rol"] == 2], [hijos, hijos + hijastros], 0).clip(max=3).astype("int64")
    jefe = c[c["pco1"] == 1].drop_duplicates("folio")
    h = pd.DataFrame({"hk": jefe["folio"].astype("int64"), "region": jefe["region"].astype("int64"), "area": jefe["area"].astype("int64")})
    h["ten"] = recodificar(jefe["ten_viv"], {1: 1, 2: 2, 3: 3, 4: 4}, 9, 9)
    h["viv"] = recodificar(jefe["v1"], {1: 1, 2: 1, 3: 1, 4: 2, 5: 2}, 3, 3)
    h["hacin"] = recodificar(jefe["ind_hacina"], {1: 1, 2: 2, 3: 3, 4: 3}, 9, 9)
    h["inet"] = recodificar(jefe["r17a"], {1: 1, 2: 0}, 9, 9)
    return grupos_persona(p), h


def etiquetas_casen(casen_dir, variables):
    """Lee del libro de códigos las categorías de las variables usadas."""
    wb = openpyxl.load_workbook(casen_dir / "docs" / "Libro_de_codigos_Casen_2024.xlsx", read_only=True, data_only=True)
    filas, descripcion = [], {}
    for ws in wb.worksheets:
        actual = None
        for r in ws.iter_rows(values_only=True):
            if len(r) < 5:
                continue
            if r[1] and r[1] != "Nombre variable" and r[2]:
                actual = str(r[1])
                descripcion[actual] = re.sub(r"\s+", " ", str(r[2])).strip()
            if actual in variables and r[3] is not None and re.fullmatch(r"-?\d+", str(r[3]).strip()):
                filas.append((variables[actual], actual, int(r[3]), re.sub(r"\s+", " ", str(r[4])).strip()))
    wb.close()
    return pd.DataFrame(filas, columns=["columna", "variable_casen", "valor", "etiqueta"]).drop_duplicates(), descripcion


# ---------------------------------------------------------------- principal


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    censo, casen_dir, salida, contexto = (Path(a) for a in sys.argv[1:])
    salida.mkdir(parents=True, exist_ok=True)
    contexto.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEMILLA)
    con = duckdb.connect()

    print("1. Sorteando la muestra del censo ...", flush=True)
    per, hog, edades, (n_per, n_hog, n_fuera) = sortear(con, censo, rng)
    per = completar_edad(per, edades, rng)
    per = derivar_familia(per)
    hog["hk"] = hog["id_vivienda"] * 100 + hog["id_hogar"]
    en_hogar = (per["tipo_operativo"] == 2).to_numpy()
    print(f"   {len(hog):,} hogares y {len(per):,} personas ({en_hogar.sum():,} en hogares)")

    print("2. Leyendo Casen ...", flush=True)
    cols = ", ".join(COLUMNAS_CASEN)
    casen = con.execute(f"select {cols} from '{(casen_dir / 'casen_2024.parquet').as_posix()}' order by folio, id_persona").df()
    casen = casen[casen["folio"].isin(casen.loc[casen["dau"].notna(), "folio"])].reset_index(drop=True)
    cp, ch = estandarizar_casen(casen)
    rp, rh = estandarizar_censo(per[en_hogar].reset_index(drop=True), hog)
    cp["expr"] = casen["expr"].to_numpy()

    print("3. Emparejando hogares (ingresos, vehículos, redes, alimentación, discriminación) ...", flush=True)
    dh = rasgos_hogar(cp, ch).merge(casen[casen["pco1"] == 1].drop_duplicates("folio")[["folio", "expr", *DEL_HOGAR]],
                                   left_on="hk", right_on="folio")
    hh = rasgos_hogar(rp, rh)
    hh = hog[["hk"]].merge(hh, on="hk", how="left")  # mismo orden que `hog`
    dh["pred"], hh["pred"], r2 = predecir_ingreso(dh, hh)
    clases = [["region", "area", "tam5", "j_inmig", "j_indig"], ["macro", "area", "tam5", "j_inmig", "j_indig"],
              ["area", "tam5", "j_inmig"], ["tam5"]]
    don_h, nivel_h = emparejar_por_prediccion(hh, dh, clases, "expr", VECINOS, rng)
    for origen, destino in DEL_HOGAR.items():
        hog[destino] = dh[origen].to_numpy()[don_h]
    hog["n_vehiculos"] = hog["n_vehiculos"].where(hog["tiene_vehiculo"] == 1, 0)
    hog["inseg_alim_n"] = (hog[[d for o, d in DEL_HOGAR.items() if o.startswith("r8")]] == 1).sum(axis=1)
    hog["casen_folio_donante"] = dh["folio"].to_numpy()[don_h]
    hog["nivel_match_hogar"] = nivel_h
    print(f"   R2 ponderado del modelo de ingreso: {r2:.3f}; niveles usados: {np.bincount(nivel_h)[1:].tolist()}")

    print("4. Emparejando personas (previsión, trabajo, participación, cuidados) ...", flush=True)
    decil_h = hog.set_index("hk")["decil_ingreso"]
    rp["decil"] = rp["hk"].map(decil_h).astype("int64")
    # El servicio doméstico puertas adentro no tiene decil propio en Casen: se usa el del hogar.
    cp["decil"] = cp["hk"].map(casen.dropna(subset=["dau"]).drop_duplicates("folio").set_index("folio")["dau"]).astype("int64")
    for d in (rp, cp):
        d["quintil"] = (d["decil"] + 1) // 2
    prev3 = lambda s: recodificar(s, {1: 1, 2: 2}, 3, 3)
    cp["jefe_prev"] = cp["hk"].map(prev3(casen.loc[casen["pco1"] == 1].drop_duplicates("folio").set_index("folio")["s13"]))
    base = ["sexo", "edad5", "educ5", "activ", "cise", "disc"]
    grueso = ["sexo", "edad10", "educ3", "activ", "cise"]
    niveles = [base + ["decil", "region", "area", "ciuo", "rol", "inmig"], base + ["decil", "region", "ciuo"],
               base + ["decil", "macro"], base + ["decil"], base + ["quintil"], grueso + ["disc", "decil"],
               grueso + ["quintil"], ["sexo", "edad10", "activ", "cise"], ["sexo", "edad10", "activ"], ["sexo", "edadb"], []]
    don_p = np.full(len(rp), -1, "int64")
    nivel_p = np.zeros(len(rp), "int64")
    jefes = (rp["rol"] == 1).to_numpy()
    don_p[jefes], nivel_p[jefes] = emparejar(rp[jefes], cp, niveles, "expr", rng)
    # El resto del hogar se empareja además por el sistema de salud de su jefatura, como en Casen.
    rp["jefe_prev"] = rp["hk"].map(pd.Series(prev3(casen["s13"]).to_numpy()[don_p[jefes]], index=rp.loc[jefes, "hk"]))
    rp["jefe_prev"] = rp["jefe_prev"].fillna(3).astype("int64")
    niveles_resto = [n + ["jefe_prev"] for n in niveles[:8]] + niveles[8:]
    don_p[~jefes], nivel_p[~jefes] = emparejar(rp[~jefes], cp, niveles_resto, "expr", rng)
    imput = pd.DataFrame({destino: casen[origen].to_numpy()[don_p] for origen, destino in DE_LA_PERSONA.items()})
    imput.loc[(rp["activ"] != 1).to_numpy(), SOLO_OCUPADOS] = np.nan
    imput.loc[(rp["edad"] < 15).to_numpy(), "cotiza_pension"] = np.nan
    imput["dependencia_grado"] = imput["dependencia_grado"].fillna(0).where((rp["edad"] >= 15).to_numpy())
    imput.loc[imput["prevision_salud"] != 1, "fonasa_grupo"] = np.nan
    imput["nivel_match_persona"] = nivel_p
    imput["casen_folio_donante"] = casen["folio"].to_numpy()[don_p]
    imput["casen_id_persona_donante"] = casen["id_persona"].to_numpy()[don_p]
    imput["decil_ingreso"] = rp["decil"].to_numpy()
    imput["quintil_ingreso"] = rp["quintil"].to_numpy()

    # Tiempo de traslado: mismo medio de transporte que declara la persona en el censo.
    viaja = rp["modo"].between(1, 5).to_numpy()
    dv = cp[(casen["o28a_hr"] >= 0).to_numpy() & (casen["o28a_min"] >= 0).to_numpy() & cp["modo"].between(1, 5).to_numpy()]
    minutos = (casen["o28a_hr"] * 60 + casen["o28a_min"]).to_numpy()[dv.index]
    dv = dv.reset_index(drop=True)
    d, _ = emparejar(rp[viaja], dv, [["modo", "region", "area", "quintil"], ["modo", "region", "area"],
                                     ["modo", "macro", "area"], ["modo", "area"], ["modo"], []], "expr", rng)
    imput["tiempo_traslado_min"] = np.nan
    imput.loc[viaja, "tiempo_traslado_min"] = minutos[d]

    # Género: solo lo respondieron los adultos presentes en la entrevista, con su propio factor.
    adulto = (rp["edad"] >= 18).to_numpy()
    filtro = casen["genero"].notna().to_numpy()
    dg = cp[filtro].reset_index(drop=True)
    dg["expr_osig"] = casen.loc[filtro, "expr_osig"].to_numpy()
    d, _ = emparejar(rp[adulto], dg, [["sexo", "edad5", "educ5", "region"], ["sexo", "edad5", "educ3"],
                                      ["sexo", "edad10"], ["sexo"], []], "expr_osig", rng)
    imput["genero"] = np.nan
    imput.loc[adulto, "genero"] = casen.loc[filtro, "genero"].to_numpy()[d]

    # Hijos nacidos vivos: observado en el censo para mujeres de 15+; el resto se imputa.
    p_hog = per[en_hogar].reset_index(drop=True)
    observado = (p_hog["p46a_tot_hijs_nac"] >= 0).fillna(False).to_numpy(bool)
    falta = np.logical_not(observado) & (rp["edad"] >= 12).to_numpy()
    filtro = (casen["s5"] >= 0).to_numpy()
    ds = cp[filtro].reset_index(drop=True)
    d, _ = emparejar(rp[falta], ds, [["sexo", "edad5", "nh", "estciv", "educ5", "quintil"], ["sexo", "edad5", "nh", "estciv", "educ3"],
                                     ["sexo", "edad5", "nh", "estciv"], ["sexo", "edad10", "nh"], ["sexo", "edad10"], ["sexo"], []],
                     "expr", rng)
    imput["hijos_total"] = p_hog["p46a_tot_hijs_nac"].where(observado).astype("float64")
    imput.loc[falta, "hijos_total"] = np.maximum(casen.loc[filtro, "s5"].to_numpy()[d], p_hog.loc[falta, "hijos_en_hogar"].fillna(0).to_numpy())
    imput["hijos_origen"] = np.select([observado, falta], ["censo", "casen"], None)

    print("5. Escribiendo resultados ...", flush=True)
    hog.insert(0, "id_hogar_muestra", np.arange(1, len(hog) + 1))
    hog["n_personas"] = hog["hk"].map(per[en_hogar].groupby("hk").size()).to_numpy()
    completo = pd.DataFrame(index=per.index, columns=imput.columns)
    completo.loc[en_hogar] = imput.to_numpy()
    fuera = ~en_hogar
    mujeres_fuera = fuera & (per["p46a_tot_hijs_nac"] >= 0).fillna(False).to_numpy(bool)
    completo.loc[mujeres_fuera, "hijos_total"] = per.loc[mujeres_fuera, "p46a_tot_hijs_nac"]
    completo.loc[mujeres_fuera, "hijos_origen"] = "censo"
    numericas = [c for c in imput.columns if c != "hijos_origen"]
    completo[numericas] = completo[numericas].apply(pd.to_numeric)
    per = pd.concat([per, completo], axis=1)
    per.insert(0, "id_persona_muestra", np.arange(1, len(per) + 1))
    per.insert(1, "id_hogar_muestra", per["hk"].map(hog.set_index("hk")["id_hogar_muestra"]).astype("Int64"))
    enteras = [c for c in per.columns if c not in ("hijos_origen", "cod_caenes") and per[c].dtype.kind == "f"
               and (per[c].dropna() % 1 == 0).all()]
    per[enteras] = per[enteras].astype("Int64")
    enteras_h = [c for c in hog.columns if hog[c].dtype.kind == "f" and (hog[c].dropna() % 1 == 0).all()]
    hog[enteras_h] = hog[enteras_h].astype("Int64")
    per = per.drop(columns=["hk"])
    hog = hog.drop(columns=["hk"])
    per.to_parquet(salida / "personas.parquet", index=False)
    hog.to_parquet(salida / "hogares.parquet", index=False)

    # Tabla única: una fila por persona con las columnas de su hogar y vivienda al lado.
    solo_hogar = [c for c in hog.columns if c not in per.columns]
    del_hogar = hog[["id_hogar_muestra", "casen_folio_donante", *solo_hogar]].rename(
        columns={"casen_folio_donante": "casen_folio_donante_hogar"}
    )
    del_hogar["id_hogar_muestra"] = del_hogar["id_hogar_muestra"].astype("Int64")
    todo = per.merge(del_hogar, on="id_hogar_muestra", how="left", validate="many_to_one")
    assert len(todo) == len(per)
    # Las personas fuera de hogares dejan nulos que convierten los códigos en decimales: se vuelven a enteros.
    a_enteras = [c for c in solo_hogar if todo[c].dtype.kind == "f" and (todo[c].dropna() % 1 == 0).all()]
    todo[a_enteras] = todo[a_enteras].astype("Int64")
    todo.to_parquet(salida / "muestra.parquet", index=False)
    todo.to_csv(salida / "muestra.csv", index=False)
    print(f"   tabla única: {len(todo):,} filas y {todo.shape[1]} columnas")

    etiquetas, descripcion = etiquetas_casen(casen_dir, {**DEL_HOGAR, **DE_LA_PERSONA, "genero": "genero"})
    etiquetas.to_csv(contexto / "etiquetas_casen.csv", index=False)

    documentar(contexto, per, hog, casen, cp, descripcion, etiquetas, censo, con,
               dict(n_per=n_per, n_hog=n_hog, n_fuera=n_fuera, r2=r2, nivel_h=nivel_h, nivel_p=nivel_p))
    print(f"Listo: {len(per):,} personas y {len(hog):,} hogares en {salida}")


# ---------------------------------------------------------------- documentación y validación


def documentar(contexto, per, hog, casen, cp, descripcion, etiquetas, censo, con, info):
    fallas = []

    def comprobar(nombre, condicion, detalle):
        print(f"   {'OK   ' if condicion else 'FALLA'} {nombre}: {detalle}")
        if not condicion:
            fallas.append(nombre)

    en_hogar = per["tipo_operativo"] == 2
    comprobar("tamaño de la muestra de personas", abs(len(per) / info["n_per"] * PASO - 1) < 0.005,
              f"{len(per):,} de {info['n_per']:,} ({len(per) / info['n_per'] * 100:.3f} %)")
    comprobar("tamaño de la muestra de hogares", abs(len(hog) / info["n_hog"] * PASO - 1) < 0.001, f"{len(hog):,} de {info['n_hog']:,}")
    comprobar("todos los hogares tienen decil", hog["decil_ingreso"].notna().all(), "sin nulos")
    comprobar("todas las personas en hogares tienen previsión", per.loc[en_hogar, "prevision_salud"].notna().all(), "sin nulos")
    comprobar("no quedan edades suprimidas", (per["edad"] >= 0).all(), "edad >= 0")

    # A. Muestra contra censo completo
    P = f"'{(censo / 'microdatos' / 'personas_censo2024.parquet').as_posix()}'"
    H = f"'{(censo / 'microdatos' / 'hogares_censo2024.parquet').as_posix()}'"
    filas_a, peor = [], 0.0
    for tabla, origen, df, variables in [
        ("personas", P, per, ["sexo", "region", "area", "edad_quinquenal", "cine11", "sit_fuerza_trabajo", "p23_est_civil",
                              "p28_autoid_pueblo", "p25_lug_nacimiento", "p31_religion_rec", "tipo_operativo"]),
        ("hogares", f"(select * from {H} where tipo_operativo = 2)", hog, ["region", "tipologia_hogar", "p12_tenencia_viv", "p15d_serv_internet_fija"]),
    ]:
        for v in variables:
            censo_pct = dict(con.execute(f"select coalesce({v}, -1), 100.0 * count(*) / sum(count(*)) over () from {origen} group by 1").fetchall())
            muestra_pct = (df[v].astype("float64").fillna(-1).value_counts(normalize=True) * 100).to_dict()
            dif = max(abs(muestra_pct.get(k, 0) - p) for k, p in censo_pct.items())
            peor = max(peor, dif)
            filas_a.append((f"`{tabla}.{v}`", len(censo_pct), dec(dif, 2)))
    comprobar("la muestra reproduce las distribuciones del censo", peor < 0.5, f"diferencia máxima {peor:.2f} puntos")
    comunas = con.execute(f"select comuna, count(*) from {P} group by 1").df()
    comunas.columns = ["comuna", "censo"]
    comunas["muestra"] = comunas["comuna"].map(per.groupby("comuna").size()).fillna(0)
    comunas["dif"] = comunas["muestra"] - comunas["censo"] / PASO

    # B. Imputaciones contra Casen ponderada
    w = casen["expr"].to_numpy("float64")
    jefes_c = (casen["pco1"] == 1).to_numpy()

    def casen_pct(col, filtro=None, peso=w):
        m = casen[col].notna().to_numpy() if filtro is None else filtro
        s = pd.Series(peso[m]).groupby(casen.loc[m, col].to_numpy()).sum()
        return (s / s.sum() * 100).to_dict()

    def muestra_pct(df, col, filtro=None):
        s = df[col] if filtro is None else df.loc[filtro, col]
        return (s.dropna().astype("float64").value_counts(normalize=True) * 100).to_dict()

    etq = {(r.columna, r.valor): r.etiqueta for r in etiquetas.itertuples()}
    filas_b = []

    def comparar(titulo, col, m_pct, c_pct, valores=None):
        for v in valores or sorted(set(m_pct) | set(c_pct)):
            if v < 0:
                continue
            filas_b.append((titulo, re.sub(r"^\d+\.\s*", "", etq.get((col, int(v)), str(int(v))))[:45], dec(m_pct.get(v, 0)), dec(c_pct.get(v, 0))))

    comparar("Decil de ingreso (hogares)", "decil_ingreso", muestra_pct(hog, "decil_ingreso"), casen_pct("dau", jefes_c & casen["dau"].notna().to_numpy()))
    comparar("Previsión de salud (personas)", "prevision_salud", muestra_pct(per, "prevision_salud"), casen_pct("s13"))
    comparar("Grupo de Fonasa", "fonasa_grupo", muestra_pct(per, "fonasa_grupo"), casen_pct("s13_fonasa"))
    comparar("Hogar con vehículo", "tiene_vehiculo", muestra_pct(hog, "tiene_vehiculo"), casen_pct("r14", jefes_c))
    comparar("Pobreza por ingresos (personas)", "pobreza_ingresos",
             muestra_pct(per.merge(hog[["id_hogar_muestra", "pobreza_ingresos"]], on="id_hogar_muestra"), "pobreza_ingresos"), casen_pct("pobreza"))
    comparar("Categoría ocupacional (ocupados)", "categoria_ocupacional", muestra_pct(per, "categoria_ocupacional"), casen_pct("o15"))
    comparar("Cotiza para pensión (15+)", "cotiza_pension", muestra_pct(per, "cotiza_pension"), casen_pct("cotiza"))
    comparar("Participa en organizaciones", "participa_organizacion", muestra_pct(per, "participa_organizacion"), casen_pct("r6"), [1, 2, 3, 15])
    comparar("Género (18+)", "genero", muestra_pct(per, "genero"), casen_pct("genero", peso=casen["expr_osig"].fillna(0).to_numpy("float64")))
    comparar("Preocupación por falta de alimentos (hogares)", "inseg_alim_preocupacion", muestra_pct(hog, "inseg_alim_preocupacion"), casen_pct("r8a", jefes_c), [1])
    hombres = (per["sexo"] == 1) & (per["edad"] >= 15) & en_hogar
    hc = ((casen["sexo"] == 1) & (casen["edad"] >= 15) & (casen["s5"] >= 0)).to_numpy()
    medias = [
        ("Hijos por hombre de 15+ (imputado)", per.loc[hombres, "hijos_total"].astype("float64").mean(), np.average(casen.loc[hc, "s5"], weights=w[hc])),
        ("Hijos por mujer de 15+ (censo vs. Casen)", per.loc[(per["sexo"] == 2) & (per["edad"] >= 15) & (per["hijos_origen"] == "censo"), "hijos_total"].astype("float64").mean(),
         np.average(casen.loc[(casen["sexo"] == 2) & (casen["edad"] >= 15) & (casen["s5"] >= 0), "s5"],
                    weights=w[((casen["sexo"] == 2) & (casen["edad"] >= 15) & (casen["s5"] >= 0)).to_numpy()])),
        ("Minutos de traslado al trabajo", per["tiempo_traslado_min"].astype("float64").mean(),
         np.average((casen["o28a_hr"] * 60 + casen["o28a_min"])[(casen["o28a_hr"] >= 0) & (casen["o28c"].notna())],
                    weights=w[((casen["o28a_hr"] >= 0) & (casen["o28c"].notna())).to_numpy()])),
        ("Ingreso autónomo per cápita del hogar, mediana de hogares ($)", hog["ingreso_autonomo_pc"].median(),
         float(casen.loc[jefes_c].sort_values("ypchautcor")["ypchautcor"].iloc[np.searchsorted(np.cumsum(casen.loc[jefes_c].sort_values("ypchautcor")["expr"]), w[jefes_c].sum() / 2)])),
    ]
    isapre_por_decil = per[en_hogar].groupby("decil_ingreso")["prevision_salud"].apply(lambda s: (s == 2).mean() * 100)
    isapre_casen = pd.Series(w * (casen["s13"] == 2)).groupby(casen["dau"].to_numpy()).sum() / pd.Series(w).groupby(casen["dau"].to_numpy()).sum() * 100
    mixtos = per[en_hogar].groupby("id_hogar_muestra")["prevision_salud"].nunique().gt(1).mean() * 100
    mixtos_casen = np.average(casen.groupby("folio")["s13"].nunique().gt(1), weights=casen.groupby("folio")["expr"].first()) * 100

    niveles_h = np.bincount(info["nivel_h"], minlength=5)[1:]
    niveles_p = np.bincount(info["nivel_p"], minlength=12)[1:]
    val = [
        "# Validación de la muestra del 1 %",
        "",
        "Generado por `scripts/construir_muestra.py`. Todas las cifras se recalculan en cada ejecución.",
        "",
        "## A. La muestra frente al censo completo",
        "",
        f"La muestra tiene {miles(len(per))} personas ({dec(len(per) / info['n_per'] * 100, 3)} % de {miles(info['n_per'])}) y {miles(len(hog))} hogares "
        f"({dec(len(hog) / info['n_hog'] * 100, 3)} % de {miles(info['n_hog'])}).",
        "Para cada variable se compara la distribución porcentual en la muestra y en el censo, y se informa la mayor diferencia entre categorías, en puntos porcentuales.",
        "",
        tabla_md(["Variable", "Categorías", "Diferencia máxima (pp)"], filas_a),
        "",
        f"Por comuna, la muestra se aleja del 1 % exacto en {dec(comunas['dif'].abs().mean(), 1)} personas en promedio y en {dec(comunas['dif'].abs().max(), 0)} como máximo. "
        f"Comunas sin ninguna persona en la muestra: {int((comunas['muestra'] == 0).sum())}, de las más pequeñas del país.",
        "",
        "## B. Los datos imputados frente a Casen",
        "",
        "Las columnas comparan la distribución en la muestra con la de Casen 2024 ponderada. No tienen que coincidir exactamente: la imputación respeta la relación entre cada dato y las características de la persona o del hogar, y la población del censo no es idéntica a la que Casen expande (Casen se calibra a proyecciones de población y solo cubre viviendas particulares).",
        "",
        tabla_md(["Dato", "Categoría", "Muestra %", "Casen %"], filas_b),
        "",
        tabla_md(["Promedio o mediana", "Muestra", "Casen"], [(n, dec(a, 2) if a < 1000 else miles(a), dec(b, 2) if b < 1000 else miles(b)) for n, a, b in medias]),
        "",
        "### Coherencia entre datos imputados",
        "",
        "Porcentaje de personas en Isapre según decil de ingreso del hogar. Ambos datos vienen de donantes distintos, así que esta tabla muestra si el encadenamiento conservó la relación:",
        "",
        tabla_md(["Decil", "Muestra %", "Casen %"], [(int(d), dec(isapre_por_decil.get(d, 0)), dec(isapre_casen.get(d, 0))) for d in range(1, 11)]),
        "",
        f"Hogares cuyos integrantes tienen sistemas de salud distintos: {dec(mixtos)} % en la muestra y {dec(mixtos_casen)} % en Casen.",
        "",
        "## C. Calidad del emparejamiento",
        "",
        f"El modelo que predice el ingreso per cápita del hogar explica el {dec(info['r2'] * 100, 0)} % de la varianza del logaritmo del ingreso en Casen (R² ponderado).",
        "",
        "Hogares según la clase dentro de la cual se buscó al donante (`nivel_match_hogar`):",
        "",
        tabla_md(["Nivel", "Clase", "Hogares", "%"], [
            (i + 1, c, miles(n), dec(n / len(hog) * 100)) for i, (c, n) in enumerate(zip(
                ["región, área, tamaño, origen de la jefatura", "macrozona, área, tamaño, origen de la jefatura", "área, tamaño, jefatura inmigrante", "tamaño"], niveles_h))]),
        "",
        "Personas según el nivel de coincidencia con su donante (`nivel_match_persona`). Del 1 al 5 coinciden sexo, edad quinquenal, educación, actividad y discapacidad; del 6 en adelante la coincidencia es más gruesa:",
        "",
        tabla_md(["Nivel", "Llaves", "Personas", "%"], [
            (i + 1, c, miles(n), dec(n / niveles_p.sum() * 100)) for i, (c, n) in enumerate(zip(
                ["+ decil, región, área, ocupación, parentesco, inmigrante", "+ decil, región, ocupación", "+ decil, macrozona", "+ decil", "+ quintil",
                 "sexo, edad decenal, educación en 3 tramos, actividad, discapacidad, decil", "sexo, edad decenal, educación en 3 tramos, actividad, quintil",
                 "sexo, edad decenal, actividad", "sexo, edad decenal, actividad (sin sistema de la jefatura)",
                 "sexo, grupo amplio de edad", "cualquiera"], niveles_p))]),
        "",
    ]
    (contexto / "validacion.md").write_text("\n".join(val) + "\n", encoding="utf-8")

    # README con el diccionario de columnas nuevas
    def cobertura(df, col, universo=None):
        base = df if universo is None else df[universo]
        return f"{dec(base[col].notna().mean() * 100, 0)} %"

    def cats(col):
        e = etiquetas[etiquetas["columna"] == col]
        return "; ".join(f"{r.valor} {re.sub(r'^-?\d+\.\s*', '', r.etiqueta)}" for r in e.itertuples())

    fam = [
        ("`edad`", "Censo; imputada donde `edad_imputada = 1`", f"Edad en años, tope 85. En {miles(per['edad_imputada'].sum())} personas de comunas pequeñas se sorteó dentro de su tramo quinquenal."),
        ("`hijos_total`", "Censo o Casen, según `hijos_origen`", f"Hijos nacidos vivos. Observado para mujeres de 15+ ({miles((per['hijos_origen'] == 'censo').sum())} casos); imputado para hombres y para mujeres sin respuesta ({miles((per['hijos_origen'] == 'casen').sum())})."),
        ("`hijos_en_hogar`", "Derivado del hogar censal", "Hijos que viven en el hogar. Solo para la jefatura y su pareja."),
        ("`hermanos_en_hogar`", "Derivado del hogar censal", "Hermanos que viven en el hogar. Solo para hijos de la jefatura, la jefatura y sus hermanos."),
        ("`esc_padre`, `esc_madre`", "Derivado del hogar censal", f"Años de escolaridad del padre y la madre, solo si viven en el mismo hogar ({cobertura(per, 'esc_madre')} de las personas tiene dato de la madre)."),
        ("`cine11_padre`, `cine11_madre`", "Derivado del hogar censal", "Nivel educativo del padre y la madre (códigos de `cine11`)."),
        ("`vive_con_padre`, `vive_con_madre`", "Derivado del hogar censal", "1 si el padre o la madre vive en el hogar. En ese caso su tramo socioeconómico es el decil del hogar."),
    ]
    pers = [
        ("`decil_ingreso`, `quintil_ingreso`", "Decil y quintil de ingreso autónomo per cápita del hogar (copiado de `hogares`)."),
        ("`prevision_salud`", f"Sistema de salud: {cats('prevision_salud')}."),
        ("`fonasa_grupo`", f"Grupo de Fonasa: {cats('fonasa_grupo')}."),
        ("`categoria_ocupacional`", f"Solo ocupados: {cats('categoria_ocupacional')}."),
        ("`tiene_contrato`", "Solo ocupados asalariados: 1 sí, 0 no."),
        ("`cotiza_pension`", "15 años o más: cotizó el mes pasado en un sistema de pensiones (1 sí, 0 no)."),
        ("`sindicato`", "Solo ocupados: pertenece a un sindicato (1 sí, 2 no)."),
        ("`participa_organizacion`", f"Organización en que participó en los últimos 12 meses: {cats('participa_organizacion')}."),
        ("`dependencia_grado`", "15 años o más: 0 no dependiente, 1 severa, 2 moderada, 3 leve."),
        ("`es_cuidador`", "1 si cuida a un integrante del hogar con dependencia."),
        ("`tiempo_traslado_min`", "Minutos de viaje al trabajo, para ocupados que se trasladan. Se emparejó por el medio de transporte declarado en el censo (`p45_medio_transporte`)."),
        ("`genero`", f"18 años o más: {cats('genero')}."),
        ("`nivel_match_persona`", "Qué tan fino fue el emparejamiento (1 el mejor, 11 el peor). Ver `validacion.md`."),
        ("`casen_folio_donante`, `casen_id_persona_donante`", "Identifican a la persona de Casen de la que se copiaron los datos."),
    ]
    hogs = [
        ("`decil_ingreso`, `quintil_ingreso`", "Decil y quintil nacional de ingreso autónomo per cápita. Es el tramo socioeconómico."),
        ("`ingreso_autonomo_pc`, `ingreso_total_pc`", "Ingreso mensual per cápita del hogar, en pesos de noviembre de 2024. El total por hogar es este valor por `n_personas`."),
        ("`pobreza_ingresos`", f"{cats('pobreza_ingresos')}."),
        ("`tiene_vehiculo`, `n_vehiculos`", "El hogar tiene vehículo de uso particular o laboral (1 sí, 2 no) y cuántos."),
        ("`red_*` (9 columnas)", f"El hogar conoce a alguien que pueda ayudar con: cuidado en enfermedad, cuidado de dependientes, vehículo, dinero, trámites, tecnología, reparaciones, conseguir trabajo, consejo. {cats('red_dinero')}."),
        ("`inseg_alim_*` (8 columnas) e `inseg_alim_n`", "Experiencias de inseguridad alimentaria en los últimos 12 meses (1 sí, 2 no) y cuántas de las ocho ocurrieron."),
        ("`discrim_*` (21 columnas)", "Alguien del hogar fue discriminado en los últimos 12 meses por ese motivo (1 sí, 0 no). `discrim_ninguna = 1` si no hubo."),
        ("`nivel_match_hogar`", "Clase en la que se encontró al hogar donante (1 la más específica)."),
        ("`casen_folio_donante`", "Hogar de Casen del que se copiaron los datos."),
    ]
    readme = [
        "# Muestra del 1 % de la población de Chile",
        "",
        f"`data/muestra/personas.parquet` tiene {miles(len(per))} personas y `data/muestra/hogares.parquet` tiene {miles(len(hog))} hogares. "
        "Son registros reales y anonimizados del Censo 2024, sorteados para representar al país, a los que se agregaron datos imputados desde la Encuesta Casen 2024.",
        "",
        "**Cada fila representa a 100 personas.** No hay ponderadores: un porcentaje calculado en la muestra estima el del país.",
        "",
        "**Los datos imputados no son de esa persona.** Son un valor plausible, sorteado entre personas u hogares de Casen parecidos. Sirven para estudiar distribuciones y relaciones, no para afirmar nada de un registro en particular. `validacion.md` muestra cuánto se parecen a la fuente.",
        "",
        "## Cómo se construyó",
        "",
        f"1. **Sorteo.** Se ordenaron los hogares del censo por región, comuna, área y tamaño, y se tomó 1 de cada {PASO}. Así cada comuna y cada tamaño de hogar pesan lo que deben. "
        f"Los hogares entran completos, con todos sus integrantes. Aparte se tomó 1 de cada {PASO} personas en viviendas colectivas y en situación de calle ({miles((~en_hogar).sum())} personas).",
        "2. **Edad.** En las 51 comunas donde el censo solo publica el tramo quinquenal, la edad exacta se sorteó según la distribución de su región, sexo y tramo.",
        "3. **Familia.** Hijos, hermanos y educación de los padres se dedujeron del parentesco dentro del hogar. Solo existen para quienes viven juntos.",
        f"4. **Hogares.** Con Casen se ajustó un modelo del ingreso per cápita según región, área, tamaño, características de la jefatura, ocupados, educación, tenencia, tipo de vivienda, hacinamiento e internet. "
        f"Dentro de cada combinación de región, área y tamaño, los hogares de la muestra y los de Casen se ordenan por su ingreso predicho, y cada hogar de la muestra recibe un donante de Casen que ocupa su misma posición relativa (con un margen aleatorio de {VECINOS} vecinos). "
        "Se empareja por posición y no por valor porque el censo registra algo menos de empleo y educación que Casen; así la distribución de ingresos de cada clase queda igual a la de Casen. De ese donante se copian ingresos, vehículos, redes de apoyo, inseguridad alimentaria y discriminación.",
        "5. **Personas.** A cada persona se le sorteó un donante de Casen del mismo sexo, edad, educación, actividad y discapacidad, y en lo posible del mismo decil, región, ocupación y parentesco. "
        "El decil es el que se imputó a su hogar en el paso anterior, y los integrantes de un hogar se emparejan además por el sistema de salud de su jefatura. De ese donante se copian previsión, datos del trabajo, participación y cuidados.",
        "6. **Sorteos aparte.** El tiempo de traslado, el género y los hijos de quienes el censo no pregunta tienen cada uno su propio emparejamiento, con las llaves que más les importan.",
        "",
        f"La semilla del sorteo está fija (`SEMILLA = {SEMILLA}`), así que volver a ejecutar el script produce la misma muestra.",
        "",
        "## Columnas",
        "",
        "Las columnas del censo conservan su nombre y sus códigos; están descritas en `contexto/censo2024/diccionario.md`. "
        "`hogares` trae además las columnas de la vivienda. Las etiquetas de las columnas imputadas están en `etiquetas_casen.csv`.",
        "",
        "Identificadores: `id_persona_muestra`, `id_hogar_muestra` (une ambas tablas; es nulo para personas fuera de hogares) y las llaves originales del censo.",
        "",
        "**Tabla única.** `data/muestra/muestra.parquet` y `data/muestra/muestra.csv` tienen todo junto: una fila por persona, con las columnas de su hogar y su vivienda repetidas en cada integrante. "
        "Para contar hogares o viviendas en esa tabla hay que quedarse con una fila por `id_hogar_muestra` (por ejemplo `parentesco = 1`), o usar `hogares.parquet`. "
        "Las personas fuera de hogares tienen vacías las columnas del hogar. `casen_folio_donante_hogar` es el donante del hogar y `casen_folio_donante` el de la persona.",
        "",
        "### Edad y familia (en `personas`)",
        "",
        tabla_md(["Columna", "Origen", "Contenido"], fam),
        "",
        "### Imputadas desde Casen por persona (en `personas`)",
        "",
        tabla_md(["Columna", "Contenido"], pers),
        "",
        "### Imputadas desde Casen por hogar (en `hogares`)",
        "",
        tabla_md(["Columna", "Contenido"], hogs),
        "",
        "## Límites",
        "",
        f"- **Personas fuera de hogares.** Las {miles((~en_hogar).sum())} personas en viviendas colectivas o en situación de calle no tienen datos de Casen, porque esa encuesta solo cubre viviendas particulares.",
        "- **No respuesta del censo.** Los `-99` y `-66` del censo se conservan tal cual, salvo la edad.",
        "- **Comunas.** Casen no es representativa por comuna. Los datos imputados son fiables por región y por grupos sociales, no para comparar comunas entre sí.",
        "- **Relaciones no medidas.** Una relación entre dos datos imputados por separado (por ejemplo, tiempo de traslado y participación en organizaciones) solo refleja lo que ambos comparten con la edad, la educación, el ingreso y las demás llaves.",
        "- **Familia fuera del hogar.** No hay hermanos ni educación de los padres para quienes no viven con ellos. Casen 2024 tampoco lo pregunta.",
        "- **Discriminación.** Los motivos se copian del hogar donante, que coincide en si la jefatura es inmigrante o indígena, pero no en todo lo demás.",
        "- **Fechas.** El censo se levantó entre marzo y julio de 2024 y Casen entre noviembre de 2024 y febrero de 2025.",
        "- **No incluye** tendencia política ni valores, que ninguna de las dos fuentes mide.",
        "",
        "## Uso",
        "",
        "```sh",
        'uv run python -I scripts/consulta.py "select decil_ingreso, round(100 * avg((prevision_salud = 2)::int), 1) as pct_isapre from muestra_personas group by 1 order by 1"',
        "```",
        "",
        "Las vistas `muestra` (tabla única), `muestra_personas` y `muestra_hogares` están disponibles en `scripts/consulta.py`. Para reconstruir:",
        "",
        "```sh",
        "uv run python -I scripts/descargar_casen.py data/casen2024",
        "uv run python -I scripts/construir_muestra.py data/censo2024 data/casen2024 data/muestra contexto/muestra",
        "```",
        "",
        "Fuentes: INE, Censo de Población y Vivienda 2024; Ministerio de Desarrollo Social y Familia, Encuesta Casen 2024.",
        "",
    ]
    (contexto / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    if fallas:
        sys.exit(f"\n{len(fallas)} verificaciones fallaron: {fallas}")


if __name__ == "__main__":
    main()
