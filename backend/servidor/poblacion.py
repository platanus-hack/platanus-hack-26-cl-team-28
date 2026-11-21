"""De dónde salen los agentes de cada consulta: se filtra la población y se sortea una muestra.

`TablaAgentes` lee `data/agentes/` (ver contexto/chile/agentes.md): 1,5 millones de personas
reales del censo, cada una en representación de unas 10. Con los filtros de la interfaz se
queda con quienes los cumplen y sortea hasta el máximo pedido. El sorteo va estratificado por
región: cada región recibe una cuota fija, proporcional a las personas que representan sus
agentes filtrados (`repartir`), y dentro de ella se sortea en proporción a cuántas personas
representa cada uno. El filtro `reduccion` elige el nivel de clusterización: un agente por
cada 10, 100 o 1.000 personas (los niveles vienen marcados en la tabla).
El perfil de cada persona elegida se arma en el momento, con la misma función que usa el
banco de pruebas (`scripts/personas_muestra.py`). Cada agente guarda también su fila: el
motor escribe con ella el perfil reducido que lee el modelo (`metodo.perfil_de`).

`ArchivoFijo` es el respaldo: las 2.000 personas de `data/pruebas/poblacion/al_azar_2000.jsonl`.
Se usa si falta DuckDB o la tabla, y siempre con la corrida grabada, que solo tiene respuestas
de esas personas.
"""

import ast
import dataclasses
import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from . import metodo
from .agentes import ARCHIVO_AGENTES, REGIONES, Agente, agente_de, cargar_agentes, cargar_comunas

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_TABLA = RAIZ / "data" / "agentes"
# La muestra es siempre la misma para los mismos filtros: así la caché de respuestas sirve.
SEMILLA = 2024
EDAD_SIN_TOPE = 90
EDAD_MINIMA = 14
SIN_FILTRO = -1
# Agentes ya armados que se guardan: al cambiar un filtro, muchos se repiten y no hay que volver a leerlos.
AGENTES_GUARDADOS = 30_000

# Los mismos tramos que usa la interfaz para filtrar (índices de frontend/src/dominio/catalogos.ts).
GENERO = "case when genero in (1, 3) then 1 when genero in (2, 4) then 0 when sexo = 1 then 1 else 0 end"
EDUCACION = "case when cine11 between 8 and 11 then 3 when cine11 in (6, 7) or cine11 is null or cine11 < 0 then 1 else 0 end"
POLITICA = "case when posicion_politica > 0 then (posicion_politica - 1) // 2 else 5 end"
# Sorteo sin reposición en proporción a las personas que representa cada agente (Efraimidis y Spirakis),
# con un azar fijo por persona. `{peso}` es la columna del nivel de reducción elegido.
ORDEN = f"-ln((hash(id_persona_muestra, {SEMILLA}) % 1000003 + 1) / 1000004.0) / {{peso}}"
# Niveles de reducción: personas por agente y la columna de la tabla que lo dice.
NIVELES = {10: "representa", 100: "representa_100", 1000: "representa_1000"}
SIN_REDUCIR = 10


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

    def cuerpo(self) -> bytes:
        """La respuesta ya escrita en JSON: se arma una vez y se reutiliza si se vuelve a pedir."""
        if not hasattr(self, "_cuerpo"):
            self._cuerpo = json.dumps(self.publica(), ensure_ascii=False).encode()
        return self._cuerpo


def limpiar(filtros: dict | None) -> dict:
    """Los filtros de la interfaz, con lo que no venga como "sin filtro"."""
    f = filtros or {}
    entero = lambda clave, defecto: int(f[clave]) if isinstance(f.get(clave), (int, float)) else defecto
    return {
        # Sin filtro de edad y "desde los 14" son lo mismo: así comparten muestra guardada.
        "region": entero("region", SIN_FILTRO), "edadMin": max(EDAD_MINIMA, entero("edadMin", EDAD_MINIMA)), "edadMax": min(EDAD_SIN_TOPE, entero("edadMax", EDAD_SIN_TOPE)),
        "genero": entero("genero", SIN_FILTRO), "quintil": entero("quintil", SIN_FILTRO),
        "educacion": entero("educacion", SIN_FILTRO), "politica": entero("politica", SIN_FILTRO),
        "reduccion": entero("reduccion", SIN_REDUCIR) if entero("reduccion", SIN_REDUCIR) in NIVELES else SIN_REDUCIR,
    }


