# 1. Conexión y primera simulación

[Índice](README.md)

## 1.1 Claude Code

Abre Claude Code con tu cuenta habitual. Asigna a `URL_DEL_MCP` la URL HTTPS completa publicada por What If Chile, incluida la ruta `/mcp`.

```sh
claude mcp add --transport http whatif-chile "$URL_DEL_MCP"
```

En la sesión escribe `/mcp` y comprueba que `whatif-chile` esté conectado. Si estás desarrollando en el repositorio, el [arranque local](05-operacion-y-pruebas.md#51-arranque-local) deja el servicio en `http://127.0.0.1:8788/mcp`.

> Usa What If Chile para simular con 10 agentes una propuesta para extender el subsidio al transporte público rural. Confirma conmigo antes de iniciar y muéstrame el resultado por variante.

Al confirmar, autorizas el uso de tu sesión de IA y el guardado de la propuesta y sus resultados en el historial del MCP. Claude Code puede lanzar subagentes para resolver la encuesta, las voces y las reformulaciones. La sesión devuelve el identificador de la corrida y sus resultados. El acceso de la corrida debe permanecer en la sesión o en un lugar privado. [Documentación de Claude Code sobre MCP](https://code.claude.com/docs/en/mcp).

## 1.2 Otros clientes MCP

Configura la URL como servidor remoto con transporte **Streamable HTTP**. El registro del servidor y el descubrimiento de herramientas se hacen sin una clave de API. Para simular, el cliente debe poder interpretar los lotes devueltos por `trabajo`, resolverlos con su modelo y entregar el JSON de respuesta. Un cliente con subagentes puede delegar los lotes. Uno con un solo modelo puede resolverlos en la conversación principal. El [contrato](03-protocolo-y-flujos.md) muestra el ciclo completo.

## 1.3 Texto para la ayuda de la web

La integración propuesta es un botón **MCP** encima del control de tema. El panel puede ofrecer el comando, la URL y el ejemplo de simulación, con botones para copiarlos. Antes de habilitar la URL pública, indica que la conexión pública todavía está pendiente y muestra el comando al confirmar un endpoint operativo. El panel debe indicar que los resultados de las corridas del servicio aislado se consultan desde el cliente MCP.

El registro como MCP solo configura la URL. Para ejecutar una simulación no se le pide al usuario que copie, genere ni comparta una credencial de IA.
