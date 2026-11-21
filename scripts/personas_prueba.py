#!/usr/bin/env python3
"""Genera personas de prueba para comparar modelos locales.

Uso:
    uv run python -I scripts/personas_prueba.py data/censo2024 data/pruebas/personas.jsonl [N] [SEMILLA]

Toma N adultos (18 años o más, en viviendas particulares) al azar de los
microdatos del Censo 2024 y traduce los códigos con el diccionario del INE.
Por defecto N = 200 y SEMILLA = 1; con la misma semilla sale la misma muestra.

Cada línea del archivo de salida tiene dos bloques:
  "censo"             atributos reales de una persona censada.
  "relleno_aleatorio" atributos que el censo no trae (tendencia política,
                      tramo socioeconómico, previsión, padres, Schwartz, OCEAN...),
                      sorteados de forma uniforme e independiente entre sí.

El relleno NO representa a la población: sirve para medir la velocidad del
modelo y si reacciona al perfil, no para sacar conclusiones sustantivas.
"""

import json
import random
import re
import sys
from pathlib import Path

import duckdb
import openpyxl

TENDENCIAS = [
    "Izquierda",
    "Centroizquierda",
    "Centro",
    "Centroderecha",
    "Derecha",
    "No se identifica con ninguna",
]
QUINTILES = [
    "Quintil 1 (20 % de menores ingresos)",
    "Quintil 2",
    "Quintil 3",
    "Quintil 4",
    "Quintil 5 (20 % de mayores ingresos)",
]
PREVISIONES = [
    "Fonasa tramo A",
    "Fonasa tramo B",
    "Fonasa tramo C",
    "Fonasa tramo D",
    "Isapre",
    "Fuerzas Armadas y de Orden",
    "Ninguna",
]
EDUCACION_PADRES = [
    "Sin estudios",
    "Básica incompleta",
    "Básica completa",
    "Media incompleta",
    "Media completa",
    "Técnica de nivel superior",
    "Universitaria",
    "Postgrado",
]
SCHWARTZ = [
    "autodirección",
    "estimulación",
    "hedonismo",
    "logro",
    "poder",
    "seguridad",
    "conformidad",
    "tradición",
    "benevolencia",
    "universalismo",
]
OCEAN = ["apertura a la experiencia", "responsabilidad", "extraversión", "amabilidad", "neuroticismo"]

CONSULTA = """
WITH muestra AS (
    SELECT id_vivienda, id_hogar, id_persona, region, comuna, area, sexo, edad,
           p23_est_civil, p27_nacionalidad, p27_nacionalidad_esp, p28_autoid_pueblo,
           p28_pueblo_pert, cine11, escolaridad, sit_fuerza_trabajo,
           p45_medio_transporte, p46a_tot_hijs_nac
    FROM read_parquet($personas)
    WHERE edad >= 18 AND tipo_operativo = 2
    ORDER BY hash(id_vivienda, id_hogar, id_persona, $semilla)
    LIMIT $n
)
SELECT m.*, h.p12_tenencia_viv, h.tipologia_hogar, v.p2_tipo_vivienda
FROM muestra m
LEFT JOIN read_parquet($hogares) h USING (id_vivienda, id_hogar)
LEFT JOIN read_parquet($viviendas) v USING (id_vivienda)
ORDER BY m.id_vivienda, m.id_hogar, m.id_persona
"""


def limpiar(texto):
    return re.sub(r"\s+", " ", str(texto).replace("​", "").replace("\xa0", " ")).strip()


def cargar_diccionario(ruta):
    """Devuelve (etiquetas, territorios, paises) a partir del diccionario del INE."""
    libro = openpyxl.load_workbook(ruta, read_only=True)
    etiquetas = {}
    for hoja in ("tabla_personas", "tabla_hogares", "tabla_viviendas"):
        for fila in libro[hoja].iter_rows(min_row=2, values_only=True):
            variable, valor, etiqueta = fila[1], fila[3], fila[4]
            try:
                valor = int(valor)
            except (TypeError, ValueError):
                continue  # rangos ("0:85") y "NA"
            if valor >= 0 and etiqueta:
                etiquetas.setdefault(variable, {})[valor] = limpiar(etiqueta)
    territorios = {
        (limpiar(tipo), int(codigo)): limpiar(nombre)
        for codigo, tipo, nombre in libro["codigos_territoriales"].iter_rows(min_row=2, values_only=True)
        if codigo is not None
    }
    paises = {
        int(codigo): limpiar(nombre)
        for codigo, nombre in libro["cod_territoriales_especificos"].iter_rows(min_row=2, values_only=True)
        if codigo is not None
    }
    return etiquetas, territorios, paises


