# What If Chile en AWS: una EC2 con el motor (Haiku por la CLI de Claude Code), Caddy y el front.
#
#     cd infra && terraform init && terraform apply
#
# La sesión de Claude y la clave de acceso no están aquí ni en el repositorio: viven en /etc/ph26
# dentro de la máquina (ver infra/README.md).

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  backend "s3" {
    bucket  = "ph26-whatif-tfstate-337227272524"
    key     = "whatif.tfstate"
    region  = "us-east-1"
    profile = "japs"
  }
}

variable "perfil" {
  description = "Perfil de AWS con que se despliega"
  default     = "japs"
}

variable "tipo" {
  description = "Cada lote es un proceso de la CLI y lo que limita es la CPU: 16 vCPU dan unos 90 agentes por segundo"
  default     = "c7i.4xlarge"
}

variable "dominio" {
  default = "whatif.japs.ing"
}

variable "repositorio" {
  default = "https://github.com/platanus-hack/platanus-hack-26-cl-team-28.git"
}

provider "aws" {
  region  = "us-east-1"
  profile = var.perfil
  default_tags {
    tags = { proyecto = "hackathon-ph26", iniciativa = "personal" }
  }
}

data "aws_vpc" "defecto" {
  default = true
}

data "aws_ssm_parameter" "ubuntu" {
  name = "/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id"
}

resource "aws_key_pair" "despliegue" {
  key_name   = "ph26-whatif"
  public_key = file("${path.module}/llave.pub")
}

resource "aws_security_group" "web" {
  name        = "ph26-whatif"
  description = "What If Chile: web y SSH con llave"
  vpc_id      = data.aws_vpc.defecto.id

  dynamic "ingress" {
    for_each = [22, 80, 443]
    content {
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "motor" {
  ami                    = data.aws_ssm_parameter.ubuntu.value
  instance_type          = var.tipo
  key_name               = aws_key_pair.despliegue.key_name
  vpc_security_group_ids = [aws_security_group.web.id]
  user_data = templatefile("${path.module}/instalar.sh", {
    dominio     = var.dominio
    repositorio = var.repositorio
  })
  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }
  tags = { Name = "ph26-whatif" }
  lifecycle {
    # Una imagen nueva de Ubuntu o un cambio en el instalador no deben recrear la máquina.
    ignore_changes = [ami, user_data]
  }
}

# Sin IP fija: la cuenta ya usa sus cinco direcciones elásticas. La IP pública se mantiene mientras la
# máquina no se detenga; si se detiene y vuelve a partir, hay que actualizar el registro del dominio.

output "ip" {
  value = aws_instance.motor.public_ip
}

output "ssh" {
  value = "ssh -i ~/.ssh/ph26_whatif ubuntu@${aws_instance.motor.public_ip}"
}
