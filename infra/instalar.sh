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

cat > /etc/systemd/system/ph26-motor.service <<'UNIDAD'
[Unit]
Description=What If Chile: motor de simulacion
After=network-online.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/ph26/backend
Environment=HOME=/home/ubuntu MOTOR=claude LOTE=20 CONCURRENCIA=150
EnvironmentFile=/etc/ph26/entorno
ExecStart=/home/ubuntu/.local/bin/uv run python -m servidor
Restart=always
RestartSec=2
LimitNOFILE=65536
TasksMax=infinity

[Install]
WantedBy=multi-user.target
UNIDAD

cat > /etc/caddy/Caddyfile <<'CADDY'
(sitio) {
	# /etc/ph26/acceso.caddy pide usuario y clave; si no existe, el sitio queda abierto.
	import /etc/ph26/*.caddy
	handle /api/* {
		reverse_proxy 127.0.0.1:8787 {
			flush_interval -1
		}
	}
	handle {
		root * /var/www/ph26
		encode gzip
		try_files {path} /index.html
		file_server
	}
}

${dominio} {
	import sitio
}

# Por la IP, sin certificado: sirve para probar antes de que exista el dominio.
http:// {
	import sitio
}
CADDY

systemctl daemon-reload
systemctl enable ph26-motor
sudo -u ubuntu HOME=/home/ubuntu FORZAR=1 bash /home/ubuntu/ph26/infra/desplegar.sh
systemctl restart caddy
touch /home/ubuntu/listo