def del_censo(f, etiquetas, territorios, paises):
    """Atributos legibles de una fila del censo. Omite lo que no tiene dato válido."""

    def etiqueta(variable):
        return etiquetas.get(variable, {}).get(f[variable])

    datos = {
        "Edad": "85 años o más" if f["edad"] >= 85 else f"{f['edad']} años",
        "Sexo": etiqueta("sexo"),
        "Región": territorios.get(("Región", f["region"])),
        "Comuna": territorios.get(("Comuna", f["comuna"])),
        "Zona": {1: "Urbana", 2: "Rural"}.get(f["area"]),
    }
    pais = paises.get(f["p27_nacionalidad_esp"])
    datos["Nacionalidad"] = {
        1: "Chilena",
        2: f"Chilena y {pais}" if pais and pais != "Chile" else "Chilena y otra",
        3: pais or "Extranjera",
    }.get(f["p27_nacionalidad"])
    datos["Estado civil"] = etiqueta("p23_est_civil")
    if f["p28_autoid_pueblo"] == 1:
        datos["Pueblo indígena u originario"] = etiqueta("p28_pueblo_pert") or "Sí, sin especificar"
    elif f["p28_autoid_pueblo"] == 2:
        datos["Pueblo indígena u originario"] = "No pertenece"
    nivel = etiqueta("cine11")
    if nivel:
        nivel = re.sub(r"^\d+:\s*", "", nivel)
        if f["escolaridad"] is not None and f["escolaridad"] >= 0:
            nivel += f" ({f['escolaridad']} años de escolaridad)"
        datos["Nivel educacional"] = nivel
    datos["Situación laboral"] = etiqueta("sit_fuerza_trabajo")
    datos["Tipo de vivienda"] = etiqueta("p2_tipo_vivienda")
    datos["Tenencia de la vivienda"] = etiqueta("p12_tenencia_viv")
    datos["Tipo de hogar"] = etiqueta("tipologia_hogar")
    datos["Transporte principal"] = etiqueta("p45_medio_transporte")
    # El censo solo pregunta por hijos a las mujeres.
    if f["p46a_tot_hijs_nac"] is not None and f["p46a_tot_hijs_nac"] >= 0:
        datos["Hijos"] = str(f["p46a_tot_hijs_nac"])
    return {clave: valor for clave, valor in datos.items() if valor}


def relleno(censo, azar, transportes):
    """Atributos que el censo no trae, sorteados de forma uniforme."""
    datos = {}
    if "Transporte principal" not in censo:
        datos["Transporte principal"] = azar.choice(transportes)
    if "Hijos" not in censo:
        datos["Hijos"] = str(azar.randint(0, 4))
    datos["Hermanos"] = str(azar.randint(0, 5))
    datos["Tramo socioeconómico"] = azar.choice(QUINTILES)
    datos["Tendencia política"] = azar.choice(TENDENCIAS)
    datos["Previsión de salud"] = azar.choice(PREVISIONES)
    datos["Nivel educacional de los padres"] = azar.choice(EDUCACION_PADRES)
    datos["Tramo socioeconómico de los padres"] = azar.choice(QUINTILES)
    datos["Valores de Schwartz (1 = nada importante, 6 = muy importante)"] = ", ".join(
        f"{valor} {azar.randint(1, 6)}" for valor in SCHWARTZ
    )
    datos["Personalidad OCEAN (1 = muy bajo, 5 = muy alto)"] = ", ".join(
        f"{rasgo} {azar.randint(1, 5)}" for rasgo in OCEAN
    )
    return datos


def main():
    if not 3 <= len(sys.argv) <= 5:
        sys.exit(__doc__)
    raiz, salida = Path(sys.argv[1]), Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    semilla = int(sys.argv[4]) if len(sys.argv) > 4 else 1

    etiquetas, territorios, paises = cargar_diccionario(raiz / "docs" / "diccionario_variables_censo2024.xlsx")
    micro = raiz / "microdatos"
    resultado = duckdb.connect().execute(
        CONSULTA,
        {
            "personas": str(micro / "personas_censo2024.parquet"),
            "hogares": str(micro / "hogares_censo2024.parquet"),
            "viviendas": str(micro / "viviendas_censo2024.parquet"),
            "semilla": semilla,
            "n": n,
        },
    )
    columnas = [c[0] for c in resultado.description]
    transportes = list(etiquetas["p45_medio_transporte"].values())

    salida.parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", encoding="utf-8") as f:
        for i, fila in enumerate(resultado.fetchall(), start=1):
            censo = del_censo(dict(zip(columnas, fila)), etiquetas, territorios, paises)
            persona = {
                "id": f"p{i:05d}",
                "censo": censo,
                "relleno_aleatorio": relleno(censo, random.Random(f"{semilla}-{i}"), transportes),
            }
            f.write(json.dumps(persona, ensure_ascii=False) + "\n")
    print(f"{i} personas en {salida} (semilla {semilla})")


if __name__ == "__main__":
    main()
