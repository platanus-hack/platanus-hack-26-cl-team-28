"""Motores que hacen responder a los agentes.

El método es el de `scripts/probar_modelo.py` (ver `metodo.py`): cada persona responde las
mismas cinco preguntas con un entero de 1 a 7, sin texto. Lo que cambia entre motores es quién
contesta:

- `LlamaLocal`: el servidor llama-server del banco de pruebas, una persona por llamada, con la
  misma función `encuestar` del script. Se usa si `LLAMA_URL` está definida.
- `ClaudeApi`: Claude Haiku por la API de Anthropic (`ANTHROPIC_API_KEY`).
- `ClaudeCodigo`: Claude Haiku por la CLI de Claude Code (`claude -p`).
- `Grabado`: repite respuestas reales guardadas en `data/pruebas/`.

Con Claude las personas van en lotes (`LOTE` por llamada, como en las pruebas con subagentes);
`LOTE=1` pregunta de a una. Las frases que muestra la interfaz no son parte de la encuesta: se
piden después, en una llamada aparte, a unas pocas personas que ya respondieron (`comentar`).
"""

import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import metodo
from .agentes import Agente

N = len(metodo.CLAVES)

ESQUEMA_LOTE = {
    "type": "object",
    "properties": {
        "r": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer"},
                    "p": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["i", "p"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["r"],
    "additionalProperties": False,
}

# Lo único que se agrega a las instrucciones del banco: que vienen varias personas juntas.
INSTRUCCION_LOTE = (
    "Vienen varias personas, numeradas. Responde la encuesta por separado como cada una de ellas, "
    f"sin que una influya en otra. Para cada persona devuelve `i` (su número) y `p` (sus {N} "
    "respuestas, enteros de 1 a 7, en el orden de las preguntas)."
)

SISTEMA_VOCES = (
    "Estas personas ya contestaron una encuesta sobre una política pública en Chile. Sus respuestas "
    "están dadas y no se cambian. Para cada una, escribe la frase con que le explicaría a la "
    "encuestadora su respuesta a la primera pregunta: en primera persona, con su voz y su motivo "
    "concreto según su perfil, en máximo 14 palabras."
)

ESQUEMA_VOCES = {
    "type": "object",
    "properties": {
        "r": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"i": {"type": "integer"}, "f": {"type": "string"}},
                "required": ["i", "f"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["r"],
    "additionalProperties": False,
}


@dataclass
class Consumo:
    llamadas: int = 0
    costo_usd: float = 0.0
    tokens_entrada: int = 0
    tokens_salida: int = 0

    def sumar(self, otro: "Consumo") -> None:
        self.llamadas += otro.llamadas
        self.costo_usd += otro.costo_usd
        self.tokens_entrada += otro.tokens_entrada
        self.tokens_salida += otro.tokens_salida


@dataclass
class Respuesta:
    agente: int
    #: Una nota de 1 a 7 por cada pregunta del banco, en su orden.
    respuestas: list[int]
    #: Frase pedida aparte, después de responder; vacía si no se le pidió.
    frase: str = ""

    @property
    def acuerdo(self) -> int:
        """La primera pregunta: si está de acuerdo con que se implemente la política."""
        return self.respuestas[0]


@dataclass
class ResultadoLote:
    respuestas: list[Respuesta]
    consumo: Consumo = field(default_factory=Consumo)


def prompt_lote(agentes: list[Agente]) -> str:
    personas = "\n\n".join(f"## Persona {k}\n\n{metodo.perfil(agente)}" for k, agente in enumerate(agentes))
    return f"{INSTRUCCION_LOTE}\n\n{personas}"


def notas_validas(notas) -> bool:
    return isinstance(notas, list) and len(notas) == N and all(type(v) is int and 1 <= v <= 7 for v in notas)


def leer_lote(datos: dict, agentes: list[Agente]) -> list[Respuesta]:
    respuestas, vistos = [], set()
    for fila in datos.get("r", []):
        k = fila.get("i")
        if not isinstance(k, int) or not 0 <= k < len(agentes) or k in vistos or not notas_validas(fila.get("p")):
            continue
        vistos.add(k)
        respuestas.append(Respuesta(agentes[k].indice, fila["p"]))
    return respuestas


def prompt_voces(politica: str, pares: list[tuple[Agente, Respuesta]]) -> str:
    preguntas = "\n".join(f"{k}. {texto}" for k, texto in enumerate(metodo.PREGUNTAS, start=1))
    personas = "\n\n".join(
        f"## Persona {k}\n\n{metodo.perfil(agente)}\n- Sus respuestas (1 a 7, en el orden de las preguntas): {respuesta.respuestas}"
        for k, (agente, respuesta) in enumerate(pares)
    )
    return f"# Política\n\n{politica.strip()}\n\n# Preguntas\n\n{preguntas}\n\n{personas}\n\nDevuelve `i` (número de la persona) y `f` (su frase)."


def leer_voces(datos: dict, pares: list[tuple[Agente, Respuesta]]) -> list[tuple[int, str]]:
    salida = []
    for fila in datos.get("r", []):
        k, frase = fila.get("i"), str(fila.get("f", "")).strip()[:160]
        if isinstance(k, int) and 0 <= k < len(pares) and frase:
            salida.append((pares[k][0].indice, frase))
    return salida


class Motor:
    nombre = "motor"
    modelo = ""
    grabado = False

    def responder(self, politica: str, agentes: list[Agente]) -> ResultadoLote:
        raise NotImplementedError

    def redactar(self, sistema: str, prompt: str, esquema: dict) -> tuple[dict, Consumo]:
        raise NotImplementedError

    def comentar(self, politica: str, pares: list[tuple[Agente, Respuesta]]) -> tuple[list[tuple[int, str]], Consumo]:
        """Frases de personas que ya respondieron. Por defecto, ninguna: no todos los motores escriben."""
        return [], Consumo()

    def describir(self) -> dict:
        return {"nombre": self.nombre, "modelo": self.modelo, "grabado": self.grabado}

    @property
    def clave(self) -> str:
        """Modelo más versión de las instrucciones: si cambia el prompt, la caché no se reutiliza."""
        version = hashlib.sha256((metodo.SISTEMA + "".join(metodo.PREGUNTAS) + INSTRUCCION_LOTE).encode()).hexdigest()[:8]
        return f"{self.modelo}:{version}"


class ClaudeCodigo(Motor):
    """Haiku por la CLI de Claude Code. Cada lote es un proceso `claude -p` aparte."""

    nombre = "Claude Code"

    def __init__(self, modelo: str = "haiku", modelo_redaccion: str = "sonnet", espera: int = 150):
        self.modelo = f"claude-{modelo}" if not modelo.startswith("claude") else modelo
        self._modelo = modelo
        self._redaccion = modelo_redaccion
        self._espera = espera
        # Carpeta vacía para que la CLI no cargue instrucciones de ningún proyecto.
        self._carpeta = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ph26-agentes"
        self._carpeta.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def disponible() -> bool:
        return shutil.which("claude") is not None

    def _llamar(self, modelo: str, sistema: str, prompt: str, esquema: dict) -> tuple[dict, Consumo]:
        orden = [
            "claude", "-p", "--model", modelo,
            "--setting-sources", "", "--strict-mcp-config", "--tools", "",
            "--no-session-persistence", "--output-format", "json",
            "--system-prompt", sistema, "--json-schema", json.dumps(esquema),
        ]
        # El prompt va por la entrada estándar: una ley completa no cabe como argumento de un proceso.
        salida = subprocess.run(
            orden, cwd=self._carpeta, input=prompt, capture_output=True,
            text=True, timeout=self._espera, check=False,
        )
        datos = json.loads(salida.stdout or "{}")
        if datos.get("is_error") or "structured_output" not in datos:
            raise RuntimeError(f"La CLI de Claude no respondió: {datos.get('terminal_reason') or salida.stderr[:200]}")
        uso = datos.get("usage", {})
        consumo = Consumo(
            llamadas=1,
            costo_usd=float(datos.get("total_cost_usd") or 0),
            tokens_entrada=int(uso.get("input_tokens") or 0)
            + int(uso.get("cache_read_input_tokens") or 0)
            + int(uso.get("cache_creation_input_tokens") or 0),
            tokens_salida=int(uso.get("output_tokens") or 0),
        )
        return datos["structured_output"], consumo

    def responder(self, politica, agentes):
        datos, consumo = self._llamar(self._modelo, metodo.sistema_con_politica(politica), prompt_lote(agentes), ESQUEMA_LOTE)
        return ResultadoLote(leer_lote(datos, agentes), consumo)

    def comentar(self, politica, pares):
        datos, consumo = self._llamar(self._modelo, SISTEMA_VOCES, prompt_voces(politica, pares), ESQUEMA_VOCES)
        return leer_voces(datos, pares), consumo

    def redactar(self, sistema, prompt, esquema):
        return self._llamar(self._redaccion, sistema, prompt, esquema)


class ClaudeApi(Motor):
    """Haiku 5.5 por la API de Anthropic, sin razonamiento previo para que cada lote tarde segundos."""

    nombre = "API de Anthropic"
    # Precios por millón de tokens de Haiku 5.5 (prompts de hasta 100 mil tokens).
    PRECIO_ENTRADA = 0.10
    PRECIO_SALIDA = 0.50

    def __init__(self, modelo: str = "claude-haiku-5-5", modelo_redaccion: str = "claude-sonnet-5-5"):
        import anthropic  # solo se necesita si hay clave

        self.modelo = modelo
        self._redaccion = modelo_redaccion
        self._cliente = anthropic.Anthropic()

    @staticmethod
    def disponible() -> bool:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def _llamar(self, modelo: str, sistema: str, prompt: str, esquema: dict, rapido: bool) -> tuple[dict, Consumo]:
        extra = {"thinking": {"type": "disabled"}, "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": esquema}}}
        if not rapido:
            extra = {"output_config": {"effort": "medium", "format": {"type": "json_schema", "schema": esquema}}}
        respuesta = self._cliente.messages.create(
            model=modelo,
            max_tokens=16000,
            system=[{"type": "text", "text": sistema}],
            messages=[{"role": "user", "content": prompt}],
            **extra,
        )
        texto = "".join(bloque.text for bloque in respuesta.content if bloque.type == "text")
        uso = respuesta.usage
        entrada = (uso.input_tokens or 0) + (uso.cache_read_input_tokens or 0) + (uso.cache_creation_input_tokens or 0)
        consumo = Consumo(
            llamadas=1,
            costo_usd=(entrada * self.PRECIO_ENTRADA + uso.output_tokens * self.PRECIO_SALIDA) / 1e6,
            tokens_entrada=entrada,
            tokens_salida=uso.output_tokens,
        )
        return json.loads(texto), consumo

    def responder(self, politica, agentes):
        datos, consumo = self._llamar(self.modelo, metodo.sistema_con_politica(politica), prompt_lote(agentes), ESQUEMA_LOTE, rapido=True)
        return ResultadoLote(leer_lote(datos, agentes), consumo)

    def comentar(self, politica, pares):
        datos, consumo = self._llamar(self.modelo, SISTEMA_VOCES, prompt_voces(politica, pares), ESQUEMA_VOCES, rapido=True)
        return leer_voces(datos, pares), consumo

    def redactar(self, sistema, prompt, esquema):
        return self._llamar(self._redaccion, sistema, prompt, esquema, rapido=False)


class Grabado(Motor):
    """Repite una corrida real ya hecha. Para cualquier política responde lo grabado de sala cuna."""

    nombre = "Corrida grabada"
    grabado = True
    ARCHIVO = Path(__file__).resolve().parent.parent / "data" / "pruebas" / "sala_cuna" / "resultados_haiku55_2000_20x100.jsonl"

    def __init__(self, agentes: list[Agente], pausa: float = 0.6):
        por_id = {agente.id: agente.indice for agente in agentes}
        self._acuerdo: dict[int, list[int]] = {}
        with open(self.ARCHIVO, encoding="utf-8") as f:
            for linea in f:
                fila = json.loads(linea)
                if fila.get("valida") and fila["id"] in por_id:
                    self._acuerdo[por_id[fila["id"]]] = [fila["respuestas"][clave] for clave in metodo.CLAVES]
        self.modelo = "claude-haiku-5-5 (grabado)"
        self._pausa = pausa

    def responder(self, politica, agentes):
        time.sleep(self._pausa)
        respuestas = [Respuesta(a.indice, self._acuerdo[a.indice]) for a in agentes if a.indice in self._acuerdo]
        return ResultadoLote(respuestas, Consumo())

    def redactar(self, sistema, prompt, esquema):
        raise RuntimeError("La corrida grabada no redacta variantes nuevas")


class LlamaLocal(Motor):
    """El servidor llama-server del banco de pruebas: una persona por llamada, con su misma función."""

    nombre = "Modelo local"

    def __init__(self, url: str):
        self._url = url.rstrip("/")
        modelo = metodo.banco.pedir(f"{self._url}/v1/models", espera=10)["data"][0]["id"]
        self.modelo = Path(modelo).name.removesuffix(".gguf")
        self._temperatura = float(os.environ.get("TEMPERATURA", "1.0"))

    def responder(self, politica, agentes):
        respuestas = []
        for agente in agentes:
            registro = metodo.banco.encuestar(self._url, politica, metodo.persona_de(agente), agente.indice, self._temperatura, logprobs=False)
            if registro["valida"]:
                respuestas.append(Respuesta(agente.indice, [registro["respuestas"][clave] for clave in metodo.CLAVES]))
        return ResultadoLote(respuestas, Consumo(llamadas=len(agentes)))

    def redactar(self, sistema, prompt, esquema):
        raise RuntimeError("El modelo local solo responde la encuesta; para iteraciones hace falta Claude")


def elegir_motor(agentes: list[Agente]) -> Motor:
    """`MOTOR` en el entorno fuerza uno (api, claude, grabado); si no, el mejor disponible."""
    pedido = os.environ.get("MOTOR", "").lower()
    if pedido == "grabado":
        return Grabado(agentes)
    if os.environ.get("LLAMA_URL") and pedido in ("", "local"):
        return LlamaLocal(os.environ["LLAMA_URL"])
    if pedido in ("", "api") and ClaudeApi.disponible():
        return ClaudeApi()
    if pedido in ("", "claude") and ClaudeCodigo.disponible():
        return ClaudeCodigo()
    return Grabado(agentes)
