"""De dónde salen los agentes de cada consulta: se filtra la población y se sortea una muestra.

`TablaAgentes` lee `data/agentes/` (ver contexto/chile/agentes.md): 1,5 millones de personas
reales del censo, cada una en representación de unas 10. Con los filtros de la interfaz se
queda con quienes los cumplen y sortea hasta el máximo pedido, en proporción a `representa`.
El perfil de cada persona elegida se arma en el momento, con la misma función que usa el
banco de pruebas (`scripts/personas_muestra.py`).

`ArchivoFijo` es el respaldo: las 2.000 personas de `data/pruebas/poblacion/al_azar_2000.jsonl`.
Se usa si falta DuckDB o la tabla, y siempre con la corrida grabada, que solo tiene respuestas
de esas personas.
"""

import dataclasses
import hashlib
import importlib.util
import json
import threading
from dataclasses import dataclass
from pathlib import Path

from .agentes import ARCHIVO_AGENTES, REGIONES, Agente, agente_de, cargar_agentes, cargar_comunas

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_TABLA = RAIZ / "data" / "agentes"
# La muestra es siempre la misma para los mismos filtros: así la caché de respuestas sirve.
SEMILLA = 2024
EDAD_SIN_TOPE = 90
SIN_FILTRO = -1

# Los mismos tramos que usa la interfaz para filtrar (índices de frontend/src/dominio/catalogos.ts).
GENERO = "case when genero in (1, 3) then 1 when genero in (2, 4) then 0 when sexo = 1 then 1 else 0 end"
EDUCACION = "case when cine11 between 8 and 11 then 3 when cine11 in (6, 7) or cine11 is null or cine11 < 0 then 1 else 0 end"
POLITICA = "case when posicion_politica > 0 then (posicion_politica - 1) // 2 else 5 end"
# Sorteo sin reposición en proporción a `representa` (Efraimidis y Spirakis), con un azar fijo por persona.
ORDEN = f"-ln((hash(id_persona_muestra, {SEMILLA}) % 1000003 + 1) / 1000004.0) / representa"


@dataclass
class Muestra:
    id: str
    agentes: list[Agente]
    #: Cuántos agentes de la tabla cumplen los filtros, antes de recortar al tamaño pedido.
    disponibles: int
    #: A cuántas personas representan esos agentes.
    representadas: int

    def publica(self) -> dict:
        return {"id": self.id, "disponibles": self.disponibles, "representadas": self.representadas, "agentes": [a.publico() for a in self.agentes]}


def limpiar(filtros: dict | None) -> dict:
    """Los filtros de la interfaz, con lo que no venga como "sin filtro"."""
    f = filtros or {}
    entero = lambda clave, defecto: int(f[clave]) if isinstance(f.get(clave), (int, float)) else defecto
    return {
        "region": entero("region", SIN_FILTRO), "edadMin": entero("edadMin", 0), "edadMax": entero("edadMax", EDAD_SIN_TOPE),
        "genero": entero("genero", SIN_FILTRO), "quintil": entero("quintil", SIN_FILTRO),
        "educacion": entero("educacion", SIN_FILTRO), "politica": entero("politica", SIN_FILTRO),
    }


def identificador(filtros: dict, tamano: int) -> str:
    return hashlib.sha256(json.dumps([filtros, tamano], sort_keys=True).encode()).hexdigest()[:12]


class ArchivoFijo:
    """Las 2.000 personas del archivo de pruebas, filtradas en memoria."""

    nombre = "Archivo de 2.000 personas"

    def __init__(self, archivo: Path = ARCHIVO_AGENTES):
        self.agentes = cargar_agentes(archivo)

    def describir(self) -> dict:
        return {"fuente": self.nombre, "agentes": len(self.agentes), "personas": len(self.agentes), "representa": 1}

    def muestra(self, filtros: dict | None, tamano: int) -> Muestra:
        f = limpiar(filtros)
        pasa = lambda valor, filtro: filtro == SIN_FILTRO or valor == filtro
        posibles = [
            a for a in self.agentes
            if pasa(a.region, f["region"]) and a.edad >= f["edadMin"] and (a.edad <= f["edadMax"] or f["edadMax"] >= EDAD_SIN_TOPE)
            and pasa(a.genero, f["genero"]) and pasa(a.quintil, f["quintil"]) and pasa(a.educacion, f["educacion"]) and pasa(a.politica, f["politica"])
        ]
        posibles.sort(key=lambda a: hashlib.sha256(f"{SEMILLA}-{a.id}".encode()).digest())
        elegidos = [dataclasses.replace(a, indice=k) for k, a in enumerate(posibles[:tamano])]
        return Muestra(identificador(f, tamano), elegidos, len(posibles), len(posibles))


