#!/bin/bash
# Primer arranque de la máquina. Deja instalado lo necesario y dos servicios (el despliegue lo
# dispara GitHub Actions por SSH en cada push a main, con infra/desplegar.sh):
#   ph26-motor   el servidor de simulación, en 127.0.0.1:8787
#   caddy        HTTPS para ${dominio}, el front y /api hacia el motor
set -x
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -yq poppler-utils rsync git caddy
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -yq nodejs
npm install -g @anthropic-ai/claude-code
sudo -u ubuntu bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
sudo -u ubuntu git clone ${repositorio} /home/ubuntu/ph26

# La llave con que entra GitHub Actions a desplegar.
cat /home/ubuntu/ph26/infra/llave-cd.pub >> /home/ubuntu/.ssh/authorized_keys

mkdir -p /etc/ph26 /var/www/ph26
# Aquí van CLAUDE_TOKENS (sesiones de `claude setup-token`) y, si se quiere, otros ajustes del motor.
touch /etc/ph26/entorno && chmod 600 /etc/ph26/entorno

# El servicio del motor y la configuración de Caddy están en el repositorio (infra/); el despliegue
# los vuelve a instalar cuando cambian.
cp /home/ubuntu/ph26/infra/ph26-motor.service /etc/systemd/system/ph26-motor.service
cp /home/ubuntu/ph26/infra/Caddyfile /etc/caddy/Caddyfile
mkdir -p /etc/systemd/system/caddy.service.d
printf '[Service]\nEnvironment=DOMINIO=%s\n' "${dominio}" > /etc/systemd/system/caddy.service.d/dominio.conf

systemctl daemon-reload
systemctl enable ph26-motor
sudo -u ubuntu HOME=/home/ubuntu FORZAR=1 bash /home/ubuntu/ph26/infra/desplegar.sh
systemctl restart caddy
touch /home/ubuntu/listo
