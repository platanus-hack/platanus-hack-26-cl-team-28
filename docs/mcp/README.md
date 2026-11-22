# Documentación del MCP de What If Chile

What If Chile puede simular propuestas desde Claude Code y otros clientes MCP. El servidor selecciona la muestra y organiza la corrida. El cliente ejecuta cada lote con el modelo de su sesión y devuelve sus respuestas para validarlas y guardarlas.

| Campo | Valor |
|---|---|
| Proyecto | What If Chile, equipo 28 de Platanus Hack 2026 |
| Alcance | `mcp/`, workflow propio de GitHub Actions y reutilización del motor en `backend/servidor/` |
| Implementación de referencia | `fa9dca0`, probada localmente y en GitHub Actions |
| Disponibilidad | Servicio ejecutable en local. La URL pública requiere activar el despliegue en un host dedicado |
| Transporte | MCP Streamable HTTP en `/mcp` |

## Mapa de lectura

| Documento | Responde |
|---|---|
| [1. Conexión y primera simulación](01-conexion.md) | Cómo agregar el MCP a Claude Code, usarlo desde otro cliente y presentar las instrucciones en la web |
| [2. Arquitectura](02-arquitectura.md) | Qué ejecuta el cliente, qué conserva el servidor y qué partes comparte con la web |
| [3. Protocolo y flujos](03-protocolo-y-flujos.md) | Herramientas, ejemplos JSON, ciclo de lotes, reintentos y estados de una corrida |
| [4. Privacidad y datos](04-privacidad-y-datos.md) | Qué viaja en cada lote, acceso a corridas, persistencia y alcance de la privacidad |
| [5. Operación y pruebas](05-operacion-y-pruebas.md) | Arranque local, topes, pruebas, Actions, publicación de imagen y reversión |

Para alguien que va a usarlo por primera vez, basta con el documento 1. Quien integra un cliente encontrará el contrato en el documento 3. La [documentación del backend](../backend/README.md) describe el motor que comparte el MCP.
