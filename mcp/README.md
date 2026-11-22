# What If Chile MCP

El MCP prepara simulaciones de What If Chile para que Claude Code u otro cliente compatible ejecute los lotes con su propio modelo. El servidor elige la muestra, valida las respuestas y guarda la corrida. El registro de la URL se hace sin proporcionar claves ni tokens de IA.

## Conexión rápida en local

Desde la raíz del repositorio, con Python 3.14 y uv:

```sh
uv sync --project mcp --locked
uv run --directory mcp --locked --no-sync -m whatif_mcp
```

En otra terminal:

```sh
claude mcp add --transport http whatif-chile http://127.0.0.1:8788/mcp
```

En Claude Code, comprueba la conexión con `/mcp` y pide una primera simulación. El modo aislado tiene su propio historial. La URL pública está pendiente de activar en un host dedicado.

Consulta el [índice de documentación](../docs/mcp/README.md) para ver la guía de conexión, arquitectura, protocolo, privacidad y operación.
