output "app_public_ipv4" {
  description = "Reserved public IPv4 for HOST-001 smoke and future DOMAIN-001 A record."
  value       = yandex_vpc_address.app.external_ipv4_address[0].address
}

output "app_vm_id" {
  value = yandex_compute_instance.app.id
}

output "postgresql_cluster_id" {
  value = yandex_mdb_postgresql_cluster.main.id
}

output "postgresql_host_profile" {
  description = "Selected Managed PostgreSQL topology profile: single or two."
  value       = var.postgresql_host_profile
}

output "postgresql_rw_fqdn" {
  description = "Managed PostgreSQL read-write FQDN. Use port 6432."
  value       = "c-${yandex_mdb_postgresql_cluster.main.id}.rw.mdb.yandexcloud.net"
}

output "runtime_lockbox_secret_id" {
  description = "Add the runtime secret payload after infrastructure creation; Terraform intentionally creates no secret values."
  value       = yandex_lockbox_secret.runtime.id
}

output "deployment_boundary" {
  value = "HOST-001 foundation only: no data migration, no legal activation, no real-data Alice, no commercial launch."
}


output "field_test_resources_enabled" {
  value = var.field_test_resources_enabled
}

output "field_test_backup_bucket" {
  description = "Synthetic Stage C Object Storage bucket name; null when the field-test profile is disabled."
  value       = var.field_test_resources_enabled ? yandex_storage_bucket.field_test[0].bucket : null
}

output "field_test_backup_lockbox_secret_id" {
  description = "Lockbox secret containing temporary Object Storage access keys; values are never Terraform outputs."
  value       = var.field_test_resources_enabled ? yandex_lockbox_secret.field_test_storage[0].id : null
}

output "field_test_restore_rw_fqdn" {
  description = "Disposable Stage C PostgreSQL 18 restore target; null when disabled."
  value       = var.field_test_resources_enabled ? "c-${yandex_mdb_postgresql_cluster.field_test_restore[0].id}.rw.mdb.yandexcloud.net" : null
}
