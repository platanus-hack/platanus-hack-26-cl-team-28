"""El método de encuesta es el de `scripts/probar_modelo.py`: mismas instrucciones, mismas
preguntas y mismo perfil. Aquí solo se importa, para que lo que se cambie allá sea lo que usa el
servidor, sin copias que se desalineen.

Lo que el servidor fija del banco de pruebas:
- Redacción 1 de las instrucciones y las preguntas en su orden.
- El perfil en prosa, por secciones (`scripts/personas_muestra.py`), con el filtro de datos de
  `scripts/filtro_perfil.py`: al modelo no le llega todo lo que se sabe de la persona, sino el
  núcleo más los datos de los temas que toca la política. `PERFIL` en el entorno elige el
  nivel: `tematico` (por defecto), `nucleo` o `completo` (sin filtro, como antes).
- Sin pregunta de control cuando responde Claude: ahí la primera respuesta sí depende del
  perfil. El modelo local la lleva, como en el banco (`cfg_local`).

La encuesta es fija: las cinco preguntas del banco (apoyo, justicia, confianza, efectividad e
influencia), cada una con un entero de 1 a 7 y su propia escala (`ESCALAS`: qué significan el 1
y el 7). La primera es la que decide la postura de cada persona (a favor, indecisa o en contra).
"""

import functools
import importlib.util
import os
import sys
import threading
from collections import OrderedDict
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _cargar(nombre: str):
    """Un script del banco como módulo. Queda registrado: si otro script lo importa, es el mismo."""
    if nombre in sys.modules:
        return sys.modules[nombre]
    spec = importlib.util.spec_from_file_location(nombre, _SCRIPTS / f"{nombre}.py")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    try:
        spec.loader.exec_module(modulo)
    except BaseException:
        del sys.modules[nombre]
        raise
    return modulo


banco = _cargar("probar_modelo")
filtro = _cargar("filtro_perfil")

#: La primera pregunta del banco («¿Estarías de acuerdo con que se implemente esta política en tu región?»)
#: supone que el texto es una medida. Cuando es una afirmación («la intervención estatal genera demasiada
#: burocracia») los agentes contestaban al revés: quien estaba de acuerdo con la afirmación respondía que no
#: quería que «se implemente». Medido con la CEP 96, el lado correcto pasó de 20 % a 100 % con esta redacción
#: (data/pruebas/realidad_1000/INFORME.md). Las demás preguntas son las del banco.
APOYO_BANCO: str = banco.PREGUNTAS[0]
APOYO: str = "¿Estás de acuerdo o en desacuerdo con lo que plantea el tema de la encuesta?"
PREGUNTAS: list[str] = [APOYO, *banco.PREGUNTAS[1:]]
CLAVES: list[str] = banco.CLAVES
#: Qué significan el 1 y el 7 en cada pregunta, en su orden.
ESCALAS: list[tuple[str, str]] = banco.ESCALAS
#: El nombre corto de cada pregunta (Apoyo, Justicia...).
NOMBRES: list[str] = banco.NOMBRES
lineas_preguntas = banco.lineas_preguntas

#: Cómo arma el banco los mensajes cuando responde Claude, en lotes.
CFG = {"orden": list(range(len(CLAVES))), "control": False, "etiqueta": None, "redaccion": 1, "perfil": "prosa"}

#: Cuánto del perfil lee el modelo: uno de `filtro.NIVELES`.
NIVEL: str = os.environ.get("PERFIL", "").strip().lower() or "tematico"
if NIVEL not in filtro.NIVELES:
    raise SystemExit(f"PERFIL={NIVEL!r} no existe; los niveles son {', '.join(filtro.NIVELES)}")
#: Las etiquetas políticas del perfil. No se le entregan al modelo: con ellas contesta por bando y separa a
#: izquierda y derecha el doble que la CEP (51 puntos contra 22). Sin ellas, y conservando lo que la persona
#: opina de fondo (rol del Estado, inmigración, seguridad, confianza), la distancia queda como la real y los
#: grupos siguen igual de bien ordenados. `IDENTIDAD_POLITICA=1` en el entorno las devuelve.
IDENTIDAD_POLITICA = frozenset({"posicion_politica", "partido", "sin_partido", "voto_2025", "aprueba_gobierno", "aprueba_gobierno_anterior"})
CON_IDENTIDAD: bool = os.environ.get("IDENTIDAD_POLITICA", "").strip().lower() in ("1", "si", "sí", "true")
#: Lo que distingue a este perfil del completo en la caché de respuestas (vacío si va completo:
#: las respuestas guardadas antes del filtro se dieron con el perfil completo y siguen sirviendo).
VERSION_PERFIL: str = ("" if NIVEL == "completo" else f"{NIVEL}:{filtro.VERSION}") + ("" if CON_IDENTIDAD else ":sin-identidad")

