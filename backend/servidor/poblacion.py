"""De dónde salen los agentes de cada consulta: se filtra la población y se sortea una muestra.

`TablaAgentes` lee `data/agentes/` (ver contexto/chile/agentes.md): 1,5 millones de personas
reales del censo, cada una en representación de unas 10. Con los filtros de la interfaz se
queda con quienes los cumplen y sortea hasta el máximo pedido. El sorteo va estratificado por
región, comuna y zona (urbana o rural): cada estrato recibe una cuota fija, proporcional a las
personas que representan sus agentes filtrados, y cada comuna, cada región y cada zona, en su
región y en el país, quedan a menos de una persona de su parte exacta (`repartir`). Dentro de cada estrato se sortea en proporción a
cuántas personas representa cada uno. El filtro `reduccion` elige el nivel de clusterización: un agente por
cada 10, 100, 1.000 o 10.000 personas (los niveles vienen marcados en la tabla).
El perfil de cada persona elegida se arma en el momento, con la misma función que usa el
banco de pruebas (`scripts/personas_muestra.py`). Cada agente guarda también su fila: el
motor escribe con ella el perfil reducido que lee el modelo (`metodo.perfil_de`).

Los filtros son los parámetros de `sociedad.py` (región, género, trabajo, posición política…),
cada uno con varias opciones elegibles, más el rango de edad. Al partir, la tabla se resume en
memoria (`rasgos`: una fila por agente con su opción en cada parámetro) y sobre ese resumen se
filtra, se sortea y se saca el retrato: cuánta gente hay en cada opción entre quienes cumplen
los demás filtros. Leer eso mismo de los archivos tardaba diez veces más.

`ArchivoFijo` es el respaldo: las 2.000 personas de `data/pruebas/poblacion/al_azar_2000.jsonl`.
Se usa si falta DuckDB o la tabla.
"""

import ast
import dataclasses
import hashlib
import json
import math
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from . import metodo, sociedad
from .agentes import ARCHIVO_AGENTES, REGIONES, Agente, agente_de, cargar_agentes, cargar_comunas

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_TABLA = RAIZ / "data" / "agentes"
# La muestra es siempre la misma para los mismos filtros: así la caché de respuestas sirve.
SEMILLA = 2024
EDAD_SIN_TOPE = sociedad.EDAD_SIN_TOPE
EDAD_MINIMA = sociedad.EDAD_MINIMA
# Agentes ya armados que se guardan: al cambiar un filtro, muchos se repiten y no hay que volver a leerlos.
AGENTES_GUARDADOS = 30_000

# Sorteo sin reposición en proporción a las personas que representa cada agente (Efraimidis y Spirakis),
# con un azar fijo por persona. `{peso}` es la columna del nivel de reducción elegido.
ORDEN = f"-ln((hash(id_persona_muestra, {SEMILLA}) % 1000003 + 1) / 1000004.0) / {{peso}}"
# Niveles de reducción: personas por agente y la columna de la tabla que lo dice.
NIVELES = {10: "representa", 100: "representa_100", 1000: "representa_1000", 10000: "representa_10000"}
SIN_REDUCIR = 10
#: Zona del censo (columna `area`): 1 urbana, 2 rural.
ZONAS = {"Urbana": 1, "Rural": 2}


@dataclass
class Muestra:
    id: str
    agentes: list[Agente]
    #: Cuántos agentes de la tabla cumplen los filtros, antes de recortar al tamaño pedido.
    disponibles: int
    #: A cuántas personas representan esos agentes.
    representadas: int
    #: Por parámetro, las personas de cada opción entre quienes cumplen los demás filtros; en
    #: "edad", las de cada edad desde los 14 (ver `sociedad.retrato_de`).
    retrato: dict

    def publica(self) -> dict:
        return {"id": self.id, "disponibles": self.disponibles, "representadas": self.representadas,
                # En este orden viene `s`, la opción de cada agente en cada parámetro.
                "dimensiones": list(sociedad.CLAVES), "retrato": self.retrato, "agentes": [a.publico() for a in self.agentes]}

    def cuerpo(self) -> bytes:
        """La respuesta ya escrita en JSON: se arma una vez y se reutiliza si se vuelve a pedir."""
        if not hasattr(self, "_cuerpo"):
            self._cuerpo = json.dumps(self.publica(), ensure_ascii=False).encode()
        return self._cuerpo


