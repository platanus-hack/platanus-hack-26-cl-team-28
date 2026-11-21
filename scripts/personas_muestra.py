#!/usr/bin/env python3
"""Saca personas de la muestra del 1 % y las deja listas para scripts/probar_modelo.py.

Uso:
    uv run python -I scripts/personas_muestra.py data/muestra/muestra.parquet data/pruebas/sala_cuna/personas.jsonl [N] [SEMILLA]

Toma N adultos (18 años o más) al azar de la muestra. Por defecto N = 200 y
SEMILLA = 1; con la misma semilla sale la misma selección.

Cada línea del archivo de salida tiene:
  "atributos"  lo que se le muestra al modelo, con las etiquetas del censo y de Casen.
  "grupos"     las mismas variables en pocas categorías, para comparar medias en el informe.

Solo usa datos que existen en la muestra. No inventa tendencia política, valores
de Schwartz ni personalidad OCEAN: ni el censo ni Casen los miden. Los hermanos y
los datos de los padres existen solo para quienes viven con ellos.
"""

import csv
import json
import re
import sys
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
CONTEXTO = RAIZ / "contexto"

COLUMNAS = """
    id_persona_muestra, edad, sexo, genero, region, comuna, area,
    p27_nacionalidad, p27_nacionalidad_esp, quintil_ingreso, p23_est_civil,
    p28_autoid_pueblo, p28_pueblo_pert, cine11, escolaridad, p2_tipo_vivienda,
    p45_medio_transporte, tiene_vehiculo, hijos_total, hermanos_en_hogar,
    cine11_padre, cine11_madre, vive_con_padre, vive_con_madre,
    prevision_salud, fonasa_grupo
"""