def repartir(tamano: int, por_region: dict[int, tuple[int, float]]) -> dict[int, int]:
    """Cuántos agentes van de cada región: `tamano` repartido en proporción a las personas que
    representan, por el método del resto mayor.

    `por_region` es {región: (agentes disponibles, personas que representan)}. Ninguna región
    recibe más agentes de los que tiene; lo que no cabe en una se reparte entre las demás. Las
    cuotas suman `min(tamano, disponibles)`. No hay mínimo: una región que pesa menos de media
    persona de la muestra puede quedar en 0, que es lo proporcional."""
    cuotas = {r: 0 for r in por_region}
    abiertas = {r for r, (disponibles, _) in por_region.items() if disponibles > 0}
    falta = min(int(tamano), sum(d for d, _ in por_region.values()))
    while falta > 0 and abiertas:
        peso = sum(max(0.0, float(por_region[r][1])) for r in abiertas)
        # Sin personas que pesar (no debería pasar), se reparte por agentes disponibles.
        medida = (lambda r: max(0.0, float(por_region[r][1]))) if peso > 0 else (lambda r: float(por_region[r][0]))
        total = peso if peso > 0 else sum(por_region[r][0] for r in abiertas)
        ideal = {r: falta * medida(r) / total for r in abiertas}
        extra = {r: int(ideal[r]) for r in abiertas}
        # El resto mayor: los que quedan van a las regiones con mayor parte fraccionaria.
        sobran = falta - sum(extra.values())
        for r in sorted(abiertas, key=lambda r: (-(ideal[r] - extra[r]), r))[:sobran]:
            extra[r] += 1
        topadas = set()
        for r in abiertas:
            cabe = por_region[r][0] - cuotas[r]
            cuotas[r] += min(extra[r], cabe)
            if extra[r] >= cabe:
                topadas.add(r)
        falta = min(int(tamano), sum(d for d, _ in por_region.values())) - sum(cuotas.values())
        abiertas -= topadas
    return cuotas


def identificador(filtros: dict, tamano: int) -> str:
    return hashlib.sha256(json.dumps([filtros, tamano], sort_keys=True).encode()).hexdigest()[:12]


class ArchivoFijo:
    """Las 2.000 personas del archivo de pruebas, filtradas en memoria."""

    nombre = "Archivo de 2.000 personas"

    def __init__(self, archivo: Path = ARCHIVO_AGENTES):
        self.agentes = cargar_agentes(archivo)

    def describir(self) -> dict:
        return {"fuente": self.nombre, "agentes": len(self.agentes), "personas": len(self.agentes), "representa": 1, "niveles": []}

    def muestra(self, filtros: dict | None, tamano: int) -> Muestra:
        f = limpiar(filtros)
        pasa = lambda valor, filtro: filtro == SIN_FILTRO or valor == filtro
        posibles = [
            a for a in self.agentes
            if pasa(a.region, f["region"]) and a.edad >= f["edadMin"] and (a.edad <= f["edadMax"] or f["edadMax"] >= EDAD_SIN_TOPE)
            and pasa(a.genero, f["genero"]) and pasa(a.quintil, f["quintil"]) and pasa(a.educacion, f["educacion"]) and pasa(a.politica, f["politica"])
        ]
        orden = lambda a: hashlib.sha256(f"{SEMILLA}-{a.id}".encode()).digest()
        posibles.sort(key=orden)
        por_region: dict[int, list[Agente]] = {}
        for a in posibles:
            por_region.setdefault(a.region, []).append(a)
        cuotas = repartir(tamano, {r: (len(lista), len(lista)) for r, lista in por_region.items()})
        tomados = sorted((a for r, lista in por_region.items() for a in lista[: cuotas[r]]), key=orden)
        elegidos = [dataclasses.replace(a, indice=k) for k, a in enumerate(tomados)]
        return Muestra(identificador(f, tamano), elegidos, len(posibles), len(posibles))