def limpiar(filtros: dict | None) -> dict:
    """Los filtros de la interfaz en una sola forma: quienes piden lo mismo comparten muestra guardada.

    Llegan como {edadMin, edadMax, reduccion, y por parámetro la lista de opciones elegidas}."""
    f = filtros or {}
    entero = lambda clave, defecto: int(f[clave]) if isinstance(f.get(clave), (int, float)) else defecto
    return {
        # Sin filtro de edad y "desde los 14" son lo mismo.
        "edadMin": max(EDAD_MINIMA, entero("edadMin", EDAD_MINIMA)), "edadMax": min(EDAD_SIN_TOPE, entero("edadMax", EDAD_SIN_TOPE)),
        "reduccion": entero("reduccion", SIN_REDUCIR) if entero("reduccion", SIN_REDUCIR) in NIVELES else SIN_REDUCIR,
        "elegidos": sociedad.limpiar(f),
    }


def costo_de_estrato(estrato) -> float:
    """Un número al azar, pero fijo, por estrato (ver `repartir`)."""
    return int.from_bytes(hashlib.blake2b(f"{SEMILLA}-{estrato}".encode(), digest_size=8).digest(), "big") / 2**64


def repartir(tamano: int, estratos: dict, costo=costo_de_estrato) -> dict:
    """Cuántos agentes van de cada estrato: `tamano` repartido en proporción a las personas que
    representan, sin que ningún grupo se desvíe en una persona o más de su parte exacta.

    `estratos` es {(región, comuna, zona): (agentes disponibles, personas que representan)}. La
    parte exacta de un estrato es `tamano` × sus personas / las de todos, y casi nunca es entera.
    Se redondea cada una hacia abajo o hacia arriba de modo que también queden redondeadas así
    las sumas de cada comuna, cada región, cada zona en cada región y cada zona en el país. Es
    un redondeo controlado (Cox, 1987): las partes exactas son un flujo en una red (país →
    región → comuna → estrato → zona de la región → zona → país) y se corren por ciclos de la red,
    sin romper el balance de ningún nodo, hasta que todas sean enteras. Siempre se puede.

    Cuál de los dos redondeos toca a cada estrato lo decide `costo`, un umbral al azar pero fijo
    por estrato: en cada ciclo se corre hacia donde suben los estratos cuya parte fraccionaria
    pasa su umbral (y bajan los que no). Sin las sumas que cuidar, eso sería sortear cada
    redondeo con probabilidad igual a su parte fraccionaria. Como la parte exacta de cada estrato
    crece con el tamaño, con un tamaño y su doble suben casi siempre los mismos, y la muestra chica
    queda casi entera dentro de la grande. Una comuna que pesa menos de una persona de la muestra
    entra o no según su umbral y lo que haya en su región.

    Ningún estrato recibe más agentes de los que tiene: los que no alcanzan su parte exacta
    entran completos y el resto se reparte entre los demás. Las cuotas suman
    `min(tamano, disponibles)`."""
    claves = sorted(estratos)
    disponibles = [max(0, int(estratos[k][0])) for k in claves]
    personas = [max(0, int(round(float(estratos[k][1])))) for k in claves]
    if sum(personas[i] for i, d in enumerate(disponibles) if d) == 0:
        # Sin personas que pesar (no debería pasar), se reparte por agentes disponibles.
        personas = list(disponibles)
    meta = min(max(0, int(tamano)), sum(disponibles))
    libres = [i for i, d in enumerate(disponibles) if d > 0]
    fijos: dict[int, int] = {}
    falta = meta
    # Los estratos chicos para su parte exacta entran completos; se repite porque al sacarlos la
    # parte de los demás sube.
    while libres:
        peso = sum(personas[i] for i in libres)
        topados = {i for i in libres if peso == 0 or falta * personas[i] >= disponibles[i] * peso}
        if not topados:
            break
        for i in topados:
            fijos[i] = disponibles[i]
            falta -= disponibles[i]
        libres = [i for i in libres if i not in topados]
    # Todo en enteros, sobre un denominador común: la parte exacta de un estrato libre es
    # falta × personas / peso, que se guarda como falta × personas (en unidades de 1/peso).
    peso = sum(personas[i] for i in libres) or 1
    valor = {i: falta * personas[i] for i in libres}
    valor.update({i: c * peso for i, c in fijos.items()})

    # La red: cada arista lleva la suma de los estratos que pasan por ella.
    aristas: dict[tuple, list] = {}  # (desde, hasta) -> [valor]

    def sumar(desde, hasta, v):
        aristas.setdefault((desde, hasta), [0])[0] += v

    for i, v in valor.items():
        region, comuna, zona = claves[i]
        sumar("país", ("región", region), v)
        sumar(("región", region), ("comuna", region, comuna), v)
        sumar(("comuna", region, comuna), ("zona de región", region, zona, i), v)
        sumar(("zona de región", region, zona, i), ("zona de región", region, zona), v)
        sumar(("zona de región", region, zona), ("zona", zona), v)
        sumar(("zona", zona), "fin", v)
    # Cada estrato es la arista que va de su comuna a la zona de su región, pasando por un nodo
    # propio (así dos estratos de la misma comuna y zona, si los hubiera, no se confunden).
    lista = list(aristas)
    valores = [aristas[a][0] for a in lista]
    estrato_de_arista = {}
    for n, (desde, hasta) in enumerate(lista):
        if isinstance(hasta, tuple) and len(hasta) == 4:
            estrato_de_arista[n] = hasta[3]
    # Se prefiere subir el estrato cuya parte fraccionaria pasa su umbral (`costo`): como la parte
    # exacta crece con el tamaño, el que sube con un tamaño prefiere subir también con el doble.
    costos = {n: costo(claves[i]) - valores[n] % peso / peso for n, i in estrato_de_arista.items()}
    fraccion = {n for n, v in enumerate(valores) if v % peso}
    vecinas: dict = {}
    for n in fraccion:
        for nodo in lista[n]:
            vecinas.setdefault(nodo, set()).add(n)

    def quitar(n):
        fraccion.discard(n)
        for nodo in lista[n]:
            vecinas[nodo].discard(n)

    while fraccion:
        # Un ciclo de aristas fraccionarias: todo nodo con una tiene al menos otra, porque lo que
        # entra y lo que sale suman lo mismo. Se camina hasta volver a un nodo ya pisado.
        inicio = min(fraccion)
        nodos, pasos, visto = [lista[inicio][0]], [], {lista[inicio][0]: 0}
        actual, anterior = lista[inicio][0], None
        while True:
            n = min(a for a in vecinas[actual] if a != anterior)
            desde, hasta = lista[n]
            siguiente, adelante = (hasta, True) if desde == actual else (desde, False)
            pasos.append((n, adelante))
            if siguiente in visto:
                ciclo = pasos[visto[siguiente]:]
                break
            visto[siguiente] = len(nodos)
            nodos.append(siguiente)
            actual, anterior = siguiente, n
        # Cuánto se puede correr en cada sentido antes de que una arista llegue a un entero.
        subir = min((peso - valores[n] % peso) if adelante else (valores[n] % peso) for n, adelante in ciclo)
        bajar = min((valores[n] % peso) if adelante else (peso - valores[n] % peso) for n, adelante in ciclo)
        cambio = sum((costos[n] if adelante else -costos[n]) for n, adelante in ciclo if n in costos)
        paso = subir if cambio < 0 else -bajar
        for n, adelante in ciclo:
            valores[n] += paso if adelante else -paso
            if valores[n] % peso == 0:
                quitar(n)
    cuotas = [0] * len(claves)
    for n, i in estrato_de_arista.items():
        cuotas[i] = valores[n] // peso
    return {k: c for k, c in zip(claves, cuotas)}


