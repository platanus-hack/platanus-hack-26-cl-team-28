#!/usr/bin/env bash
# Levanta el motor de simulación (backend) y el front, y los detiene juntos con Ctrl+C.
#
#     ./iniciar.sh             # motor en vivo si hay Claude Code o ANTHROPIC_API_KEY
#     MOTOR=grabado ./iniciar.sh   # sin red: repite una corrida real guardada
set -euo pipefail
raiz="$(cd "$(dirname "$0")" && pwd)"

(cd "$raiz/backend" && LOTE="${LOTE:-20}" CONCURRENCIA="${CONCURRENCIA:-50}" exec python3 -m servidor) &
motor=$!
trap 'kill $motor 2>/dev/null' EXIT

cd "$raiz/frontend"
[ -d node_modules ] || npm install
npx vite