# Perfiles ya escritos con un filtro, por persona: en una corrida cada persona se repite en cada variante.
PERFILES_GUARDADOS = 60_000
_perfiles: OrderedDict[tuple[str, frozenset], dict] = OrderedDict()
_cerrojo = threading.Lock()


def cfg_local(url: str, temperatura: float) -> dict:
    """Lo que necesita `banco.encuestar` para preguntar al modelo local, una persona por llamada."""
    return {**CFG, "control": True, "url": url, "temperatura": temperatura, "logprobs": False}


@functools.lru_cache(maxsize=256)
def datos_de(politica: str) -> frozenset | None:
    """Los datos del perfil que se entregan para esta política; None es el perfil completo."""
    datos = filtro.datos_para(politica, NIVEL)
    if CON_IDENTIDAD:
        return datos
    # El perfil completo es None (sin filtro): para quitarle algo hay que nombrar todo lo demás.
    return frozenset((datos if datos is not None else frozenset(filtro.DATOS)) - IDENTIDAD_POLITICA)


def temas_de(politica: str) -> list[str]:
    """Los temas que el filtro detecta en la política, si el nivel los usa."""
    return filtro.temas_de(politica) if NIVEL == "tematico" else []


@functools.lru_cache(maxsize=1)
def redactor():
    """(módulo que escribe los perfiles, etiquetas, secciones).

    Ese script necesita DuckDB, así que se carga solo cuando hay tabla de agentes."""
    perfiles = _cargar("personas_muestra")
    return perfiles, perfiles.cargar_etiquetas(), list(perfiles.SECCIONES)


def perfil_de(agente, datos: frozenset | None = None) -> dict:
    """El perfil por secciones con solo los datos pedidos.

    Sin filtro va el completo. También cuando el agente no trae su fila de la tabla (los del
    archivo fijo de respaldo vienen con el perfil ya escrito): no hay con qué reescribirlo."""
    if datos is None or agente.fila is None:
        return agente.perfil
    clave = (agente.id, datos)
    with _cerrojo:
        if clave in _perfiles:
            _perfiles.move_to_end(clave)
            return _perfiles[clave]
    perfiles, etiquetas, secciones = redactor()
    escrito, _ = perfiles.describir(agente.fila, etiquetas, secciones, con_cep=True, datos=datos)
    with _cerrojo:
        _perfiles[clave] = escrito
        while len(_perfiles) > PERFILES_GUARDADOS:
            _perfiles.popitem(last=False)
    return escrito


def persona_de(agente, datos: frozenset | None = None) -> dict:
    """El agente en la forma que esperan las funciones del banco de pruebas."""
    return {"id": agente.id, "perfil": perfil_de(agente, datos)}


def sistema_del_banco(politica: str) -> str:
    """El mensaje de sistema con las cinco preguntas del banco tal cual, sin la redacción de apoyo del
    servidor. Es con el que se corrieron los benchmarks guardados (scripts/benchmark_indecision_luna.py)."""
    return banco.mensajes(politica, {}, CFG)[0]["content"]


def sistema_con_politica(politica: str) -> str:
    """Mensaje de sistema tal como lo arma el banco: instrucciones, tema y preguntas con su escala."""
    sistema = sistema_del_banco(politica)
    # La pregunta de apoyo va al final del mensaje, después del tema: se cambia ahí y no en el texto de la propuesta.
    cabeza, marca, cola = sistema.rpartition("# Preguntas")
    return cabeza + marca + cola.replace(APOYO_BANCO, APOYO, 1)


#: Todo lo que el banco le dice al modelo además del tema: si cambia, la caché no se reutiliza.
VERSION: str = sistema_con_politica("")


def perfil(agente, datos: frozenset | None = None) -> str:
    """El perfil que lee el modelo: el texto del banco, una línea por sección."""
    return banco.prosa_de(persona_de(agente, datos)) or ""