class TablaAgentes:
    """La tabla de agentes del repositorio, consultada con DuckDB."""

    nombre = "Tabla de agentes del Censo 2024"

    def __init__(self, carpeta: Path = CARPETA_TABLA):
        import duckdb  # solo hace falta para esta fuente

        ruta = RAIZ / "scripts" / "personas_muestra.py"
        spec = importlib.util.spec_from_file_location("personas_muestra", ruta)
        self._perfiles = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self._perfiles)
        self._etiquetas = self._perfiles.cargar_etiquetas()
        self._secciones = list(self._perfiles.SECCIONES)
        self._comunas = cargar_comunas()
        self._carpeta = carpeta
        if not list(carpeta.glob("region_*.parquet")):
            raise FileNotFoundError(f"No hay tabla de agentes en {carpeta}")
        self._con = duckdb.connect()
        self._cerrojo = threading.Lock()
        self._agentes, self._personas = self._con.execute(f"select count(*), sum(representa) from {self._origen(SIN_FILTRO)}").fetchall()[0]

    def describir(self) -> dict:
        return {"fuente": self.nombre, "agentes": self._agentes, "personas": self._personas, "representa": round(self._personas / self._agentes)}

    def _origen(self, region: int) -> str:
        """Con filtro de región se lee solo el archivo de esa región."""
        archivo = f"region_{REGIONES[region][1]:02d}.parquet" if 0 <= region < len(REGIONES) else "region_*.parquet"
        return f"read_parquet('{(self._carpeta / archivo).as_posix()}')"

    @staticmethod
    def _condiciones(f: dict) -> tuple[str, list]:
        partes, valores = ["edad >= ?"], [f["edadMin"]]
        if f["edadMax"] < EDAD_SIN_TOPE:
            partes.append("edad <= ?")
            valores.append(f["edadMax"])
        for clave, expresion in (("genero", GENERO), ("quintil", "quintil_ingreso - 1"), ("educacion", EDUCACION), ("politica", POLITICA)):
            if f[clave] != SIN_FILTRO:
                partes.append(f"({expresion}) = ?")
                valores.append(f[clave])
        return " and ".join(partes), valores

    def muestra(self, filtros: dict | None, tamano: int) -> Muestra:
        f = limpiar(filtros)
        origen = self._origen(f["region"])
        donde, valores = self._condiciones(f)
        with self._cerrojo:
            cursor = self._con.cursor()
            disponibles, representadas = cursor.execute(f"select count(*), coalesce(sum(representa), 0) from {origen} where {donde}", valores).fetchall()[0]
            resultado = cursor.execute(
                f"""with elegidos as (select id_persona_muestra as id, {ORDEN} as orden from {origen} where {donde} order by orden limit ?)
                    select p.*, p.n_personas as integrantes, e.orden
                    from {origen} p join elegidos e on p.id_persona_muestra = e.id order by e.orden""",
                [*valores, int(tamano)],
            )
            columnas = [c[0] for c in resultado.description]
            filas = [dict(zip(columnas, fila)) for fila in resultado.fetchall()]
        agentes = []
        for indice, fila in enumerate(filas):
            perfil, grupos = self._perfiles.describir(fila, self._etiquetas, self._secciones, con_cep=True)
            datos = self._perfiles.datos_sueltos(fila, self._etiquetas, grupos)
            agentes.append(agente_de(indice, f"p{fila['id_persona_muestra']}", perfil, grupos, datos, self._comunas))
        return Muestra(identificador(f, tamano), agentes, int(disponibles), int(representadas))


def elegir_poblacion(fija: bool = False):
    """La tabla de agentes si se puede leer; si no, o si se pide, el archivo fijo."""
    if not fija:
        try:
            return TablaAgentes()
        except (ImportError, FileNotFoundError) as error:
            print(f"Sin tabla de agentes ({error}); se usa el archivo de 2.000 personas.", flush=True)
    return ArchivoFijo()
