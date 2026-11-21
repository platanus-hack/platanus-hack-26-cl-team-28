"""Motores que hacen responder a los agentes.

El método es el de `scripts/probar_modelo.py` (ver `metodo.py`): cada persona responde las
mismas cinco preguntas con un entero de 1 a 7, cada una con su escala, sin texto. Lo que cambia
entre motores es quién contesta:

- `LlamaLocal`: el servidor llama-server del banco de pruebas, una persona por llamada, con la
  misma función `encuestar` del script. Se usa si `LLAMA_URL` está definida.
- `ClaudeApi`: Claude Haiku por la API de Anthropic (`ANTHROPIC_API_KEY`).
- `ClaudeCodigo`: Claude Haiku por la CLI de Claude Code (`claude -p`).

Sin ninguno de ellos el servidor no arranca: la interfaz queda en su demostración, que sortea
respuestas en el navegador. La encuesta es fija (`metodo.PREGUNTAS`): no se cambia por corrida.

Con Claude las personas van en lotes (`LOTE` por llamada, como en las pruebas con subagentes);
`LOTE=1` pregunta de a una. Las frases que muestra la interfaz no son parte de la encuesta: se
piden después, en una llamada aparte, a unas pocas personas que ya respondieron (`comentar`).

De cada persona el modelo lee el perfil filtrado: el núcleo más los datos de los temas de la
política (`metodo.datos_de`, definido en scripts/filtro_perfil.py). `PERFIL=completo` lo apaga.
"""

import hashlib
import itertools
import json
import os
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

from . import metodo
from .agentes import Agente

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

