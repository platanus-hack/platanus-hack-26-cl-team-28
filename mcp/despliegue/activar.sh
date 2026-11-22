#!/usr/bin/env bash
# Se ejecuta en el host dedicado del MCP. El proyecto web queda fuera de Compose.
set -euo pipefail
imagen=${1:?Falta el digest de la imagen}
if [[ ! "$imagen" =~ ^ghcr\.io/[a-z0-9._/-]+@sha256:[a-f0-9]{64}$ ]]; then
  echo "El despliegue requiere un digest de GHCR" >&2
  exit 1
fi
cd "$HOME/whatif-mcp"
umask 077
anterior=""
if [[ -f .imagen ]]; then
  read -r anterior < .imagen
fi
printf 'WHATIF_MCP_IMAGE=%s\n' "$imagen" > .imagen.proxima
trap 'unlink .imagen.proxima 2>/dev/null || true' EXIT
compose=(docker compose -p whatif-mcp -f compose.yml)
"${compose[@]}" --env-file .imagen.proxima pull
if "${compose[@]}" --env-file .imagen.proxima up -d --wait --wait-timeout 60; then
  mv .imagen.proxima .imagen
  exit 0
fi
if [[ -n "$anterior" ]]; then
  "${compose[@]}" --env-file .imagen up -d --wait --wait-timeout 60
else
  "${compose[@]}" --env-file .imagen.proxima down
fi
echo "No se activó la nueva versión del MCP" >&2
exit 1