def estrato_de(agente: Agente) -> tuple[int, int, int]:
    """Región, comuna y zona de un agente del archivo fijo (0 si no se sabe)."""
    return agente.region, agente.codigo_comuna, ZONAS.get(agente.atributos.get("Zona", ""), 0)


def identificador(filtros: dict, tamano: int) -> str:
    return hashlib.sha256(json.dumps([filtros, tamano], sort_keys=True).encode()).hexdigest()[:12]


class ArchivoFijo:
    """Las 2.000 personas del archivo de pruebas, filtradas en memoria."""

    nombre = "Archivo de 2.000 personas"

    def __init__(self, archivo: Path = ARCHIVO_AGENTES):
        self.agentes = cargar_agentes(archivo, sociedad.codigos)

    def describir(self) -> dict:
        return {"fuente": self.nombre, "agentes": len(self.agentes), "personas": len(self.agentes), "representa": 1, "niveles": [],
                "parametros": sociedad.publico()}

    def muestra(self, filtros: dict | None, tamano: int) -> Muestra:
        f = limpiar(filtros)
        posibles = [a for a in self.agentes if sociedad.pasa_edad(a.edad, f["edadMin"], f["edadMax"]) and sociedad.coincide(a.rasgos, f["elegidos"])]
        retrato = sociedad.retrato_de(((a.rasgos, a.edad, 1) for a in self.agentes), f["elegidos"], f["edadMin"], f["edadMax"])
        orden = lambda a: hashlib.sha256(f"{SEMILLA}-{a.id}".encode()).digest()
        posibles.sort(key=orden)
        por_estrato: dict[tuple, list[Agente]] = {}
        for a in posibles:
            por_estrato.setdefault(estrato_de(a), []).append(a)
        por_estrato = dict(sorted(por_estrato.items()))
        cuotas = repartir(tamano, {e: (len(lista), len(lista)) for e, lista in por_estrato.items()})
        tomados = sorted((a for e, lista in por_estrato.items() for a in lista[: cuotas[e]]), key=orden)
        elegidos = [dataclasses.replace(a, indice=k) for k, a in enumerate(tomados)]
        return Muestra(identificador(f, tamano), elegidos, len(posibles), len(posibles), retrato)


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
        self._agentes, self._personas = self._con.execute(f"select count(*), sum(representa) from {self._origen()}").fetchall()[0]
        self._columnas = self._columnas_del_perfil(ruta)
        self._armados: OrderedDict[int, Agente] = OrderedDict()
        de_la_tabla = {c[0] for c in self._con.execute(f"describe select * from {self._origen()}").fetchall()}
        self._niveles = {n: columna for n, columna in NIVELES.items() if columna in de_la_tabla}
        # El resumen en memoria: la opción de cada agente en cada parámetro y sus pesos por nivel.
        codigos = ", ".join(f"({p.sql})::tinyint as c_{p.clave}" for p in sociedad.PARAMETROS)
        self._con.execute(f"create table rasgos as select id_persona_muestra, region, comuna, area, edad, {codigos}, {', '.join(self._niveles.values())} from {self._origen()}")

    def _columnas_del_perfil(self, ruta: Path) -> str:
        """Solo las columnas que el perfil usa: leer las 230 de la tabla cuesta el doble.

        Son las que aparecen nombradas en scripts/personas_muestra.py, más las de discriminación,
        que ese script arma por prefijo."""
        de_la_tabla = [c[0] for c in self._con.execute(f"describe select * from {self._origen()}").fetchall()]
        nombradas = {nodo.value for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))) if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)}
        usadas = [c for c in de_la_tabla if c in nombradas or c.startswith("discrim_") or c in ("id_persona_muestra", "n_personas", "representa")]
        return ", ".join(usadas)

    def describir(self) -> dict:
        return {"fuente": self.nombre, "agentes": self._agentes, "personas": self._personas, "representa": round(self._personas / self._agentes),
                "niveles": sorted(self._niveles), "parametros": sociedad.publico()}

    def _origen(self, regiones: list[int] | None = None) -> str:
        """Los archivos de la tabla; con una sola región elegida se lee solo el suyo."""
        archivo = f"region_{REGIONES[regiones[0]][1]:02d}.parquet" if regiones and len(regiones) == 1 else "region_*.parquet"
        return f"read_parquet('{(self._carpeta / archivo).as_posix()}')"

    def _condiciones(self, f: dict, peso: str, salvo: str | None = None, con_edad: bool = True) -> str:
        """La condición sobre `rasgos` de quienes cumplen los filtros. `salvo` deja un parámetro
        sin filtrar y `con_edad` falso deja la edad abierta: así se arma el retrato. Todo lo que
        se escribe en la consulta son enteros ya validados por `limpiar`."""
        partes = [f"edad >= {f['edadMin'] if con_edad else EDAD_MINIMA}"]
        # En un nivel más reducido solo quedan los agentes marcados para ese nivel.
        if peso != NIVELES[SIN_REDUCIR]:
            partes.append(f"{peso} is not null")
        if con_edad and f["edadMax"] < EDAD_SIN_TOPE:
            partes.append(f"edad <= {f['edadMax']}")
        partes += [f"c_{clave} in ({', '.join(map(str, indices))})" for clave, indices in f["elegidos"].items() if clave != salvo]
        return " and ".join(partes)

    def _retrato(self, cursor, f: dict, peso: str) -> dict:
        """Personas por opción de cada parámetro, cada uno sin su propio filtro, y por edad."""
        consultas = [
            f"select {k} as parametro, c_{clave}::integer as opcion, sum({peso})::bigint as personas from rasgos where {self._condiciones(f, peso, salvo=clave)} group by 2"
            for k, clave in enumerate(sociedad.CLAVES)
        ]
        consultas.append(f"select -1, least(edad, {EDAD_SIN_TOPE})::integer, sum({peso})::bigint from rasgos where {self._condiciones(f, peso, con_edad=False)} group by 2")
        retrato = sociedad.retrato_vacio()
        for parametro, opcion, personas in cursor.execute(" union all ".join(consultas)).fetchall():
            if parametro < 0:
                retrato["edad"][opcion - EDAD_MINIMA] = int(personas)
            elif opcion >= 0:
                retrato[sociedad.CLAVES[parametro]][opcion] = int(personas)
        return retrato

    def muestra(self, filtros: dict | None, tamano: int) -> Muestra:
        f = limpiar(filtros)
        origen = self._origen(f["elegidos"].get("region"))
        peso = self._niveles.get(f["reduccion"], NIVELES[SIN_REDUCIR])
        donde = self._condiciones(f, peso)
        codigos = ", ".join(f"c_{clave}" for clave in sociedad.CLAVES)
        with self._cerrojo:
            cursor = self._con.cursor()
            retrato = self._retrato(cursor, f, peso)
            # Primero quiénes: se sortea sobre el resumen en memoria.
            conteo = cursor.execute(
                f"""select region, comuna, area, count(*), coalesce(sum({peso}), 0) from rasgos where {donde}
                    group by all order by region, comuna, area"""
            ).fetchall()
            disponibles = sum(n for *_, n, _ in conteo)
            representadas = sum(p for *_, p in conteo)
            cuotas = [(*e, c) for e, c in repartir(tamano, {(r, c, z): (n, p) for r, c, z, n, p in conteo}).items() if c > 0]
            # Cada estrato (región, comuna y zona) aporta sus primeros en el orden del sorteo,
            # hasta su cuota; el orden mezclado entre estratos se mantiene. El azar por persona
            # se repite entre 1,5 M de filas: el id desempata para que la muestra y su orden sean
            # siempre los mismos.
            sorteo = cursor.execute(
                f"""select id_persona_muestra, {peso}, {codigos} from (
                        select *, {ORDEN.format(peso=peso)} as orden,
                               row_number() over (partition by region, comuna, area order by {ORDEN.format(peso=peso)}, id_persona_muestra) as puesto
                        from rasgos where {donde}
                    ) join (select unnest(?::integer[]) as region, unnest(?::integer[]) as comuna, unnest(?::integer[]) as area,
                                   unnest(?::integer[]) as cuota) using (region, comuna, area)
                    where puesto <= cuota order by orden, id_persona_muestra""",
                [list(columna) for columna in zip(*cuotas)],
            ).fetchall() if cuotas else []
            elegidos = [fila[0] for fila in sorteo]
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
            agentes = [dataclasses.replace(self._armados[i], indice=k, representa=int(w), rasgos=tuple(rasgos)) for k, (i, w, *rasgos) in enumerate(sorteo)]
            for i in elegidos:
                self._armados.move_to_end(i)
            while len(self._armados) > AGENTES_GUARDADOS:
                self._armados.popitem(last=False)
        return Muestra(identificador(f, tamano), agentes, int(disponibles), int(representadas), retrato)


def elegir_poblacion():
    """La tabla de agentes si se puede leer; si no, el archivo fijo."""
    try:
        return TablaAgentes()
    except (ImportError, FileNotFoundError) as error:
        print(f"Sin tabla de agentes ({error}); se usa el archivo de 2.000 personas.", flush=True)
    return ArchivoFijo()
