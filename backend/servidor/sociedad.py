"""Los parámetros de la sociedad con que la interfaz elige a quiénes preguntar.

Cada parámetro es una lista corta de opciones (región, género, situación laboral, posición
política…). Aquí se define, en un solo lugar, cómo se saca la opción de cada persona:

- de la tabla de agentes, con una expresión SQL (`sql`), que es la que filtra y cuenta;
- del perfil ya escrito, con una función sobre sus grupos y datos sueltos (`de_perfil`), para
  el archivo fijo de respaldo, que no trae las columnas de la tabla.

Las dos formas dan el mismo índice (`tests/test_sociedad.py` lo comprueba) y -1 cuando el dato
no existe para esa persona: quien tiene -1 queda fuera al filtrar por ese parámetro. Los de
opinión vienen imputados desde la CEP y solo existen para mayores de 18 años.

El orden de `PARAMETROS` y el de sus opciones es el que viaja a la interfaz
(`frontend/src/vivo/sociedad.ts` lleva los rótulos y cómo se dibuja cada uno).

Un filtro es {clave: [índices elegidos]}; sin lista, o con todas las opciones, no filtra. El
retrato de una población es, por parámetro, cuántas personas hay en cada opción entre quienes
cumplen los *demás* filtros: así la interfaz muestra de antemano cuánta gente suma o quita
cada opción.
"""

from dataclasses import dataclass
from typing import Callable

from .agentes import CODIGO_A_INDICE, REGIONES

SIN_DATO = -1
EDAD_MINIMA = 14
# El censo publica la edad con tope: 85 es «85 años o más».
EDAD_SIN_TOPE = 85


@dataclass(frozen=True)
class Parametro:
    clave: str
    opciones: tuple[str, ...]
    #: Expresión sobre las columnas de la tabla de agentes: el índice de la opción, o -1.
    sql: str
    #: Lo mismo desde (grupos, datos) de `scripts/personas_muestra.py`.
    de_perfil: Callable[[dict, dict], int]


def _de_grupo(nombre: str, opciones: dict[str, int], por_defecto: int = SIN_DATO) -> Callable[[dict, dict], int]:
    return lambda grupos, datos: opciones.get(grupos.get(nombre), por_defecto)


def _trabajo(grupos: dict, datos: dict) -> int:
    situacion = grupos.get("Situación laboral")
    return SIN_DATO if not situacion else {"Desocupado": 1, "Fuera de la fuerza de trabajo": 2}.get(situacion, 0)


def _menores(grupos: dict, datos: dict) -> int:
    menores = grupos.get("Menores en el hogar") or "Sin dato"
    return SIN_DATO if menores == "Sin dato" else 1 if menores == "Sin menores" else 0


def _politica(grupos: dict, datos: dict) -> int:
    # Sin el grupo no hay datos de opinión (menores de 18); con él, no ubicarse es una respuesta.
    if "Posición política" not in grupos:
        return SIN_DATO
    return (datos["posicion_politica"] - 1) // 2 if datos.get("posicion_politica") else 5


PARAMETROS: tuple[Parametro, ...] = (
    Parametro(
        "region", tuple(nombre for nombre, _ in REGIONES),
        "case region " + " ".join(f"when {codigo} then {i}" for i, (_, codigo) in enumerate(REGIONES)) + " else -1 end",
        lambda grupos, datos: CODIGO_A_INDICE.get(datos.get("region"), SIN_DATO),
    ),
    Parametro(
        "genero", ("Mujeres", "Hombres"),
        "case when genero in (1, 3) then 1 when genero in (2, 4) then 0 when sexo = 1 then 1 else 0 end",
        lambda grupos, datos: {"Femenino": 0, "Masculino": 1}.get(datos.get("genero"), 0),
    ),
    Parametro(
        "educacion", ("Básica o menos", "Media", "Superior"),
        "case when cine11 between 8 and 11 then 2 when cine11 in (6, 7) or cine11 is null or cine11 < 0 then 1 else 0 end",
        _de_grupo("Nivel educacional", {"Básica o menos": 0, "Media": 1, "Superior": 2}, 1),
    ),
    Parametro(
        "nacionalidad", ("Chilena", "Extranjera"),
        # Quien tiene doble nacionalidad cuenta como chilena.
        "case when p27_nacionalidad in (1, 2) then 0 when p27_nacionalidad = 3 then 1 else -1 end",
        _de_grupo("Nacionalidad", {"Chilena": 0, "Doble nacionalidad": 0, "Extranjera": 1}),
    ),
    Parametro(
        "trabajo", ("Trabaja", "Busca trabajo", "No trabaja ni busca"),
        "case sit_fuerza_trabajo when 1 then 0 when 2 then 1 when 3 then 2 else -1 end",
        _trabajo,
    ),
    Parametro(
        "menores", ("Con menores de 18", "Sin menores"),
        "case when id_hogar_muestra is null then -1 when len(coalesce(edades_menores, [])) > 0 then 0 else 1 end",
        _menores,
    ),
    Parametro(
        "vivienda", ("Propia", "Arrendada", "Cedida u otra"),
        "case when id_hogar_muestra is null then -1 when p12_tenencia_viv in (1, 2) then 0 when p12_tenencia_viv in (3, 4) then 1 when p12_tenencia_viv >= 0 then 2 else -1 end",
        _de_grupo("Tenencia de la vivienda", {"Propia": 0, "Arrendada": 1, "Cedida u otra": 2}),
    ),
    Parametro(
        "salud", ("Fonasa A o B", "Fonasa C o D", "Isapre", "Otra"),
        # «Otra» junta Fonasa sin grupo declarado, Fuerzas Armadas, otro sistema y sin previsión.
        "case when prevision_salud = 1 and fonasa_grupo in (1, 2) then 0 when prevision_salud = 1 and fonasa_grupo in (3, 4) then 1 "
        "when prevision_salud = 2 then 2 when prevision_salud >= 0 then 3 else -1 end",
        _de_grupo("Previsión de salud", {"Fonasa A o B": 0, "Fonasa C o D": 1, "Isapre": 2, "Fonasa sin grupo": 3, "Otra o ninguna": 3}),
    ),
    Parametro(
        "quintil", ("I", "II", "III", "IV", "V"),
        "case when quintil_ingreso between 1 and 5 then quintil_ingreso - 1 else -1 end",
        lambda grupos, datos: datos["quintil"] - 1 if 1 <= (datos.get("quintil") or 0) <= 5 else SIN_DATO,
    ),
    Parametro(
        "politica", ("Izquierda", "Centroizquierda", "Centro", "Centroderecha", "Derecha", "No se ubica"),
        "case when posicion_politica is null then -1 when posicion_politica > 0 then (posicion_politica - 1) // 2 else 5 end",
        _politica,
    ),
    Parametro(
        "gobierno", ("Aprueba", "Desaprueba", "Ni aprueba ni desaprueba"),
        "case when posicion_politica is null then -1 else (case aprueba_gobierno when 1 then 0 when 2 then 1 when 3 then 2 else -1 end) end",
        _de_grupo("Evaluación del gobierno", {"Aprueba": 0, "Desaprueba": 1, "Ni aprueba ni desaprueba": 2}),
    ),
    Parametro(
        "voto", ("Jara", "Kast", "Blanco o nulo", "No votó o no responde"),
        "case when posicion_politica is null then -1 when voto_segunda_vuelta_2025 = 1 then 0 when voto_segunda_vuelta_2025 = 2 then 1 "
        "when voto_segunda_vuelta_2025 in (3, 4) then 2 else 3 end",
        _de_grupo("Voto en 2025", {"Jara": 0, "Kast": 1, "Blanco o nulo": 2, "No votó o no responde": 3}),
    ),
    Parametro(
        "confianza", ("Mucha o bastante", "Poca o nada"),
        "case when posicion_politica is null then -1 when confianza_gobierno in (1, 2) then 0 when confianza_gobierno in (3, 4) then 1 else -1 end",
        _de_grupo("Confianza en el gobierno", {"Mucha o bastante": 0, "Poca o nada": 1}),
    ),
)
CLAVES: tuple[str, ...] = tuple(p.clave for p in PARAMETROS)
POR_CLAVE: dict[str, Parametro] = {p.clave: p for p in PARAMETROS}
POSICION: dict[str, int] = {clave: k for k, clave in enumerate(CLAVES)}


