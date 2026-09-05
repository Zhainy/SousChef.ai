output "instance_public_ip" {
  description = "Dirección IP pública asignada a la instancia de SousChef"
  value       = oci_core_instance.souschef.public_ip
}

output "instance_ocid" {
  description = "OCID de la instancia de cómputo creada"
  value       = oci_core_instance.souschef.id
}

output "ssh_command" {
  description = "Comando para conectar vía SSH a la instancia"
  value       = "ssh ubuntu@${oci_core_instance.souschef.public_ip}"
}

output "next_steps" {
  description = "Pasos siguientes para desplegar la aplicación"
  value       = <<-EOT
    ===================================================================
    ¡Infraestructura OCI creada exitosamente!
    IP Pública: ${oci_core_instance.souschef.public_ip}

    1. Conectar a la instancia por SSH:
       ssh ubuntu@${oci_core_instance.souschef.public_ip}

    2. Opcional: Subir el modelo GGUF local a la VM (para fallback offline):
       scp models/Qwen3.5-4B-Q4_K_M.gguf ubuntu@${oci_core_instance.souschef.public_ip}:/opt/souschef/models/

    3. Entrar al directorio del proyecto y desplegar:
       ssh ubuntu@${oci_core_instance.souschef.public_ip} "cd /opt/souschef/app && ./scripts/deploy_oci.sh"
    ===================================================================
  EOT
}
