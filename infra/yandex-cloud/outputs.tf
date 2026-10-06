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
