#!/bin/bash
# Despliegue continuo: lo corre GitHub Actions por SSH en cada push a main
# (.github/workflows/desplegar.yml). Si main cambió, trae lo nuevo, compila el front, actualiza las dependencias del motor y lo reinicia.
#     FORZAR=1 bash infra/desplegar.sh    # despliega aunque no haya cambios
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
cd "$HOME/ph26"

git fetch -q origin main
if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] && [ -z "${FORZAR:-}" ]; then
  exit 0
fi
antes=$(git rev-parse HEAD)
git reset -q --hard origin/main

# El front solo se recompila si cambió (o la primera vez).
if [ -n "${FORZAR:-}" ] || [ ! -f /var/www/ph26/index.html ] || ! git diff --quiet "$antes" HEAD -- frontend; then
  (cd frontend && npm ci --no-audit --no-fund && npm run build)
  sudo rsync -a --delete frontend/dist/ /var/www/ph26/
fi

(cd backend && uv sync -q)
# No se corta una simulación en curso por un cambio que no toca al motor.
if [ -n "${FORZAR:-}" ] || ! git diff --quiet "$antes" HEAD -- backend; then
  sudo systemctl restart ph26-motor
fi
echo "Desplegado $(git rev-parse --short HEAD)"
