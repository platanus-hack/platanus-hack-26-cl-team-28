# 5. Operación y pruebas

[Índice](README.md)

## 5.1 Arranque local

Usa Python 3.14 y uv desde la raíz del repositorio.

```sh
uv sync --project mcp --locked
uv run --directory mcp --locked --no-sync -m whatif_mcp
```

El servicio aislado escucha en `127.0.0.1:8788` y guarda en `~/.local/state/whatif-mcp` por defecto. La prueba de humo local comprueba el proceso, el transporte, la población y el aislamiento del historial.

```sh
python mcp/despliegue/comprobar.py http://127.0.0.1:8788
```

Para probar la reapertura en la interfaz, arranca el frontend de desarrollo y usa este comando en una copia local con el motor web configurado. `--con-web` abre la API web en `127.0.0.1:8787` y usa el historial de esa copia.

```sh
MOTOR=claude uv run --directory mcp --locked --no-sync -m whatif_mcp --con-web
```

## 5.2 Configuración y capacidad

| Variable | Valor inicial | Uso |
|---|---|---|
| `WHATIF_MCP_HOST` | `localhost` | Dominio permitido por el transporte. En despliegue usa el dominio dedicado, sin esquema ni ruta |
| `WHATIF_MCP_BIND`, `WHATIF_MCP_PORT` | `127.0.0.1`, `8788` | Dirección y puerto del MCP. Compose y su verificación de salud esperan el puerto 8788 |
| `WHATIF_MCP_PROXY` | `127.0.0.1` | Direcciones de proxies de confianza para encabezados de reenvío |
| `WHATIF_MCP_DATA` | `~/.local/state/whatif-mcp` | Directorio del historial aislado. En la imagen apunta al volumen `/var/lib/whatif-mcp` |
| `WHATIF_MCP_SECRET` | Se genera en cada arranque | Secreto del servidor, de al menos 32 caracteres si se configura. Usa uno estable en el host dedicado |
| `WHATIF_MCP_MAX_MUESTRA` | 300 | Agentes por corrida, limitado además por `MAXIMO_MUESTRA` |
| `WHATIF_MCP_LOTE` | 10 | Tamaño normal de los lotes en el proceso aislado, entre 1 y 10. El motor compartido puede usar lotes iniciales más pequeños |
| `WHATIF_MCP_CORRIDAS` y `WHATIF_MCP_CORRIDAS_POR_IP` | 4 y 2 | Corridas activas globales y por IP |
| `WHATIF_MCP_LOTES_SIMULTANEOS` | 32 | Hilos del reparto del MCP que pueden esperar resultados del cliente |

La muestra por defecto es de 10 agentes si el tope lo permite. Con los valores iniciales se admiten hasta 900 respuestas pedidas por corrida. El total se calcula multiplicando el tamaño efectivo de muestra por las variantes e iteraciones solicitadas. El proceso admite 12 inicios por minuto por dirección y ocho preparaciones simultáneas. `trabajo` admite hasta seis salidas por llamada y señala los lotes pendientes. Tras 180 segundos sin `trabajo` o 30 minutos totales, la corrida vence.

Estos números son topes de configuración. La latencia y el consumo del modelo dependen del cliente. Las pruebas disponibles no establecen rendimiento bajo carga pública.

## 5.3 Entrega y despliegue

El [workflow del MCP](../../.github/workflows/mcp.yml) verifica el protocolo y el historial y arranca un contenedor de prueba. En una ejecución manual, construye una imagen, verifica su salud y publica el SHA y el digest en GHCR. La opción `desplegar` activa el digest probado mediante el entorno `mcp-production`. El servicio tiene su propio ciclo de entrega y su propio volumen.

En el host dedicado, prepara Docker Compose y coloca [compose.yml](../../mcp/despliegue/compose.yml) en `~/whatif-mcp/`. Crea `servicio.env` junto a él con `WHATIF_MCP_HOST` y `WHATIF_MCP_SECRET`. Instala el [Caddyfile dedicado](../../mcp/despliegue/whatif-mcp.caddy) con el mismo dominio configurado en Caddy. El proxy termina TLS y publica `/mcp`. Si la imagen es privada, el host necesita acceso de lectura a GHCR.

Configura `WHATIF_MCP_SSH_TARGET` con el formato `usuario@host` y los secretos `WHATIF_MCP_SSH_KEY` y `WHATIF_MCP_KNOWN_HOSTS` en el entorno `mcp-production`. El [script de activación](../../mcp/despliegue/activar.sh) comprueba la salud del contenedor y conserva el volumen. Si falla una versión, intenta volver al digest previo. En un primer despliegue fallido, retira el contenedor.

Verifica `GET /healthz` en el host, conecta Claude Code por la URL HTTPS y ejecuta una simulación pequeña. La publicación del host, el DNS, TLS y una corrida contra la URL pública siguen pendientes de verificar.

## 5.4 Evidencia y diagnóstico

```sh
PYTHONPATH=backend:mcp uv run --project mcp --locked \
  python -m unittest discover -s mcp/tests -v
```

- Las seis pruebas de integración cubren descubrimiento y validación del protocolo, encuesta y reformulación, historial y reapertura en la web local, aislamiento, reintento de entrega, cancelación e inactividad. [Pruebas](../../mcp/tests/test_integracion.py).
- Se verificó una corrida de un agente con Claude Code autenticado y dos subagentes, para encuesta y voz. El MCP guardó una corrida completa.
- GitHub Actions verificó la integración y el arranque de la imagen en `fa9dca0`. La publicación en GHCR y el despliegue a un host público no formaron parte de esa ejecución. [Ejecución de Actions](https://github.com/platanus-hack/platanus-hack-26-cl-team-28/actions/runs/44975872589).

| Síntoma | Comprobación |
|---|---|
| El cliente no conecta | Revisa la URL completa con `/mcp`, el proxy HTTPS, el dominio permitido y la salud local |
| La simulación espera y no avanza | Comprueba que el cliente llame a `trabajo`, ejecute los lotes y devuelva JSON válido |
| Una corrida no sale en la página pública | El modo aislado guarda en su propio volumen. Usa `consultar` con su acceso o prueba `--con-web` en local |
| Un acceso dejó de funcionar tras desplegar | Comprueba que se mantuvieron el secreto del servidor y el volumen. Las corridas que estaban en curso se interrumpen al reiniciar |
