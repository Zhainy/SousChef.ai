output "instance_ocid" {
  description = "OCID de la instancia de computo creada"
  value       = oci_core_instance.souschef.id
}

output "instance_public_ip" {
  description = "Direccion IP publica asignada a la instancia de SousChef"
  value       = oci_core_instance.souschef.public_ip
}

output "next_steps" {
  description = "Pasos siguientes para desplegar la aplicacion"
  value       = <<-EOT
    ===================================================================
    ¡Infraestructura OCI creada exitosamente!
    IP Publica: ${oci_core_instance.souschef.public_ip}

    1. Conectar a la instancia por SSH:
       ssh ubuntu@${oci_core_instance.souschef.public_ip}

    2. Ejecutar el script de despliegue:
       ssh ubuntu@${oci_core_instance.souschef.public_ip} "cd /opt/souschef/app && ./scripts/deploy_oci.sh"
    ===================================================================
  EOT
}

output "ssh_command" {
  description = "Comando para conectar via SSH a la instancia"
  value       = "ssh ubuntu@${oci_core_instance.souschef.public_ip}"
}
