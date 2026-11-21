#!/usr/bin/env python3
"""Imputa a los adultos de la muestra del 1 % las actitudes políticas de la Encuesta CEP N° 96.

Uso:
    uv run python -I scripts/imputar_cep.py data/muestra data/cep96 contexto/muestra

A cada persona de 18 años o más de data/muestra/personas.parquet le sortea un donante de
la CEP parecido (sexo, edad, educación, zona del país, nivel socioeconómico, actividad y
religión) y copia de él sus opiniones: posición política, partido, evaluación del gobierno,
confianza en instituciones, problemas que le importan, visión de la economía, del Estado,
de la democracia, de la inmigración, de la seguridad y de la familia. Todo sale del mismo
donante, así que las opiniones de una persona son coherentes entre sí.

Escribe data/muestra/actitudes.parquet (una fila por adulto, con id_persona_muestra), y
en la carpeta de contexto actitudes.md y etiquetas_cep.csv. No modifica la muestra. El
resultado es reproducible: depende solo de los datos y de SEMILLA.
"""

import sys
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from construir_muestra import MACROZONA, emparejar  # noqa: E402

SEMILLA = 2096

# Variable de la CEP -> columna de actitudes.parquet.
DE_LA_CEP = {
    "iden_pol_2": "posicion_politica",
    "iden_pol_3": "partido",
    "eval_gob_1": "aprueba_gobierno",
    "confianza_6_i": "confianza_gobierno",
    "confianza_6_k": "confianza_congreso",
    "confianza_6_o": "confianza_municipalidades",
    "pobreza_63": "responsabilidad_sustento",
    "interes_pol_1_b": "interes_politica",
    "elec_pres_155": "voto_segunda_vuelta_2025",
    # Política y país
    "eval_gob_63": "aprueba_gobierno_anterior",
    "elec_part_10": "votaria_voluntario",
    "interes_pol_27": "fuente_noticias",
    "percepcion_1_a": "problema_1",
    "percepcion_1_b": "problema_2",
    "percepcion_1_c": "problema_3",
    "percepcion_4": "rumbo_pais",
    "percepcion_38": "situacion_politica",
    "democracia_21": "apoyo_democracia",
    "democracia_20": "funciona_democracia",
    # Economía
    "percepcion_2": "economia_pais",
    "percepcion_3": "economia_pais_futuro",
    "percepcion_5": "economia_personal",
    "percepcion_6": "economia_personal_futuro",
    "bienestar_21": "ingresos_alcanzan",
    "bienestar_13_a": "preocupa_deudas",
    "bienestar_13_c": "preocupa_enfermedad",
    "bienestar_13_h": "preocupa_pension",
    "educacion_104_a": "clase_subjetiva",
    # Estado
    "democracia_33_a": "menos_estado_economia",
    "democracia_33_d": "estado_burocracia",
    "rol_gobierno_31": "reducir_gasto_publico",
    "rol_gobierno_28": "empleados_publicos",
    # Seguridad, orden e inmigración
    "democracia_38": "libertades_o_seguridad",
    "seguridad_37_a": "causa_delincuencia",
    "ciudadania_29_a": "justifica_marchas",
    "ciudadania_30_b": "justifica_fuerza_carabineros",
    "iden_nacional_16": "apertura_inmigracion",
    "iden_nacional_8_a": "inmigrantes_criminalidad",
    "iden_nacional_8_l": "inmigrantes_aporte",
    # Familia
    "mtf_84": "hijos_ideal",
    "mtf_46_d": "hijos_carga_financiera",
    "mtf_46_e": "hijos_restringen_carrera",
    # Confianza en otras instituciones
    "confianza_6_c": "confianza_fuerzas_armadas",
    "confianza_6_h": "confianza_carabineros",
    "confianza_6_d": "confianza_tribunales",
    "confianza_6_j": "confianza_partidos",
    "confianza_6_s": "confianza_empresas",
    "confianza_6_g": "confianza_sindicatos",
    "confianza_6_ab": "confianza_sistema_salud",
    "confianza_6_ac": "confianza_sistema_pensiones",
    "confianza_6_f": "confianza_television",
    "confianza_6_x": "confianza_redes_sociales",
    "confianza_6_a": "confianza_iglesia_catolica",
    "confianza_6_m": "confianza_universidades",
}
QUE_ES = {
    "posicion_politica": "Escala de 1 (izquierda) a 10 (derecha).",
    "partido": "Partido con el que más se identifica o simpatiza.",
    "aprueba_gobierno": "Aprueba o desaprueba cómo el presidente conduce el gobierno (José Antonio Kast, en abril-mayo de 2026).",
    "confianza_gobierno": "Confianza en el gobierno.",
    "confianza_congreso": "Confianza en el Congreso.",
    "confianza_municipalidades": "Confianza en las municipalidades.",
    "responsabilidad_sustento": "De 1 (el sustento económico de las personas es responsabilidad del Estado) a 10 (de las personas mismas).",
    "interes_politica": "Cuán interesado está en la política.",
    "voto_segunda_vuelta_2025": "Voto en la segunda vuelta presidencial de diciembre de 2025. Nulo para quien dijo no haber votado.",
}
NIVELES = [
    ["sexo", "edad7", "educ4", "macro", "nse3", "activ", "rel4"],
    ["sexo", "edad7", "educ4", "macro", "nse3", "rel4"],
    ["sexo", "edad7", "educ4", "nse3", "rel4"],
    ["sexo", "edad7", "educ4", "rel4"],
    ["sexo", "edad7", "educ4"],
    ["sexo", "edad3", "educ4"],
    ["sexo", "edad3"],
    [],
]
NOMBRES = {
    "sexo": {1: "Hombre", 2: "Mujer"},
    "edad3": {18: "18 a 34", 35: "35 a 54", 55: "55 o más"},
    "educ4": {1: "Menos que media completa", 2: "Media completa", 3: "Técnica completa", 4: "Universitaria completa"},
    "nse3": {1: "Bajo", 2: "Medio", 3: "Alto"},
    "rel4": {1: "Católica", 2: "Evangélica", 3: "Ninguna", 4: "Otra"},
}


