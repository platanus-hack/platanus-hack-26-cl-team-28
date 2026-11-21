"""Motores que hacen responder a los agentes.

- `ClaudeCodigo`: llama a Haiku por la CLI de Claude Code (`claude -p`), con la sesión del
  equipo. Es lo que corre en un PC de desarrollo sin clave de API.
- `ClaudeApi`: llama a la API de Anthropic con `ANTHROPIC_API_KEY`; sin razonamiento previo
  responde varias veces más rápido. Es el que corresponde a un despliegue.
- `Grabado`: repite respuestas reales guardadas en `data/pruebas/` (Haiku 5.5 sobre los mismos
  2.000 agentes y la política de sala cuna). Sirve sin red y se rotula como corrida grabada.

Cada motor recibe una política y un lote de agentes y devuelve, por agente, su acuerdo de 1 a 7
y una frase en primera persona.
"""

import hashlib
import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .agentes import Agente

SISTEMA = (
    "Simulas una encuesta a personas reales que viven en Chile. Para cada perfil, ponte en el lugar "
    "de esa persona (su situación, sus intereses, su forma de pensar) y responde como ella, no como "
    "un asistente ni como un experto neutral. Las personas reales difieren entre sí: usa toda la "
    "escala cuando el perfil lo justifique.\n\n"
    "Contesta como esa persona le contestaría a una encuestadora: aunque la propuesta no la afecte "
    "directamente, igual tiene una opinión sobre si le parece bien o mal (por lo que cree justo, "
    "por lo que le pasa a otros, por cómo ve al gobierno o a las empresas). Que no le toque no "
    "significa estar en desacuerdo. El 4 es solo para quien de verdad no sabe o le da lo mismo.\n\n"
    "Usa los valores y preocupaciones que de verdad tiene la gente con ese perfil en el Chile de "
    "hoy, no los tuyos: mucha gente prioriza la seguridad, el orden y el castigo al delito, "
    "desconfía de los políticos y de las grandes empresas, y mira primero su bolsillo."
)

ESQUEMA_LOTE = {
    "type": "object",
    "properties": {
        "r": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer"},
                    "a": {"type": "integer"},
                    "f": {"type": "string"},
                },
                "required": ["i", "a", "f"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["r"],
    "additionalProperties": False,
}

INSTRUCCION_LOTE = (
    "Para cada persona devuelve: i (su número en la lista), a (qué tan de acuerdo está con esta "
    "propuesta, de 1 = totalmente en desacuerdo a 7 = totalmente de "
    "acuerdo) y f (una frase de esa persona, en primera persona, de máximo 14 palabras, con su voz "
    "y su motivo concreto)."
)


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
    acuerdo: int
    frase: str


@dataclass
class ResultadoLote:
    respuestas: list[Respuesta]
    consumo: Consumo = field(default_factory=Consumo)


def prompt_lote(politica: str, agentes: list[Agente]) -> str:
    personas = "\n".join(f"{k}. {agente.perfil()}" for k, agente in enumerate(agentes))
    return f"# Política\n\n{politica.strip()}\n\n# Personas\n\n{personas}\n\n{INSTRUCCION_LOTE}"


def leer_lote(datos: dict, agentes: list[Agente]) -> list[Respuesta]:
    respuestas, vistos = [], set()
    for fila in datos.get("r", []):
        k, acuerdo = fila.get("i"), fila.get("a")
        if not isinstance(k, int) or not 0 <= k < len(agentes) or k in vistos:
            continue
        if not isinstance(acuerdo, int) or not 1 <= acuerdo <= 7:
            continue
        vistos.add(k)
        respuestas.append(Respuesta(agentes[k].indice, acuerdo, str(fila.get("f", "")).strip()[:160]))
    return respuestas


class Motor:
    nombre = "motor"
    modelo = ""
    grabado = False

    def responder(self, politica: str, agentes: list[Agente]) -> ResultadoLote:
        raise NotImplementedError

    def redactar(self, sistema: str, prompt: str, esquema: dict) -> tuple[dict, Consumo]:
        raise NotImplementedError

    def describir(self) -> dict:
        return {"nombre": self.nombre, "modelo": self.modelo, "grabado": self.grabado}

    @property
    def clave(self) -> str:
        """Modelo más versión de las instrucciones: si cambia el prompt, la caché no se reutiliza."""
        version = hashlib.sha256((SISTEMA + INSTRUCCION_LOTE).encode()).hexdigest()[:8]
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
        datos, consumo = self._llamar(self._modelo, SISTEMA, prompt_lote(politica, agentes), ESQUEMA_LOTE)
        return ResultadoLote(leer_lote(datos, agentes), consumo)

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
        datos, consumo = self._llamar(self.modelo, SISTEMA, prompt_lote(politica, agentes), ESQUEMA_LOTE, rapido=True)
        return ResultadoLote(leer_lote(datos, agentes), consumo)

    def redactar(self, sistema, prompt, esquema):
        return self._llamar(self._redaccion, sistema, prompt, esquema, rapido=False)


class Grabado(Motor):
    """Repite una corrida real ya hecha. Para cualquier política responde lo grabado de sala cuna."""

    nombre = "Corrida grabada"
    grabado = True
    ARCHIVO = Path(__file__).resolve().parent.parent / "data" / "pruebas" / "sala_cuna" / "resultados_haiku55_2000_20x100.jsonl"

    def __init__(self, agentes: list[Agente], pausa: float = 0.6):
        por_id = {agente.id: agente.indice for agente in agentes}
        self._acuerdo: dict[int, int] = {}
        with open(self.ARCHIVO, encoding="utf-8") as f:
            for linea in f:
                fila = json.loads(linea)
                if fila.get("valida") and fila["id"] in por_id:
                    self._acuerdo[por_id[fila["id"]]] = fila["respuestas"]["p1"]
        self.modelo = "claude-haiku-5-5 (grabado)"
        self._pausa = pausa

    def responder(self, politica, agentes):
        time.sleep(self._pausa)
        respuestas = [Respuesta(a.indice, self._acuerdo[a.indice], "") for a in agentes if a.indice in self._acuerdo]
        return ResultadoLote(respuestas, Consumo())

    def redactar(self, sistema, prompt, esquema):
        raise RuntimeError("La corrida grabada no redacta variantes nuevas")


def elegir_motor(agentes: list[Agente]) -> Motor:
    """`MOTOR` en el entorno fuerza uno (api, claude, grabado); si no, el mejor disponible."""
    pedido = os.environ.get("MOTOR", "").lower()
    if pedido == "grabado":
        return Grabado(agentes)
    if pedido in ("", "api") and ClaudeApi.disponible():
        return ClaudeApi()
    if pedido in ("", "claude") and ClaudeCodigo.disponible():
        return ClaudeCodigo()
    return Grabado(agentes)
