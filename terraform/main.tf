terraform {
  required_version = ">= 1.5.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

locals {
  compartment_id = var.compartment_id != "" ? var.compartment_id : var.tenancy_ocid
}

# 1. Availability Domain
data "oci_identity_availability_domains" "ads" {
  compartment_id = local.compartment_id
}

# 2. Imagen Ubuntu ARM64 (Canonical Ubuntu para A1 Flex)
data "oci_core_images" "ubuntu" {
  compartment_id   = local.compartment_id
  operating_system = "Canonical Ubuntu"
  shape            = "VM.Standard.A1.Flex"
  sort_by          = "TIMECREATED"
  sort_order       = "DESC"
}

# 3. Red Virtual en la Nube (VCN)
resource "oci_core_vcn" "souschef_vcn" {
  compartment_id = local.compartment_id
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "souschef-vcn"
  dns_label      = "souschef"
}

# 4. Internet Gateway
resource "oci_core_internet_gateway" "souschef_igw" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.souschef_vcn.id
  display_name   = "souschef-igw"
  enabled        = true
}

# 5. Route Table hacia Internet Gateway
resource "oci_core_route_table" "souschef_rt" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.souschef_vcn.id
  display_name   = "souschef-route-table"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.souschef_igw.id
  }
}

# 6. Security List (Puertos 22 SSH, 80 HTTP, 443 HTTPS)
resource "oci_core_security_list" "souschef_sl" {
  compartment_id = local.compartment_id
  vcn_id         = oci_core_vcn.souschef_vcn.id
  display_name   = "souschef-security-list"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
    description = "Permitir todo el tráfico saliente"
  }

  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "SSH access"
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "HTTP access (Let's Encrypt y redirect)"
    tcp_options {
      min = 80
      max = 80
    }
  }

  ingress_security_rules {
    protocol    = "6" # TCP
    source      = "0.0.0.0/0"
    description = "HTTPS access"
    tcp_options {
      min = 443
      max = 443
    }
  }
}

# 7. Subnet Pública
resource "oci_core_subnet" "souschef_subnet" {
  compartment_id             = local.compartment_id
  vcn_id                     = oci_core_vcn.souschef_vcn.id
  cidr_block                 = "10.0.0.0/24"
  display_name               = "souschef-public-subnet"
  dns_label                  = "public"
  route_table_id             = oci_core_route_table.souschef_rt.id
  security_list_ids          = [oci_core_security_list.souschef_sl.id]
  prohibit_public_ip_on_vnic = false
}

# 8. Instancia Ampere A1 Compute (Always Free)
resource "oci_core_instance" "souschef" {
  compartment_id      = local.compartment_id
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "souschef-vm"
  shape               = "VM.Standard.A1.Flex"

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
    subnet_id        = oci_core_subnet.souschef_subnet.id
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
}

# 10. IAM Policy para OCI Generative AI
resource "oci_identity_policy" "souschef_genai" {
  name           = "souschef-genai-policy"
  description    = "Permite a la instancia SousChef usar OCI Generative AI sin secrets"
  compartment_id = var.tenancy_ocid
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.souschef_instances.name} to use generative-ai-family in tenancy"
  ]
}