def leer_csv(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def cargar_etiquetas():
    censo = {}
    for fila in leer_csv(CONTEXTO / "censo2024" / "etiquetas.csv"):
        if re.fullmatch(r"-?\d+", fila["valor"]):  # hay filas de rangos, sin valor único
            censo.setdefault(fila["variable"], {})[int(fila["valor"])] = fila["etiqueta"].replace("\u200b", "").strip()
    casen = {}
    for fila in leer_csv(CONTEXTO / "muestra" / "etiquetas_casen.csv"):
        if re.fullmatch(r"-?\d+", fila["valor"]):
            casen.setdefault(fila["columna"], {})[int(fila["valor"])] = re.sub(r"^\d+\.\s*", "", fila["etiqueta"])
    territorios = {(f["nivel"], int(f["codigo"])): f["nombre"] for f in leer_csv(CONTEXTO / "censo2024" / "territorios.csv")}
    paises = {int(f["codigo"]): f["nombre"] for f in leer_csv(CONTEXTO / "censo2024" / "territorios_especificos.csv")}
    return censo, casen, territorios, paises


def valido(x):
    return x is not None and x >= 0


def nivel_educacional(codigo, censo):
    etiqueta = censo["cine11"].get(codigo) if valido(codigo) else None
    return re.sub(r"^\d+:\s*", "", etiqueta) if etiqueta else None


def describir(f, censo, casen, territorios, paises):
    """Devuelve (atributos para el prompt, grupos para el informe) de una fila de la muestra."""

    def etiqueta(variable):
        return censo.get(variable, {}).get(f[variable]) if valido(f[variable]) else None

    a, g = {}, {}

    a["Edad"] = "85 años o más" if f["edad"] >= 85 else f"{f['edad']} años"
    g["Edad"] = "18 a 29" if f["edad"] < 30 else "30 a 44" if f["edad"] < 45 else "45 a 59" if f["edad"] < 60 else "60 o más"

    if valido(f["genero"]):
        a["Género"] = casen["genero"][f["genero"]]
    else:
        a["Sexo"] = etiqueta("sexo")
    # Sin género declarado se agrupa por sexo, con las mismas dos etiquetas.
    g["Género"] = a.get("Género") or {"Hombre": "Masculino", "Mujer": "Femenino"}.get(a.get("Sexo"))

    pais = paises.get(f["p27_nacionalidad_esp"])
    a["Nacionalidad"] = {
        1: "Chilena",
        2: f"Chilena y {pais}" if pais and pais != "Chile" else "Chilena y otra",
        3: pais or "Extranjera",
    }.get(f["p27_nacionalidad"])
    g["Nacionalidad"] = {1: "Chilena", 2: "Doble nacionalidad", 3: "Extranjera"}.get(f["p27_nacionalidad"])

    a["Región"] = g["Región"] = territorios.get(("region", f["region"]))
    a["Comuna"] = territorios.get(("comuna", f["comuna"]))
    a["Zona"] = g["Zona"] = {1: "Urbana", 2: "Rural"}.get(f["area"])

    if valido(f["quintil_ingreso"]):
        a["Tramo socioeconómico"] = f"Quintil {f['quintil_ingreso']} de 5 según ingreso del hogar (1 es el más bajo)"
        g["Tramo socioeconómico"] = f"Quintil {f['quintil_ingreso']}"

    a["Estado civil"] = g["Estado civil"] = etiqueta("p23_est_civil")

    if f["p28_autoid_pueblo"] == 1:
        a["Pueblo indígena u originario"] = etiqueta("p28_pueblo_pert") or "Sí, sin especificar"
        g["Etnia"] = "Pueblo indígena u originario"
    elif f["p28_autoid_pueblo"] == 2:
        a["Pueblo indígena u originario"] = "No pertenece"
        g["Etnia"] = "No pertenece a un pueblo indígena"

    nivel = nivel_educacional(f["cine11"], censo)
    if nivel:
        if valido(f["escolaridad"]):
            nivel += f" ({f['escolaridad']} años de escolaridad)"
        a["Nivel educacional"] = nivel
        g["Nivel educacional"] = (
            "Superior" if 8 <= f["cine11"] <= 11 else "Media" if f["cine11"] in (6, 7) else "Básica o menos"
        )

    a["Tipo de vivienda"] = g["Tipo de vivienda"] = etiqueta("p2_tipo_vivienda")

    transporte = etiqueta("p45_medio_transporte")
    if transporte:
        tipo = {1: "Privado", 2: "Público", 5: "Privado"}.get(f["p45_medio_transporte"], "Otro")
        a["Transporte al trabajo"] = transporte if tipo == "Otro" else f"{tipo}: {transporte}"
        g["Tipo de transporte"] = tipo
    else:
        g["Tipo de transporte"] = "No se traslada a un trabajo"
    if f["tiene_vehiculo"] in (1, 2):
        a["Vehículo en el hogar"] = "Sí" if f["tiene_vehiculo"] == 1 else "No"

    if valido(f["hijos_total"]):
        a["Hijos"] = "No tiene" if f["hijos_total"] == 0 else str(f["hijos_total"])
        g["Hijos"] = "Sin hijos" if f["hijos_total"] == 0 else "Con hijos"
    if valido(f["hermanos_en_hogar"]):
        a["Hermanos que viven en su hogar"] = str(f["hermanos_en_hogar"])
    a["Nivel educacional del padre"] = nivel_educacional(f["cine11_padre"], censo)
    a["Nivel educacional de la madre"] = nivel_educacional(f["cine11_madre"], censo)
    if (f["vive_con_padre"] or f["vive_con_madre"]) and valido(f["quintil_ingreso"]):
        a["Tramo socioeconómico de los padres"] = f"Quintil {f['quintil_ingreso']} de 5 (viven en el mismo hogar)"
    g["Vive con sus padres"] = "Sí" if f["vive_con_padre"] or f["vive_con_madre"] else "No"

    if f["prevision_salud"] == 1:
        grupo = casen["fonasa_grupo"].get(f["fonasa_grupo"]) if valido(f["fonasa_grupo"]) else None
        a["Previsión de salud"] = f"Fonasa, {grupo[0].lower()}{grupo[1:]}" if grupo else "Fonasa"
        g["Previsión de salud"] = (
            "Fonasa A o B" if f["fonasa_grupo"] in (1, 2) else "Fonasa C o D" if f["fonasa_grupo"] in (3, 4) else "Fonasa sin grupo"
        )
    elif valido(f["prevision_salud"]):
        a["Previsión de salud"] = casen["prevision_salud"][f["prevision_salud"]]
        g["Previsión de salud"] = "Isapre" if f["prevision_salud"] == 2 else "Otra o ninguna"

    limpiar = lambda d: {clave: valor for clave, valor in d.items() if valor}
    return limpiar(a), limpiar(g)


def main():
    if not 3 <= len(sys.argv) <= 5:
        sys.exit(__doc__)
    muestra, salida = Path(sys.argv[1]), Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    semilla = int(sys.argv[4]) if len(sys.argv) > 4 else 1

    etiquetas = cargar_etiquetas()
    resultado = duckdb.connect().execute(
        f"""
        SELECT {COLUMNAS} FROM read_parquet($muestra)
        WHERE edad >= 18
        ORDER BY hash(id_persona_muestra, $semilla)
        LIMIT $n
        """,
        {"muestra": str(muestra), "semilla": semilla, "n": n},
    )
    columnas = [c[0] for c in resultado.description]
    filas = [dict(zip(columnas, fila)) for fila in resultado.fetchall()]

    salida.parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        for fila in filas:
            atributos, grupos = describir(fila, *etiquetas)
            persona = {"id": f"m{fila['id_persona_muestra']}", "atributos": atributos, "grupos": grupos}
            f.write(json.dumps(persona, ensure_ascii=False) + "\n")
    print(f"{len(filas)} personas en {salida} (semilla {semilla})")


if __name__ == "__main__":
    main()