def recodificar(serie, mapa, resto):
    return serie.map(mapa).fillna(resto).astype("int64")


def tramos_edad(df):
    df["edad7"] = np.select([df["edad"] < 25, df["edad"] < 35, df["edad"] < 45, df["edad"] < 55, df["edad"] < 65, df["edad"] < 75], [18, 25, 35, 45, 55, 65], 75)
    df["edad3"] = np.select([df["edad"] < 35, df["edad"] < 55], [18, 35], 55)
    df["macro"] = df["region"].map(MACROZONA).astype("int64")
    return df


def estandarizar_cep(c):
    d = pd.DataFrame({"sexo": c["sexo"].astype("int64"), "edad": c["edad"].astype("int64"), "region": c["region_3"].astype("int64")})
    # Nivel completo: quien no terminó la educación superior queda en media completa.
    d["educ4"] = recodificar(c["esc_nivel_1_c"], {0: 1, 1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 7: 2, 6: 3, 8: 4, 9: 4, 10: 4}, 9)
    d["nse3"] = recodificar(c["gse"], {5: 1, 4: 1, 3: 2, 2: 3, 1: 3}, 9)
    d["activ"] = recodificar(c["info_enc_35"], {1: 1, 2: 2, 3: 3}, 9)
    d["rel4"] = recodificar(c["religion_82"], {1: 1, 2: 2, 9: 3, 10: 3, 11: 3, 3: 4, 5: 4, 6: 4, 8: 4}, 9)
    d["pond"] = c["pond"].astype("float64")
    return tramos_edad(d)


