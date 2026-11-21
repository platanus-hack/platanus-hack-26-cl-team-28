# Despliegue en AWS

Una sola máquina (EC2 `c7i.4xlarge`, 16 vCPU) con todo: el motor de simulación, el front compilado y
Caddy con HTTPS. Los agentes responden con Haiku por la CLI de Claude Code, igual que en local, con la
sesión de una o más cuentas de Claude.

    cd infra
    terraform init
    terraform apply        # crea la máquina y el grupo de seguridad

El estado de Terraform está en el bucket `ph26-whatif-tfstate-337227272524` (perfil `japs`).

## Despliegue continuo

Cada push a `main` dispara `.github/workflows/desplegar.yml`: entra por SSH a la máquina y corre
`infra/desplegar.sh`, que trae `main`, recompila el front solo si cambió `frontend/` y reinicia el motor
solo si cambió `backend/`. Si el build del front falla, el workflow queda en rojo y el sitio sigue con la
versión anterior.

Secretos del repositorio: `WHATIF_SSH_KEY` (llave privada cuya parte pública es `infra/llave-cd.pub`) y
`WHATIF_HOST` (el dominio).

    gh run list --workflow desplegar.yml      # qué se desplegó
    gh workflow run desplegar.yml             # desplegar a mano

Para entrar a la máquina:

    ssh -i ~/.ssh/ph26_whatif ubuntu@whatif.japs.ing
    journalctl -u ph26-motor -f               # el motor
    FORZAR=1 bash ~/ph26/infra/desplegar.sh   # despliega aunque no haya cambios

## Lo que no está en el repositorio

Dos archivos en `/etc/ph26` de la máquina, que se crean a mano una vez:

- `entorno`: `CLAUDE_TOKENS=sk-ant-oat...` con los tokens de `claude setup-token`, separados por coma si
  son de varias cuentas (las llamadas se reparten entre ellas). Después, `sudo systemctl restart ph26-motor`.
- `acceso.caddy`: usuario y clave para entrar al sitio, porque cada corrida gasta la suscripción de
  quien puso su token. Sin este archivo el sitio queda abierto.

      basicauth {
          USUARIO HASH        # el hash sale de: caddy hash-password
      }

  Después, `sudo systemctl reload caddy`.

## Dominio

`whatif.japs.ing` es un registro A en Cloudflare hacia la IP de `terraform output ip`, en modo solo DNS
(nube gris). Caddy pide el certificado solo cuando el dominio ya apunta a la máquina.

## Velocidad medida (21 de noviembre de 2026)

| Agentes | Tiempo | Notas |
|---|---|---|
| 1.000 | 28 s | primera respuesta a los 6 s |
| 10.000 | 105 s | 5,6 % de los lotes falló por el límite de una sola cuenta |

Lo que limita es la CPU (cada lote es un proceso de la CLI) y, desde unos 90 agentes por segundo, la
suscripción. La máquina no tiene IP fija (la cuenta ya usa sus cinco direcciones elásticas): si se detiene y se
vuelve a encender, cambia de IP y hay que actualizar el registro A del dominio.
