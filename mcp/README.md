# What If Chile MCP

Una sesión de Claude Code puede simular propuestas sobre la población sintética de What If Chile. El servidor elige la muestra, organiza los lotes, valida las respuestas y guarda la corrida. Los subagentes de la sesión del usuario hacen la inferencia con el plan o proveedor que esa sesión ya usa.

## Conexión

Inicia sesión en Claude Code de la manera habitual. Agrega la URL HTTPS del MCP como cualquier otro servidor remoto:

```sh
claude mcp add --transport http whatif-chile https://<dominio-del-mcp>/mcp
```

Usa `/mcp` para comprobar la conexión. Por ejemplo, pide: «Usa What If Chile para simular con 10 agentes una propuesta de extensión del subsidio al transporte rural». El servidor MCP carece de acceso a la sesión y a las credenciales de Claude Code. La conexión también funciona con otro cliente Streamable HTTP capaz de resolver los lotes y devolver su JSON. [Documentación de conexión de Claude Code](https://code.claude.com/docs/en/mcp).

| Herramienta | Uso |
|---|---|
| `estado` | Lista tamaños, filtros, preguntas y visibilidad del historial. |
| `simular` | Crea la corrida con una o más propuestas, filtros e iteraciones opcionales. Devuelve `id` y `acceso`. |
| `trabajo` | Entrega salidas de lotes resueltos y obtiene lotes siguientes de encuesta, voces o redacción. |
| `consultar` | Devuelve el estado y los resultados agregados de una corrida. |
| `cancelar` | Libera los lotes pendientes. El cliente gestiona los subagentes que ya inició. |

El cliente confirma con la persona el tamaño de la muestra, el uso de su sesión y el guardado de la propuesta y resultados. Guarda el `acceso` de la corrida para `trabajo`, `consultar` y `cancelar`. Si falla la llamada inicial, reenvíala con el mismo UUID v4 aleatorio. Los recibos viven una hora en el proceso. Reenviar un lote aceptado es seguro.

`trabajo` devuelve la entrada pública y el esquema de salida de cada lote. En Claude Code la sesión puede delegar varios lotes a la vez con `Agent`, usando Haiku para encuestas y voces o Sonnet para reformulaciones. El servidor maneja hasta seis lotes por entrega y la sesión puede continuar en tandas. Si el cliente solo tiene el modelo de la conversación, puede responder esos mismos lotes directamente. Si una corrida queda sin contacto durante tres minutos, se libera. El plazo máximo de una corrida es 30 minutos.

## Privacidad y resultados

Los lotes llevan el texto de la propuesta, la encuesta y los rasgos sintéticos que la web ya muestra para cada persona. Las instrucciones privadas del motor web, los pesos del muestreo, las coordenadas, los identificadores de perfiles y el catálogo completo quedan en el servidor. Los usuarios de un cliente pueden ver los lotes que procesan.

Ambos canales reutilizan el muestreo, el orden de la encuesta, el formato de vistas y el guardado del backend. El modelo y el contexto se deciden en el cliente, así que las notas pueden diferir de la simulación web. El historial etiqueta estas corridas como resultados declarados por el cliente. El MCP conoce el número de lotes aceptados y el tiempo de la corrida. El uso de tokens, el costo y la procedencia efectiva de las respuestas solo los conoce el cliente. Los campos de tokens y costo de la vista heredada quedan en cero.

## Ejecutar y probar localmente

Desde la raíz del repositorio, con Python 3.14 y uv:

```sh
uv sync --project mcp --locked
uv run --directory mcp --locked --no-sync -m whatif_mcp
claude mcp add --transport http whatif-chile http://127.0.0.1:8788/mcp
```

El modo predeterminado escucha en loopback y escribe solo en `WHATIF_MCP_DATA` o `~/.local/state/whatif-mcp`. En una copia de desarrollo se puede usar `MOTOR=claude uv run --directory mcp --locked --no-sync -m whatif_mcp --con-web` para probar el historial navegable en una API web local. Esta opción necesita la configuración habitual del backend y usa el historial de esa copia. En el servicio aislado las corridas no entran al historial de la web pública. El backend publicado carga su historial en memoria y requiere una integración propia para recibir corridas de otro proceso.

```sh
PYTHONPATH=backend:mcp uv run --project mcp --locked \
  python -m unittest discover -s mcp/tests -v
```

Las pruebas de integración usan el transporte real, respuestas de cliente simuladas, la población del repositorio y un historial temporal. Comprueban validación, aislamiento, reintentos, cancelación, inactividad y reapertura desde la API web local.

## Servicio y Actions

El [workflow dedicado](../.github/workflows/mcp.yml) ejecuta la integración y arranca el contenedor en CI. Su ejecución manual publica una imagen de GHCR identificada por SHA. El parámetro `desplegar` promueve el digest probado a un host exclusivo del MCP mediante el entorno `mcp-production`. La web y su workflow conservan su despliegue actual.

Para habilitar el destino independiente, instala Docker Compose en el host dedicado y coloca [compose.yml](despliegue/compose.yml) en `~/whatif-mcp/`. Crea allí `servicio.env` con `WHATIF_MCP_HOST` (solo el dominio) y `WHATIF_MCP_SECRET` (un secreto aleatorio de al menos 32 caracteres que permite conservar accesos tras reinicios). El [Caddyfile dedicado](despliegue/whatif-mcp.caddy) sirve TLS en ese dominio y apunta al puerto local 8788. El host necesita permiso de lectura en GHCR si la imagen es privada.

Configura los secretos `WHATIF_MCP_SSH_TARGET` (`usuario@host`), `WHATIF_MCP_SSH_KEY` y `WHATIF_MCP_KNOWN_HOSTS` en `mcp-production`. Configura el acceso a ese entorno para quienes pueden desplegar. El despliegue conserva el volumen de historial y repone el digest anterior si falla la salud de la nueva versión. El stack y el proxy del MCP deben operar en el host dedicado.