def estandarizar_muestra(p, cortes):
    d = pd.DataFrame({"sexo": p["sexo"].astype("int64"), "edad": p["edad"].astype("int64"), "region": p["region"].astype("int64")})
    d["educ4"] = recodificar(p["cine11"], {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 12: 1, 6: 2, 7: 2, 8: 3, 9: 4, 10: 4, 11: 4}, 9)
    decil = p["decil_ingreso"].astype("float64")
    d["nse3"] = np.select([decil.isna(), decil <= cortes[0], decil <= cortes[1]], [9, 1, 2], 3)
    d["activ"] = recodificar(p["sit_fuerza_trabajo"], {1: 1, 2: 2, 3: 3}, 9)
    d["rel4"] = recodificar(p["p31_religion"], {1: 1, 2: 2, 12: 3, 5: 4, 10: 4, 999: 4}, 9)
    return tramos_edad(d)


def cortes_nse(cep, decil):
    """Deciles que dejan bajo y medio la misma proporción de personas que el GSE de la CEP (D y E; C3)."""
    return cortes_desde_conteos(cep, decil.dropna().value_counts())


def cortes_desde_conteos(cep, conteos):
    """Lo mismo, a partir de cuántos adultos hay en cada decil (una serie indexada por decil)."""
    peso = cep.groupby("nse3")["pond"].sum() / cep["pond"].sum()
    acumulado = (conteos / conteos.sum()).sort_index().cumsum()
    bajo = (acumulado - peso[1]).abs().idxmin()
    medio = (acumulado[acumulado.index > bajo] - (peso[1] + peso[2])).abs().idxmin()
    return int(bajo), int(medio)


def leer_preguntas(ruta):
    """Texto de la pregunta de cada variable de la CEP, para describir las columnas."""
    filas = list(openpyxl.load_workbook(ruta, read_only=True).active.iter_rows(values_only=True))[1:]
    return {var: " ".join(str(pregunta).split()) for var, pregunta, _, _ in filas if var in DE_LA_CEP}


def leer_etiquetas(ruta):
    filas = list(openpyxl.load_workbook(ruta, read_only=True).active.iter_rows(values_only=True))[1:]
    datos = [
        {"columna": DE_LA_CEP[var], "variable_cep": var, "valor": int(valor), "etiqueta": str(etiqueta).strip()}
        for var, _, valor, etiqueta in filas
        if var in DE_LA_CEP and valor is not None and etiqueta is not None
    ]
    return pd.DataFrame(datos)


def distribucion(valores, pesos):
    tabla = pd.Series(pesos, dtype="float64").groupby(pd.Series(valores).to_numpy()).sum()
    return 100 * tabla / tabla.sum()


def tabla_md(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    return "\n".join(lineas + ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas])


def miles(n):
    return f"{int(n):,}".replace(",", ".")


def numero(x, d=1):
    return "—" if pd.isna(x) else f"{x:.{d}f}".replace(".", ",")


