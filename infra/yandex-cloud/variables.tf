variable "cloud_id" {
  description = "Yandex Cloud cloud ID. Supply outside source control."
  type        = string
}

variable "folder_id" {
  description = "Dedicated production folder ID in the Yandex Cloud Russia region."
  type        = string
}

variable "project_name" {
  description = "Prefix for HOST-001 resources."
  type        = string
  default     = "ai-career-agent"
}

variable "app_zone" {
  description = "Primary application availability zone in the Russia region."
  type        = string
  default     = "ru-central1-d"

  validation {
    condition     = contains(["ru-central1-a", "ru-central1-b", "ru-central1-d", "ru-central1-e"], var.app_zone)
    error_message = "HOST-001 permits only Yandex Cloud Russia availability zones."
  }
}

variable "db_secondary_zone" {
  description = "Second Managed PostgreSQL availability zone."
  type        = string
  default     = "ru-central1-b"

  validation {
    condition     = contains(["ru-central1-a", "ru-central1-b", "ru-central1-d", "ru-central1-e"], var.db_secondary_zone)
    error_message = "HOST-001 permits only Yandex Cloud Russia availability zones."
  }
}

variable "app_subnet_cidr" {
  description = "Private CIDR for the application VM subnet."
  type        = string
  default     = "10.40.0.0/24"
}

variable "db_secondary_subnet_cidr" {
  description = "Private CIDR for the secondary PostgreSQL host subnet."
  type        = string
  default     = "10.40.1.0/24"
}

variable "admin_cidr" {
  description = "Single trusted IPv4 CIDR allowed to SSH to the VM, e.g. 203.0.113.10/32. Never use 0.0.0.0/0."
  type        = string

  validation {
    condition     = var.admin_cidr != "0.0.0.0/0" && can(cidrhost(var.admin_cidr, 0))
    error_message = "admin_cidr must be a valid restricted IPv4 CIDR and must not be 0.0.0.0/0."
  }
}

variable "admin_username" {
  description = "Non-root administrative user created by cloud-init."
  type        = string
  default     = "acaadmin"
}

variable "ssh_public_key" {
  description = "SSH public key for the administrative user. This is not a private credential."
  type        = string
}

variable "vm_platform_id" {
  description = "Compute Cloud platform for the initial single application VM."
  type        = string
  default     = "standard-v3"
}

variable "vm_cores" {
  type    = number
  default = 2
}

variable "vm_memory_gb" {
  type    = number
  default = 4
}

variable "vm_disk_gb" {
  type    = number
  default = 40
}

variable "ubuntu_image_family" {
  description = "Yandex Cloud Marketplace image family."
  type        = string
  default     = "ubuntu-2404-lts"
}

variable "postgresql_resource_preset_id" {
  description = "Managed PostgreSQL host class. Change only after cost/capacity review."
  type        = string
  default     = "s3-c2-m8"
}

variable "postgresql_disk_type_id" {
  type    = string
  default = "network-ssd"
}

variable "postgresql_disk_size_gb" {
  type    = number
  default = 20
}

variable "postgresql_backup_retain_days" {
  description = "Managed PostgreSQL backup retention baseline; final legal/OPS-002 policy may revise it."
  type        = number
  default     = 7

  validation {
    condition     = var.postgresql_backup_retain_days >= 7
    error_message = "HOST-001 keeps at least seven days of managed PostgreSQL backups for the field-test foundation."
  }
}

variable "postgresql_database_name" {
  type    = string
  default = "ai_career_agent"
}

variable "postgresql_username" {
  type    = string
  default = "ai_career_agent"
}

variable "postgresql_app_password" {
  description = "Supply only through TF_VAR_postgresql_app_password or another protected runtime channel. Do not put it in tfvars or Git."
  type        = string
  sensitive   = true
}

variable "postgresql_password_version" {
  description = "Increment to rotate the write-only Managed PostgreSQL user password."
  type        = number
  default     = 1
}