class TablaAgentes:
    """La tabla de agentes del repositorio, consultada con DuckDB."""

    nombre = "Tabla de agentes del Censo 2024"

    def __init__(self, carpeta: Path = CARPETA_TABLA):
        import duckdb  # solo hace falta para esta fuente

        ruta = RAIZ / "scripts" / "personas_muestra.py"
        # El mismo módulo y las mismas etiquetas con que el motor reescribe los perfiles filtrados.
        self._perfiles, self._etiquetas, self._secciones = metodo.redactor()
        self._comunas = cargar_comunas()
        self._carpeta = carpeta
        if not list(carpeta.glob("region_*.parquet")):
            raise FileNotFoundError(f"No hay tabla de agentes en {carpeta}")
        self._con = duckdb.connect()
        self._cerrojo = threading.Lock()
        self._agentes, self._personas = self._con.execute(f"select count(*), sum(representa) from {self._origen(SIN_FILTRO)}").fetchall()[0]
        self._columnas = self._columnas_del_perfil(ruta)
        self._armados: OrderedDict[int, Agente] = OrderedDict()
        de_la_tabla = {c[0] for c in self._con.execute(f"describe select * from {self._origen(SIN_FILTRO)}").fetchall()}
        self._niveles = {n: columna for n, columna in NIVELES.items() if columna in de_la_tabla}

    def _columnas_del_perfil(self, ruta: Path) -> str:
        """Solo las columnas que el perfil usa: leer las 230 de la tabla cuesta el doble.

        Son las que aparecen nombradas en scripts/personas_muestra.py, más las de discriminación,
        que ese script arma por prefijo."""
        de_la_tabla = [c[0] for c in self._con.execute(f"describe select * from {self._origen(SIN_FILTRO)}").fetchall()]
        nombradas = {nodo.value for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))) if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)}
        usadas = [c for c in de_la_tabla if c in nombradas or c.startswith("discrim_") or c in ("id_persona_muestra", "n_personas", "representa")]
        return ", ".join(usadas)

    def describir(self) -> dict:
        return {"fuente": self.nombre, "agentes": self._agentes, "personas": self._personas, "representa": round(self._personas / self._agentes),
                "niveles": sorted(self._niveles)}

    def _origen(self, region: int) -> str:
        """Con filtro de región se lee solo el archivo de esa región."""
        archivo = f"region_{REGIONES[region][1]:02d}.parquet" if 0 <= region < len(REGIONES) else "region_*.parquet"
        return f"read_parquet('{(self._carpeta / archivo).as_posix()}')"

    def _condiciones(self, f: dict, peso: str) -> tuple[str, list]:
        partes, valores = ["edad >= ?"], [f["edadMin"]]
        # En un nivel más reducido solo quedan los agentes marcados para ese nivel.
        if peso != NIVELES[SIN_REDUCIR]:
            partes.append(f"{peso} is not null")
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
        peso = self._niveles.get(f["reduccion"], NIVELES[SIN_REDUCIR])
        donde, valores = self._condiciones(f, peso)
        with self._cerrojo:
            cursor = self._con.cursor()
            # Primero quiénes: solo se leen las columnas de los filtros y el orden del sorteo.
            conteo = cursor.execute(f"select region, count(*), coalesce(sum({peso}), 0) from {origen} where {donde} group by region", valores).fetchall()
            disponibles = sum(n for _, n, _ in conteo)
            representadas = sum(p for _, _, p in conteo)
            cuotas = [(r, c) for r, c in repartir(tamano, {r: (n, p) for r, n, p in conteo}).items() if c > 0]
            # Cada región aporta sus primeros en el orden del sorteo, hasta su cuota; el orden
            # mezclado entre regiones se mantiene. El azar por persona se repite entre 1,5 M de
            # filas: el id desempata para que la muestra y su orden sean siempre los mismos.
            sorteo = cursor.execute(
                f"""select id_persona_muestra, {peso} from (
                        select id_persona_muestra, {peso}, region, {ORDEN.format(peso=peso)} as orden,
                               row_number() over (partition by region order by {ORDEN.format(peso=peso)}, id_persona_muestra) as puesto
                        from {origen} where {donde}
                    ) join (select unnest(?::integer[]) as region, unnest(?::integer[]) as cuota) using (region)
                    where puesto <= cuota order by orden, id_persona_muestra""",
                [*valores, [r for r, _ in cuotas], [c for _, c in cuotas]],
            ).fetchall() if cuotas else []
            elegidos = [i for i, _ in sorteo]
            # Después sus datos, solo de quienes no estaban ya armados.
            faltan = [i for i in elegidos if i not in self._armados]
            if faltan:
                resultado = cursor.execute(
                    f"select {self._columnas}, n_personas as integrantes from {origen} where id_persona_muestra in (select unnest(?::bigint[]))", [faltan]
                )
                columnas = [c[0] for c in resultado.description]
                for valores_fila in resultado.fetchall():
                    fila = dict(zip(columnas, valores_fila))
                    perfil, grupos = self._perfiles.describir(fila, self._etiquetas, self._secciones, con_cep=True)
                    datos = self._perfiles.datos_sueltos(fila, self._etiquetas, grupos)
                    self._armados[fila["id_persona_muestra"]] = agente_de(0, f"p{fila['id_persona_muestra']}", perfil, grupos, datos, self._comunas, fila)
            agentes = [dataclasses.replace(self._armados[i], indice=k, representa=int(w)) for k, (i, w) in enumerate(sorteo)]
            for i in elegidos:
                self._armados.move_to_end(i)
            while len(self._armados) > AGENTES_GUARDADOS:
                self._armados.popitem(last=False)
        return Muestra(identificador(f, tamano), agentes, int(disponibles), int(representadas))


def elegir_poblacion(fija: bool = False):
    """La tabla de agentes si se puede leer; si no, o si se pide, el archivo fijo."""
    if not fija:
        try:
            return TablaAgentes()
        except (ImportError, FileNotFoundError) as error:
            print(f"Sin tabla de agentes ({error}); se usa el archivo de 2.000 personas.", flush=True)
    return ArchivoFijo()
