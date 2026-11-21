"""Los agentes: personas de la muestra del 1 % del Censo 2024 con su perfil, su comuna y su ubicación.

Cada agente es una persona real y anonimizada de la muestra, de 14 años o más, con datos de
Casen y opiniones de la CEP imputados (ver contexto/muestra/README.md y actitudes.md). Su
perfil es el texto general por secciones que escribe scripts/personas_muestra.py. Aquí se
cargan, se ubican en el centroide de su comuna y se resumen en los campos que usa la
interfaz para filtrar y dibujar.
"""

import csv
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_AGENTES = RAIZ / "data" / "pruebas" / "poblacion" / "al_azar_2000.jsonl"
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
# Lo que la interfaz muestra de cada persona, en este orden: son los grupos del perfil.
A_LA_VISTA = [
    "Nivel educacional", "Situación laboral", "Tipo de colegio", "Tramo socioeconómico", "Previsión de salud",
    "Tipo de hogar", "Menores en el hogar", "Tenencia de la vivienda", "Religión", "Posición política", "Evaluación del gobierno",
]


def normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn").replace("'", "").strip()


@dataclass(frozen=True)
class Agente:
    indice: int
    id: str
    #: Resumen corto para la interfaz: edad, género, lugar y los grupos de `A_LA_VISTA`.
    atributos: dict
    #: El perfil completo que lee el modelo: {sección: texto}.
    perfil: dict
    region: int
    comuna: str
    lon: float
    lat: float
    edad: int
    genero: int
    quintil: int
    educacion: int
    #: Índice en POLITICA del frontend: 0 izquierda … 4 derecha, 5 sin identificación.
    politica: int

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
            "politica": self.politica,
            "atributos": self.atributos,
        }


def cargar_comunas() -> dict[tuple[int, str], tuple[float, float]]:
    with open(ARCHIVO_COMUNAS, encoding="utf-8") as f:
        return {
            (int(fila["region"]), normalizar(fila["nombre"])): (float(fila["lon"]), float(fila["lat"]))
            for fila in csv.DictReader(f)
        }


def cargar_agentes(archivo: Path = ARCHIVO_AGENTES) -> list[Agente]:
    comunas = cargar_comunas()
    agentes = []
    with open(archivo, encoding="utf-8") as f:
        filas = [json.loads(linea) for linea in f if linea.strip()]
    for indice, fila in enumerate(filas):
        datos, grupos = fila["datos"], fila.get("grupos", {})
        region = CODIGO_A_INDICE[datos["region"]]
        comuna = datos.get("comuna") or ""
        lon, lat = comunas.get((datos["region"], normalizar(comuna)), (None, None))
        if lon is None:
            # Sin centroide conocido: la capital regional que usa la interfaz se encarga.
            lon, lat = 0.0, 0.0
        genero = datos.get("genero") or ""
        atributos = {"Edad": f"{datos['edad']} años", "Género": genero, "Región": datos.get("nombre_region") or "", "Comuna": comuna, "Zona": datos.get("zona") or ""}
        atributos |= {clave: grupos[clave] for clave in A_LA_VISTA if grupos.get(clave)}
        agentes.append(
            Agente(
                indice=indice,
                id=fila["id"],
                atributos=atributos,
                perfil=fila["perfil"],
                region=region,
                comuna=comuna,
                lon=lon,
                lat=lat,
                edad=datos["edad"],
                genero=GENEROS.get(genero, 3),
                quintil=max(0, min(4, (datos.get("quintil") or 3) - 1)),
                educacion=EDUCACION.get(datos.get("educacion") or "", 1),
                # La escala de 1 a 10 de la CEP en cinco tramos; los menores de 18 y quienes no se ubican van aparte.
                politica=(datos["posicion_politica"] - 1) // 2 if datos.get("posicion_politica") else 5,
            )
        )
    return agentes
