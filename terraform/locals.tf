locals {
  compartment_id = var.compartment_id != "" ? var.compartment_id : var.tenancy_ocid

  common_tags = {
    Environment = "production"
    ManagedBy   = "Terraform"
    Project     = "SousChef"
  }
}
