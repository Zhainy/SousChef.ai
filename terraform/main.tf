# 1. Availability Domains
data "oci_identity_availability_domains" "ads" {
  compartment_id = local.compartment_id
}

# 2. Imagen Canonical Ubuntu 22.04 LTS para arquitectura ARM64 (A1 Flex)
data "oci_core_images" "ubuntu" {
  compartment_id           = local.compartment_id
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# 3. Red Virtual en la Nube (VCN)
resource "oci_core_vcn" "main" {
  compartment_id = local.compartment_id
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "souschef-vcn"
  dns_label      = "souschef"
  freeform_tags  = local.common_tags
}

# 4. Internet Gateway
resource "oci_core_internet_gateway" "main" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "souschef-igw"
  enabled        = true
  freeform_tags  = local.common_tags
}

# 5. Route Table hacia Internet Gateway
resource "oci_core_route_table" "main" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "souschef-route-table"
  freeform_tags  = local.common_tags

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.main.id
  }
}

# 6. Security List (SSH, HTTP, HTTPS y PMTUD ICMP)
resource "oci_core_security_list" "main" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.main.id
  display_name   = "souschef-security-list"
  freeform_tags  = local.common_tags

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
    description = "Permitir todo el trafico saliente"
  }

  ingress_security_rules {
    protocol    = "6" # TCP
    source      = var.ssh_source_cidr
    description = "SSH access"
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "HTTP access (Let's Encrypt y frontend)"
    tcp_options {
      min = 80
      max = 80
    }
  }

  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "HTTPS access seguro"
    tcp_options {
      min = 443
      max = 443
    }
  }

  ingress_security_rules {
    protocol    = "1" # ICMP
    source      = "0.0.0.0/0"
    description = "Path MTU Discovery (PMTUD) necesario en OCI para evitar caidas de paquetes TLS"
    icmp_options {
      type = 3
      code = 4
    }
  }
}

# 7. Subnet Pública
resource "oci_core_subnet" "public" {
  compartment_id             = local.compartment_id
  vcn_id                     = oci_core_vcn.main.id
  cidr_block                 = "10.0.0.0/24"
  display_name               = "souschef-public-subnet"
  dns_label                  = "public"
  route_table_id             = oci_core_route_table.main.id
  security_list_ids          = [oci_core_security_list.main.id]
  prohibit_public_ip_on_vnic = false
  freeform_tags              = local.common_tags
}

# 8. Instancia Ampere A1 Compute (Always Free)
resource "oci_core_instance" "souschef" {
  compartment_id      = local.compartment_id
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[var.availability_domain_number].name
  display_name        = "souschef-vm"
  shape               = "VM.Standard.A1.Flex"
  freeform_tags       = local.common_tags

  shape_config {
    ocpus         = var.instance_shape_ocpus
    memory_in_gbs = var.instance_shape_memory_gb
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu.images[0].id
    boot_volume_size_in_gbs = var.boot_volume_size_in_gbs
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    display_name     = "souschef-primary-vnic"
    assign_public_ip = true
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(templatefile("${path.module}/cloud-init.yaml", {
      github_repo_url = var.github_repo_url
    }))
  }

  preserve_boot_volume = false
}

# 9. Dynamic Group para Instance Principal
resource "oci_identity_dynamic_group" "souschef_instances" {
  name           = "souschef-instances"
  description    = "Grupo dinamico para la instancia de SousChef.ai"
  compartment_id = var.tenancy_ocid
  matching_rule  = "instance.id = '${oci_core_instance.souschef.id}'"
  freeform_tags  = local.common_tags
}

# 10. IAM Policy para OCI Generative AI (Menor Privilegio acotado al compartimento)
resource "oci_identity_policy" "souschef_genai" {
  name           = "souschef-genai-policy"
  description    = "Permite a la instancia SousChef usar OCI Generative AI acotado al compartimento"
  compartment_id = var.tenancy_ocid
  freeform_tags  = local.common_tags
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.souschef_instances.name} to use generative-ai-family in compartment id ${local.compartment_id}"
  ]
}
