#!/usr/bin/env bash
# Levanta el motor de simulación (backend) y el front, y los detiene juntos con Ctrl+C.
#
#     ./iniciar.sh             # motor en vivo si hay Claude Code o ANTHROPIC_API_KEY
#     TAMANO_GRUPO=3 ./iniciar.sh  # catálogo experimental de grupos de 3
#     TAMANO_GRUPO=5 ./iniciar.sh  # catálogo experimental de grupos de 5
#     MOTOR=grabado ./iniciar.sh   # sin red: repite una corrida real guardada
set -euo pipefail
raiz="$(cd "$(dirname "$0")" && pwd)"

# Con uv el motor lee la tabla de agentes (necesita DuckDB); sin uv usa el archivo fijo de 2.000 personas.
if command -v uv >/dev/null; then python=(uv run python); else python=(python3); fi
(cd "$raiz/backend" && LOTE="${LOTE:-20}" CONCURRENCIA="${CONCURRENCIA:-50}" exec "${python[@]}" -m servidor) &
motor=$!
trap 'kill $motor 2>/dev/null' EXIT

cd "$raiz/frontend"
[ -d node_modules ] || npm install
npx vite
