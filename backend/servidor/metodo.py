"""El método de encuesta es el de `scripts/probar_modelo.py` (Alonso): mismas instrucciones,
mismas cinco preguntas y mismo formato de perfil. Aquí solo se importa, para que lo que él cambie
allá sea lo que usa el servidor, sin copias que se desalineen.
"""

import importlib.util
from pathlib import Path

_RUTA = Path(__file__).resolve().parent.parent / "scripts" / "probar_modelo.py"
_spec = importlib.util.spec_from_file_location("probar_modelo", _RUTA)
banco = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(banco)

SISTEMA: str = banco.SISTEMA
PREGUNTAS: list[str] = banco.PREGUNTAS
CLAVES: list[str] = banco.CLAVES


def persona_de(agente) -> dict:
    """El agente en la forma que esperan las funciones del banco de pruebas."""
    return {"id": agente.id, "atributos": agente.atributos}


def sistema_con_politica(politica: str) -> str:
    """Mensaje de sistema tal como lo arma el banco: instrucciones, política y preguntas."""
    return banco.mensajes(politica, {"atributos": {}})[0]["content"]


def perfil(agente) -> str:
    """El perfil con el mismo formato del banco: una línea `- clave: valor` por atributo."""
    return "\n".join(f"- {clave}: {valor}" for clave, valor in banco.atributos(persona_de(agente)).items())
