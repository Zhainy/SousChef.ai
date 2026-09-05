variable "availability_domain_number" {
  description = "Índice del Availability Domain a utilizar (0, 1 o 2). Permite cambiar de AD si hay falta de capacidad de Ampere A1"
  type        = number
  default     = 0

  validation {
    condition     = var.availability_domain_number >= 0 && var.availability_domain_number <= 2
    error_message = "El índice del Availability Domain debe ser 0, 1 o 2."
  }
}

variable "boot_volume_size_in_gbs" {
  description = "Tamaño del disco de arranque en GB (mínimo 50 GB, máximo 200 GB en Always Free)"
  type        = number
  default     = 50

  validation {
    condition     = var.boot_volume_size_in_gbs >= 50 && var.boot_volume_size_in_gbs <= 200
    error_message = "El tamaño del disco debe estar entre 50 GB y 200 GB para mantenerse en Always Free."
  }
}

variable "compartment_id" {
  description = "OCID del compartimento donde aprovisionar los recursos (si se omite, se usa tenancy_ocid)"
  type        = string
  default     = ""
}

variable "fingerprint" {
  description = "Fingerprint de la API Key RSA del usuario en OCI"
  type        = string
  sensitive   = true
}

variable "github_repo_url" {
  description = "URL del repositorio Git que clonará cloud-init en la instancia"
  type        = string
  default     = "https://github.com/Zhainy/SousChef.ai.git"
}

variable "instance_shape_memory_gb" {
  description = "Cantidad de memoria RAM en GB para la instancia A1 Flex (máx 24 GB en Always Free)"
  type        = number
  default     = 12

  validation {
    condition     = var.instance_shape_memory_gb >= 1 && var.instance_shape_memory_gb <= 24
    error_message = "La memoria RAM debe estar entre 1 y 24 GB para no exceder la cuota Always Free."
  }
}

variable "instance_shape_ocpus" {
  description = "Número de OCPUs para la instancia Ampere A1 (máx 4 OCPUs en Always Free)"
  type        = number
  default     = 2

  validation {
    condition     = var.instance_shape_ocpus >= 1 && var.instance_shape_ocpus <= 4
    error_message = "El número de OCPUs debe estar entre 1 y 4 para no exceder la cuota Always Free."
  }
}

variable "private_key_path" {
  description = "Ruta absoluta al archivo de clave privada PEM (ej: ~/.oci/oci_api_key.pem)"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "Región de OCI donde se desplegará la infraestructura (ej: us-ashburn-1, us-chicago-1)"
  type        = string
  default     = "us-ashburn-1"
}

variable "ssh_public_key" {
  description = "Contenido de la clave pública SSH para acceder a la instancia"
  type        = string
}

variable "ssh_source_cidr" {
  description = "Bloque CIDR permitido para acceso SSH al puerto 22 (restringir a tu IP para mayor seguridad, ej: 190.x.x.x/32)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "tenancy_ocid" {
  description = "OCID del tenancy raíz de Oracle Cloud Infrastructure (OCI)"
  type        = string
}

variable "user_ocid" {
  description = "OCID del usuario de OCI utilizado para Terraform"
  type        = string
}
