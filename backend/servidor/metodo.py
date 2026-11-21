"""El método de encuesta es el de `scripts/probar_modelo.py` (Alonso): mismas instrucciones,
mismas preguntas y mismo perfil. Aquí solo se importa, para que lo que él cambie allá sea lo
que usa el servidor, sin copias que se desalineen.

Lo que el servidor fija del banco de pruebas:
- Redacción 1 de las instrucciones y las preguntas en su orden.
- El perfil general en prosa, por secciones (`scripts/personas_muestra.py`).
- Sin pregunta de control cuando responde Claude: ahí la primera respuesta sí depende del
  perfil. El modelo local la lleva, como en el banco (`CFG_LOCAL`).
"""

import importlib.util
from pathlib import Path

_RUTA = Path(__file__).resolve().parent.parent / "scripts" / "probar_modelo.py"
_spec = importlib.util.spec_from_file_location("probar_modelo", _RUTA)
banco = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(banco)

PREGUNTAS: list[str] = banco.PREGUNTAS
CLAVES: list[str] = banco.CLAVES

#: Cómo arma el banco los mensajes cuando responde Claude, en lotes.
CFG = {"orden": list(range(len(CLAVES))), "control": False, "etiqueta": None, "redaccion": 1, "perfil": "prosa"}


def cfg_local(url: str, temperatura: float) -> dict:
    """Lo que necesita `banco.encuestar` para preguntar al modelo local, una persona por llamada."""
    return {**CFG, "control": True, "url": url, "temperatura": temperatura, "logprobs": False}


def persona_de(agente) -> dict:
    """El agente en la forma que esperan las funciones del banco de pruebas."""
    return {"id": agente.id, "perfil": agente.perfil}


def sistema_con_politica(politica: str) -> str:
    """Mensaje de sistema tal como lo arma el banco: instrucciones, tema y preguntas."""
    return banco.mensajes(politica, {}, CFG)[0]["content"]


#: Todo lo que el banco le dice al modelo además del tema: si cambia, la caché no se reutiliza.
VERSION: str = sistema_con_politica("")


def perfil(agente) -> str:
    """El perfil que lee el modelo: el texto del banco, una línea por sección."""
    return banco.prosa_de(persona_de(agente)) or ""
