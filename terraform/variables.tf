variable "tenancy_ocid" {
  type        = string
  description = "OCID del tenancy raíz de Oracle Cloud Infrastructure (OCI)"
}

variable "user_ocid" {
  type        = string
  description = "OCID del usuario de OCI utilizado para Terraform"
}

variable "fingerprint" {
  type        = string
  description = "Fingerprint de la API Key RSA del usuario en OCI"
}

variable "private_key_path" {
  type        = string
  description = "Ruta absoluta al archivo de clave privada PEM (ej: ~/.oci/oci_api_key.pem)"
}

variable "region" {
  type        = string
  default     = "us-ashburn-1"
  description = "Región de OCI donde se desplegará la infraestructura (ej: us-ashburn-1, sa-santiago-1)"
}

variable "compartment_id" {
  type        = string
  default     = ""
  description = "OCID del compartimento (si se deja vacío, se usa tenancy_ocid)"
}

variable "ssh_public_key" {
  type        = string
  description = "Contenido de la clave pública SSH para acceder a la instancia (ej: contents of ~/.ssh/id_rsa.pub o ~/.ssh/id_ed25519.pub)"
}

variable "instance_shape_ocpus" {
  type        = number
  default     = 2
  description = "Número de OCPUs para la instancia Ampere A1 (máx 4 gratis en Always Free)"
}

variable "instance_shape_memory_gb" {
  type        = number
  default     = 12
  description = "Cantidad de memoria RAM en GB para la instancia A1 (máx 24 gratis en Always Free)"
}

variable "boot_volume_size_in_gbs" {
  type        = number
  default     = 100
  description = "Tamaño del disco de arranque en GB (máx 200 GB gratis en Always Free)"
}

variable "github_repo_url" {
  type        = string
  default     = "https://github.com/Zhainy/SousChef.ai.git"
  description = "URL del repositorio Git que clonará cloud-init en la instancia"
}