def documentar(contexto, cep, don, rec, imput, etiquetas, nivel, cortes, preguntas):
    nombres = {(e.columna, e.valor): e.etiqueta for e in etiquetas.itertuples()}
    unos = np.ones(len(imput))
    partes = [
        "# Actitudes políticas imputadas desde la Encuesta CEP",
        "",
        f"`data/muestra/actitudes.parquet` tiene una fila por cada persona de 18 años o más de la muestra del 1 % ({miles(len(imput))} personas), "
        f"con actitudes copiadas de un entrevistado parecido de la Encuesta CEP N° 96 (abril-mayo de 2026, {miles(len(cep))} entrevistas presenciales).",
        "Se une a la muestra por `id_persona_muestra`.",
        "",
        "**No son las opiniones de esa persona.** Son las de un entrevistado de la CEP con su mismo perfil, sorteado al azar. "
        "Sirven para que la población sintética tenga la misma mezcla de posiciones que el país y la misma relación con la edad, "
        "la educación, la religión y el nivel socioeconómico. No sirven para afirmar nada de un registro en particular.",
        "",
        "## Cómo se construyó",
        "",
        "Cada persona recibe un donante de la CEP de su misma celda, sorteado con probabilidad proporcional a su ponderador (`pond`). "
        "Las celdas se definen por las llaves de la tabla; si una celda tiene menos de 3 donantes, se pasa al nivel siguiente.",
        "",
        tabla_md(["Nivel", "Llaves", "Personas", "%"],
                 [[i, ", ".join(llaves) or "(ninguna)", miles((nivel == i).sum()), numero(100 * (nivel == i).mean())]
                  for i, llaves in enumerate(NIVELES, 1)]),
        "",
        "- `edad7`: 18-24, 25-34, 35-44, 45-54, 55-64, 65-74 y 75 o más. `edad3`: 18-34, 35-54 y 55 o más.",
        "- `educ4`: nivel completo (menos que media, media, técnica, universitaria). En el censo sale de `cine11`.",
        "- `macro`: macrozona (norte, centro, Región Metropolitana, sur, austral), la misma de la imputación de Casen.",
        f"- `nse3`: en la CEP, el grupo socioeconómico (D y E; C3; C2 y ABC1). En la muestra, el decil de ingreso cortado para dejar la misma proporción de personas en cada tramo: deciles 1 a {cortes[0]}, {cortes[0] + 1} a {cortes[1]} y {cortes[1] + 1} a 10. Son medidas distintas del nivel socioeconómico; se empareja por posición relativa.",
        "- `activ`: trabaja, busca trabajo o está fuera de la fuerza de trabajo.",
        "- `rel4`: católica, evangélica, ninguna u otra. En el censo sale de `p31_religion`, que viene suprimida en algunos registros.",
        "",
        "Todas las columnas de una persona vienen del mismo donante. La semilla está fija (`SEMILLA`).",
        "",
        "## Columnas",
        "",
        "Los códigos son los de la CEP: `-8` es no sabe y `-9` es no contesta. Las etiquetas están en `etiquetas_cep.csv`.",
        "",
        tabla_md(["Columna", "Variable CEP", "Contenido"], [[f"`{col}`", f"`{var}`", QUE_ES.get(col) or preguntas.get(var, "")] for var, col in DE_LA_CEP.items()]
                 + [["`nivel_match_cep`", "", "Nivel en que se encontró al donante (1 el más específico)."],
                    ["`cep_id_donante`", "`id_bu`", "Entrevistado de la CEP del que se copiaron los datos."]]),
        "",
        "## Límites",
        "",
        "- **Solo se conserva lo que explican las llaves.** La relación entre una actitud y cualquier otro dato de la muestra (comuna, previsión, tipo de vivienda, hijos) existe solo a través del sexo, la edad, la educación, la zona, el nivel socioeconómico, la actividad y la religión.",
        "- **Regiones.** La CEP tiene 1.466 casos: es representativa del país, no de cada región. La región entra como macrozona.",
        "- **Fechas.** El censo es de marzo a julio de 2024 y la CEP de abril y mayo de 2026. La evaluación del gobierno es la de ese momento.",
        "- **Personas fuera de hogares** (viviendas colectivas y situación de calle): no tienen decil, así que se emparejan sin nivel socioeconómico. La CEP no las cubre.",
        "- **Coyuntura.** Varias opiniones son del momento de la encuesta (situación económica, rumbo del país, problemas prioritarios, evaluación del gobierno): describen abril y mayo de 2026.",
        "- **No incluye** valores de Schwartz ni personalidad: la CEP no los mide. Lo más cercano son `responsabilidad_sustento`, `menos_estado_economia` y `libertades_o_seguridad`.",
        "",
        "## Validación",
        "",
        "Porcentaje de cada respuesta en la CEP (ponderada) y en la muestra con los datos imputados. Deben parecerse; la diferencia que queda viene de que la muestra tiene otra composición por edad, educación y zona que la CEP ponderada.",
        "",
    ]
    for var, col in DE_LA_CEP.items():
        real = distribucion(cep[var].fillna(-1), cep["pond"])
        imputado = distribucion(imput[col].fillna(-1), unos)
        filas = []
        for valor in sorted(set(real.index) | set(imputado.index)):
            nombre = "No aplica" if valor == -1 else nombres.get((col, int(valor)), str(int(valor)))
            filas.append([nombre, numero(real.get(valor, 0)), numero(imputado.get(valor, 0))])
        partes += [f"### `{col}`", "", tabla_md(["Respuesta", "CEP %", "Muestra %"], filas), ""]

    partes += [
        "### Por grupo",
        "",
        "Posición política media (de 1 a 10, entre quienes se ubican) y porcentaje que aprueba al gobierno, en la CEP y en la muestra.",
        "",
    ]
    filas = []
    for llave, etiquetas_llave in NOMBRES.items():
        for valor, nombre in etiquetas_llave.items():
            d, r = (don[llave] == valor).to_numpy(), (rec[llave] == valor).to_numpy()
            pos_cep, pos_imp = cep.loc[d, "iden_pol_2"], imput.loc[r, "posicion_politica"]
            w = cep.loc[d, "pond"]
            ubica_cep, ubica_imp = (pos_cep > 0).to_numpy(), (pos_imp > 0).to_numpy()
            filas.append([
                f"{llave}: {nombre}",
                miles(d.sum()),
                numero(np.average(pos_cep[ubica_cep], weights=w[ubica_cep]), 2),
                numero(pos_imp[ubica_imp].mean(), 2),
                numero(100 * np.average(cep.loc[d, "eval_gob_1"] == 1, weights=w)),
                numero(100 * (imput.loc[r, "aprueba_gobierno"] == 1).mean()),
            ])
    partes += [tabla_md(["Grupo", "Casos CEP", "Posición CEP", "Posición muestra", "Aprueba CEP %", "Aprueba muestra %"], filas), ""]
    partes += ["Fuentes: Centro de Estudios Públicos, Encuesta CEP N° 96, abril-mayo 2026; INE, Censo de Población y Vivienda 2024.", ""]
    (contexto / "actitudes.md").write_text("\n".join(partes), encoding="utf-8")


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    muestra, cep_dir, contexto = (Path(a) for a in sys.argv[1:])
    rng = np.random.default_rng(SEMILLA)

    cep = pd.read_parquet(cep_dir / "cep96.parquet")
    per = pd.read_parquet(muestra / "personas.parquet")
    per = per[per["edad"] >= 18].reset_index(drop=True)
    don = estandarizar_cep(cep)
    cortes = cortes_nse(don, per["decil_ingreso"].astype("float64"))
    rec = estandarizar_muestra(per, cortes)
    print(f"{miles(len(per))} adultos de la muestra y {miles(len(cep))} entrevistas de la CEP; nse3 corta en los deciles {cortes[0]} y {cortes[1]}")

    elegido, nivel = emparejar(rec, don, NIVELES, "pond", rng)
    imput = pd.DataFrame({"id_persona_muestra": per["id_persona_muestra"].to_numpy()})
    for var, col in DE_LA_CEP.items():
        imput[col] = cep[var].to_numpy()[elegido]
        imput[col] = imput[col].astype("Int64")
    imput["nivel_match_cep"] = nivel
    imput["cep_id_donante"] = cep["id_bu"].to_numpy()[elegido]
    imput.to_parquet(muestra / "actitudes.parquet", index=False)

    etiquetas = leer_etiquetas(cep_dir / "docs" / "diccionario_base_96.xlsx")
    etiquetas.to_csv(contexto / "etiquetas_cep.csv", index=False)
    documentar(contexto, cep, don, rec, imput, etiquetas, nivel, cortes, leer_preguntas(cep_dir / "docs" / "diccionario_base_96.xlsx"))
    for i, llaves in enumerate(NIVELES, 1):
        print(f"  nivel {i}: {100 * (nivel == i).mean():5.1f} %  {', '.join(llaves) or '(ninguna)'}")
    print(f"Listo: {muestra / 'actitudes.parquet'} y {contexto / 'actitudes.md'}")


if __name__ == "__main__":
    main()
