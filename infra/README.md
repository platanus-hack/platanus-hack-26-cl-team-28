# Despliegue en AWS

La operación del sitio (despliegue, variables, salud e incidentes) está en
[`docs/backend/08-operacion.md`](../docs/backend/08-operacion.md). Este archivo explica cómo se crea la máquina.

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

Un archivo en `/etc/ph26` de la máquina, que se crea a mano una vez:

- `entorno`: `CLAUDE_TOKENS=sk-ant-oat...` con los tokens de `claude setup-token`, separados por coma si
  son de varias cuentas (las llamadas se reparten entre ellas). Después, `sudo systemctl restart ph26-motor`.

## Sitio abierto al público

El sitio no pide usuario ni clave: cualquiera que entre puede correr simulaciones, y cada corrida
gasta la suscripción de quien puso su token. Conviene bajar lo que puede pedir cada persona, porque
todas comparten la misma suscripción y la misma máquina (unos 90 agentes por segundo entre todos).
En `/etc/ph26/entorno`, y después `sudo systemctl restart ph26-motor`:

    MAXIMO_MUESTRA=2000          # agentes por corrida (10.000 si no se pone)
    RESPUESTAS_POR_CORRIDA=8000  # agentes × (variantes + iteraciones)
    RESPUESTAS_EN_COLA=60000     # con 90 por segundo, unos 11 minutos de trabajo pendiente como máximo
    HISTORIAL_OCULTO=1           # el historial es común: sin esto, lo que escribe cualquiera lo ven todos

Con eso, quince personas con el máximo a la vez son 30.000 respuestas: unos cinco a seis minutos
para que terminen todas, avanzando a la par. Los demás topes están en `backend/servidor/README.md`.

La configuración de Caddy (`infra/Caddyfile`) y el servicio del motor (`infra/ph26-motor.service`)
están en el repositorio: `desplegar.sh` los instala cuando cambian. Caddy se valida antes de cargar y
el motor se comprueba después de reiniciar; si algo falla, vuelve lo anterior y el despliegue queda
en rojo. Un cambio en `desplegar.sh` vale recién en el despliegue siguiente (el que corre es
la copia anterior): después de tocarlo, despliega a mano una vez con `FORZAR=1`.

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
