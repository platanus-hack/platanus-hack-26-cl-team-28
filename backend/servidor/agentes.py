"""Los agentes: personas de la muestra del 1 % del Censo 2024 con su perfil, su comuna y su ubicación.

Cada agente es una persona real y anonimizada de la muestra (ver contexto/muestra/README.md),
con datos de Casen imputados. Aquí se cargan, se ubican en el centroide de su comuna y se
resumen en los campos que usa la interfaz para filtrar y dibujar.
"""

import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_AGENTES = RAIZ / "data" / "pruebas" / "sala_cuna" / "personas_2000.jsonl"
ARCHIVO_COMUNAS = RAIZ / "contexto" / "geo" / "comunas_centroides.csv"

# Mismo orden que REGIONES en frontend/src/dominio/catalogos.ts (de norte a sur).
REGIONES = [
    ("Arica y Parinacota", 15),
    ("Tarapacá", 1),
    ("Antofagasta", 2),
    ("Atacama", 3),
    ("Coquimbo", 4),
    ("Valparaíso", 5),
    ("Metropolitana de Santiago", 13),
    ("Libertador General Bernardo O'Higgins", 6),
    ("Maule", 7),
    ("Ñuble", 16),
    ("Biobío", 8),
    ("La Araucanía", 9),
    ("Los Ríos", 14),
    ("Los Lagos", 10),
    ("Aysén del General Carlos Ibáñez del Campo", 11),
    ("Magallanes y de la Antártica Chilena", 12),
]
INDICE_REGION = {nombre: i for i, (nombre, _) in enumerate(REGIONES)}
CODIGO_A_INDICE = {codigo: i for i, (_, codigo) in enumerate(REGIONES)}

GENEROS = {"Femenino": 0, "Masculino": 1, "No binario": 2}
EDUCACION = {"Básica o menos": 0, "Media": 1, "Superior": 3}


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").replace("'", "").strip()


@dataclass(frozen=True)
class Agente:
    indice: int
    id: str
    atributos: dict
    region: int
    comuna: str
    lon: float
    lat: float
    edad: int
    genero: int
    quintil: int
    educacion: int

    def perfil(self) -> str:
        """Perfil en una línea, tal como se le muestra al modelo."""
        return "; ".join(f"{clave}: {valor}" for clave, valor in self.atributos.items())

    def publico(self) -> dict:
        return {
            "i": self.indice,
            "id": self.id,
            "region": self.region,
            "comuna": self.comuna,
            "lon": self.lon,
            "lat": self.lat,
            "edad": self.edad,
            "genero": self.genero,
            "quintil": self.quintil,
            "educacion": self.educacion,
            "atributos": self.atributos,
        }


def cargar_comunas() -> dict[tuple[int, str], tuple[float, float]]:
    with open(ARCHIVO_COMUNAS, encoding="utf-8") as f:
        return {
            (int(fila["region"]), normalizar(fila["nombre"])): (float(fila["lon"]), float(fila["lat"]))
            for fila in csv.DictReader(f)
        }


def _numero(texto: str | None, defecto: int) -> int:
    hallado = re.search(r"\d+", texto or "")
    return int(hallado.group()) if hallado else defecto


def cargar_agentes(archivo: Path = ARCHIVO_AGENTES) -> list[Agente]:
    comunas = cargar_comunas()
    agentes = []
    with open(archivo, encoding="utf-8") as f:
        filas = [json.loads(linea) for linea in f if linea.strip()]
    for indice, fila in enumerate(filas):
        atributos, grupos = fila["atributos"], fila.get("grupos", {})
        region = INDICE_REGION[atributos["Región"]]
        codigo = REGIONES[region][1]
        comuna = atributos.get("Comuna", "")
        lon, lat = comunas.get((codigo, normalizar(comuna)), (None, None))
        if lon is None:
            # Sin centroide conocido: la capital regional que usa la interfaz se encarga.
            lon, lat = 0.0, 0.0
        genero_texto = atributos.get("Género") or ("Femenino" if atributos.get("Sexo") == "Mujer" else "Masculino")
        quintil = _numero(grupos.get("Tramo socioeconómico"), 3) - 1
        agentes.append(
            Agente(
                indice=indice,
                id=fila["id"],
                atributos=atributos,
                region=region,
                comuna=comuna,
                lon=lon,
                lat=lat,
                edad=_numero(atributos.get("Edad"), 40),
                genero=GENEROS.get(genero_texto, 3),
                quintil=max(0, min(4, quintil)),
                educacion=EDUCACION.get(grupos.get("Nivel educacional", ""), 1),
            )
        )
    return agentes
