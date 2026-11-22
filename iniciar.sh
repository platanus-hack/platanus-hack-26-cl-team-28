#!/usr/bin/env bash
# Levanta el motor de simulación (backend) y el front, y los detiene juntos con Ctrl+C.
#
#     ./iniciar.sh             # motor en vivo si hay Claude Code o ANTHROPIC_API_KEY
#     LLAMA_URL=http://127.0.0.1:8080 ./iniciar.sh   # sin red: con un modelo local
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