def publico() -> list[dict]:
    """El catálogo como lo pide la interfaz: clave y opciones, en el orden en que viajan los códigos."""
    return [{"clave": p.clave, "opciones": list(p.opciones)} for p in PARAMETROS]


def codigos(grupos: dict, datos: dict) -> tuple[int, ...]:
    """La opción de una persona en cada parámetro, desde su perfil ya escrito."""
    return tuple(p.de_perfil(grupos, datos) for p in PARAMETROS)


def limpiar(filtros: dict | None) -> dict[str, list[int]]:
    """Lo elegido en cada parámetro, ordenado y sin repetidos. Solo quedan los que de verdad
    filtran: sin opciones, o con todas, es lo mismo que no filtrar."""
    f = filtros or {}
    elegidos = {}
    for p in PARAMETROS:
        pedido = f.get(p.clave)
        if not isinstance(pedido, list):
            continue
        indices = sorted({int(v) for v in pedido if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < len(p.opciones) and v == int(v)})
        if indices and len(indices) < len(p.opciones):
            elegidos[p.clave] = indices
    return elegidos


def edad_tope(edad: int) -> int:
    """La edad como se cuenta en el retrato: del tope en adelante es un solo tramo."""
    return max(EDAD_MINIMA, min(EDAD_SIN_TOPE, edad))


def pasa_edad(edad: int, desde: int, hasta: int) -> bool:
    return edad >= desde and (edad <= hasta or hasta >= EDAD_SIN_TOPE)


def coincide(rasgos: tuple[int, ...], elegidos: dict[str, list[int]], salvo: str | None = None) -> bool:
    """¿Cumple la persona lo elegido? `salvo` deja un parámetro sin mirar."""
    return all(rasgos[POSICION[clave]] in indices for clave, indices in elegidos.items() if clave != salvo)


def retrato_vacio() -> dict[str, list[int]]:
    return {p.clave: [0] * len(p.opciones) for p in PARAMETROS} | {"edad": [0] * (EDAD_SIN_TOPE - EDAD_MINIMA + 1)}


def retrato_de(personas, elegidos: dict[str, list[int]], desde: int, hasta: int) -> dict[str, list[int]]:
    """El retrato en memoria. `personas` son tuplas (rasgos, edad, personas que representa)."""
    retrato = retrato_vacio()
    for rasgos, edad, peso in personas:
        # Cuántos filtros no cumple y cuál: quien falla uno solo cuenta en el retrato de ese.
        fallas = [clave for clave, indices in elegidos.items() if rasgos[POSICION[clave]] not in indices]
        if len(fallas) > 1 or edad < EDAD_MINIMA:
            continue
        # La edad tampoco mira su propio filtro: el histograma muestra todas las edades.
        if not fallas:
            retrato["edad"][edad_tope(edad) - EDAD_MINIMA] += peso
        if not pasa_edad(edad, desde, hasta):
            continue
        for clave in fallas or CLAVES:
            opcion = rasgos[POSICION[clave]]
            if opcion >= 0:
                retrato[clave][opcion] += peso
    return retrato
