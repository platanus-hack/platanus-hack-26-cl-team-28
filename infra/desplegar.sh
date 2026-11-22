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
# Ojo: el bash que corre este archivo lo sigue leyendo de la copia anterior aunque la línea de arriba
# lo haya reemplazado. Un cambio a este script vale recién en el despliegue siguiente: después de
# tocarlo, despliega a mano una vez (FORZAR=1 bash infra/desplegar.sh).
fallo=""

# El front solo se recompila si cambió (o la primera vez).
if [ -n "${FORZAR:-}" ] || [ ! -f /var/www/ph26/index.html ] || ! git diff --quiet "$antes" HEAD -- frontend; then
  (cd frontend && npm ci --no-audit --no-fund && npm run build)
  sudo rsync -a --delete frontend/dist/ /var/www/ph26/
fi

(cd backend && uv sync -q)

# La configuración de Caddy vive en infra/Caddyfile. Se instala solo si cambió y solo si es válida;
# si Caddy no logra cargarla, vuelve la anterior: el sitio nunca queda sin servidor web.
if ! sudo cmp -s infra/Caddyfile /etc/caddy/Caddyfile; then
  if sudo caddy validate --config infra/Caddyfile --adapter caddyfile >/dev/null 2>&1; then
    sudo cp -p /etc/caddy/Caddyfile /etc/caddy/Caddyfile.anterior
    sudo cp infra/Caddyfile /etc/caddy/Caddyfile
    if sudo systemctl reload caddy; then
      echo "Caddy: configuración nueva cargada"
    else
      sudo cp -p /etc/caddy/Caddyfile.anterior /etc/caddy/Caddyfile
      sudo systemctl reload caddy || sudo systemctl restart caddy
      echo "Caddy no pudo cargar la configuración nueva: quedó la anterior" >&2
      fallo=1
    fi
  else
    echo "infra/Caddyfile no es válido: quedó la configuración anterior" >&2
    fallo=1
  fi
fi

# Lo mismo con el servicio del motor (infra/ph26-motor.service).
servicio=/etc/systemd/system/ph26-motor.service
servicio_nuevo=""
if ! sudo cmp -s infra/ph26-motor.service "$servicio"; then
  sudo cp -p "$servicio" "$servicio.anterior"
  sudo cp infra/ph26-motor.service "$servicio"
  sudo systemctl daemon-reload
  servicio_nuevo=1
fi

responde() {
  for _ in $(seq 90); do
    curl -sf -m 2 http://127.0.0.1:8787/api/estado >/dev/null && return 0
    sleep 1
  done
  return 1
}

# No se corta una simulación en curso por un cambio que no toca al motor.
if [ -n "${FORZAR:-}" ] || [ -n "$servicio_nuevo" ] || ! git diff --quiet "$antes" HEAD -- backend; then
  sudo systemctl restart ph26-motor
  if ! responde; then
    echo "El motor no respondió después de reiniciar:" >&2
    sudo journalctl -u ph26-motor -n 25 --no-pager >&2 || true
    if [ -n "$servicio_nuevo" ]; then
      # Con el servicio nuevo no partió: vuelve el anterior y se intenta otra vez.
      sudo cp -p "$servicio.anterior" "$servicio"
      sudo systemctl daemon-reload
      sudo systemctl restart ph26-motor
    fi
    if [ -z "$servicio_nuevo" ] || ! responde; then
      # Tampoco así: el problema está en el código nuevo. Vuelve el motor a la versión que andaba.
      git checkout -q "$antes" -- backend
      (cd backend && uv sync -q)
      sudo systemctl restart ph26-motor
      if responde; then
        echo "El motor quedó andando con el código anterior ($(git rev-parse --short "$antes"))" >&2
      fi
    fi
    fallo=1
  fi
fi
echo "Desplegado $(git rev-parse --short HEAD)"
# Si algo de lo anterior falló, el despliegue queda en rojo aunque el sitio siga arriba con lo anterior.
[ -z "${fallo:-}" ]