def instruccion_lote(n: int) -> str:
    """Lo único que se agrega a las instrucciones del banco: que vienen varias personas juntas."""
    return (
        "Vienen varias personas, numeradas. Responde la encuesta por separado como cada una de ellas, "
        f"sin que una influya en otra. Para cada persona devuelve `i` (su número) y `p` (sus {n} "
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


#: Cada hilo dice aquí si su llamada puede esperar (`baja = True`). Al partir una corrida se lanzan
#: cien procesos a la vez y todos compiten por la CPU: los primeros lotes, que son los que hacen
#: aparecer respuestas en pantalla, van con prioridad normal y el resto cede el paso.
PRIORIDAD = threading.local()


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
    #: Una nota de 1 a 7 por cada pregunta de la encuesta, en su orden.
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


def prompt_lote(agentes: list[Agente], datos: frozenset | None = None) -> str:
    """`datos` son los datos del perfil que van (`metodo.datos_de`); None es el perfil completo."""
    personas = "\n\n".join(f"## Persona {k}\n\n{metodo.perfil(agente, datos)}" for k, agente in enumerate(agentes))
    return f"{instruccion_lote(len(metodo.PREGUNTAS))}\n\n{personas}"


def notas_validas(notas, n: int) -> bool:
    return isinstance(notas, list) and len(notas) == n and all(type(v) is int and 1 <= v <= 7 for v in notas)


def leer_lote(datos: dict, agentes: list[Agente]) -> list[Respuesta]:
    n = len(metodo.PREGUNTAS)
    respuestas, vistos = [], set()
    for fila in datos.get("r", []):
        k = fila.get("i")
        if not isinstance(k, int) or not 0 <= k < len(agentes) or k in vistos or not notas_validas(fila.get("p"), n):
            continue
        vistos.add(k)
        respuestas.append(Respuesta(agentes[k].indice, fila["p"]))
    return respuestas


def prompt_voces(politica: str, pares: list[tuple[Agente, Respuesta]]) -> str:
    preguntas = metodo.lineas_preguntas(metodo.PREGUNTAS, metodo.ESCALAS)
    # El mismo perfil con que respondió: la frase explica esas respuestas.
    datos = metodo.datos_de(politica)
    personas = "\n\n".join(
        f"## Persona {k}\n\n{metodo.perfil(agente, datos)}\n- Sus respuestas (1 a 7, en el orden de las preguntas): {respuesta.respuestas}"
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

    def responder(self, politica: str, agentes: list[Agente]) -> ResultadoLote:
        """Una nota de 1 a 7 por cada pregunta de la encuesta, de cada agente."""
        raise NotImplementedError

    def redactar(self, sistema: str, prompt: str, esquema: dict) -> tuple[dict, Consumo]:
        raise NotImplementedError

    def comentar(self, politica: str, pares: list[tuple[Agente, Respuesta]]) -> tuple[list[tuple[int, str]], Consumo]:
        """Frases de personas que ya respondieron. Por defecto, ninguna: no todos los motores escriben."""
        return [], Consumo()

    def describir(self) -> dict:
        return {"nombre": self.nombre, "modelo": self.modelo, "perfil": metodo.NIVEL}

    def clave(self) -> str:
        """Modelo más versión de las instrucciones, de la encuesta y del filtro del perfil: si cambia
        algo de lo que lee el modelo, la caché no se reutiliza."""
        texto = metodo.VERSION + instruccion_lote(len(metodo.PREGUNTAS)) + metodo.VERSION_PERFIL
        return f"{self.modelo}:{hashlib.sha256(texto.encode()).hexdigest()[:8]}"


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
        # En un servidor sin navegador la sesión viene de tokens de `claude setup-token`. Con varios
        # (CLAUDE_TOKENS, separados por coma) las llamadas se reparten entre las cuentas, por turno.
        self._tokens = [t.strip() for t in os.environ.get("CLAUDE_TOKENS", "").split(",") if t.strip()]
        self._turno = itertools.count()

    def _entorno(self) -> dict:
        # Sin telemetría ni actualizador: cada proceso gasta un tercio menos de CPU al arrancar, y con
        # cientos de procesos a la vez la CPU es lo que limita.
        entorno = {**os.environ, "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "DISABLE_AUTOUPDATER": "1"}
        if self._tokens:
            entorno["CLAUDE_CODE_OAUTH_TOKEN"] = self._tokens[next(self._turno) % len(self._tokens)]
        return entorno

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
        if getattr(PRIORIDAD, "baja", False) and shutil.which("nice"):
            orden = ["nice", "-n", "10", *orden]
        # El prompt va por la entrada estándar: una ley completa no cabe como argumento de un proceso.
        salida = subprocess.run(
            orden, cwd=self._carpeta, input=prompt, capture_output=True,
            text=True, timeout=self._espera, check=False, env=self._entorno(),
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
        perfil = metodo.datos_de(politica)
        datos, consumo = self._llamar(self._modelo, metodo.sistema_con_politica(politica), prompt_lote(agentes, perfil), ESQUEMA_LOTE)
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
        perfil = metodo.datos_de(politica)
        datos, consumo = self._llamar(self.modelo, metodo.sistema_con_politica(politica), prompt_lote(agentes, perfil), ESQUEMA_LOTE, rapido=True)
        return ResultadoLote(leer_lote(datos, agentes), consumo)

    def comentar(self, politica, pares):
        datos, consumo = self._llamar(self.modelo, SISTEMA_VOCES, prompt_voces(politica, pares), ESQUEMA_VOCES, rapido=True)
        return leer_voces(datos, pares), consumo

    def redactar(self, sistema, prompt, esquema):
        return self._llamar(self._redaccion, sistema, prompt, esquema, rapido=False)


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
        cfg = metodo.cfg_local(self._url, self._temperatura)
        datos = metodo.datos_de(politica)
        for agente in agentes:
            registro = metodo.banco.encuestar(politica, metodo.persona_de(agente, datos), agente.indice, cfg)
            if registro["valida"]:
                respuestas.append(Respuesta(agente.indice, list(registro["respuestas"].values())))
        return ResultadoLote(respuestas, Consumo(llamadas=len(agentes)))

    def redactar(self, sistema, prompt, esquema):
        raise RuntimeError("El modelo local solo responde la encuesta; para iteraciones hace falta Claude")


def elegir_motor() -> Motor:
    """`MOTOR` en el entorno fuerza uno (local, api, claude); si no, el mejor disponible.

    Sin ninguno, el servidor no arranca: no hay respuestas guardadas que repetir."""
    pedido = os.environ.get("MOTOR", "").lower()
    if pedido not in ("", "local", "api", "claude"):
        raise SystemExit(f"MOTOR={pedido!r} no existe; los motores son local, api y claude")
    if os.environ.get("LLAMA_URL") and pedido in ("", "local"):
        return LlamaLocal(os.environ["LLAMA_URL"])
    if pedido in ("", "api") and ClaudeApi.disponible():
        return ClaudeApi()
    if pedido in ("", "claude") and ClaudeCodigo.disponible():
        return ClaudeCodigo()
    faltan = {"local": "LLAMA_URL", "api": "ANTHROPIC_API_KEY (y el paquete anthropic)", "claude": "la CLI `claude` en el PATH"}
    if pedido:
        raise SystemExit(f"El motor {pedido} no está disponible: falta {faltan[pedido]}")
    raise SystemExit("No hay con qué responder la encuesta: define LLAMA_URL o ANTHROPIC_API_KEY, o instala la CLI `claude`")
