locals {
  common_labels = {
    service     = "ai-career-agent"
    package     = "host-001"
    environment = "production-foundation"
    region      = "ru"
  }
}

data "yandex_compute_image" "ubuntu" {
  family    = var.ubuntu_image_family
  folder_id = "standard-images"
}

resource "yandex_vpc_network" "main" {
  folder_id = var.folder_id
  name      = "${var.project_name}-prod"
  labels    = local.common_labels
}

resource "yandex_vpc_subnet" "app" {
  folder_id      = var.folder_id
  name           = "${var.project_name}-app-${var.app_zone}"
  zone           = var.app_zone
  network_id     = yandex_vpc_network.main.id
  v4_cidr_blocks = [var.app_subnet_cidr]
}

resource "yandex_vpc_subnet" "db_secondary" {
  folder_id      = var.folder_id
  name           = "${var.project_name}-db-${var.db_secondary_zone}"
  zone           = var.db_secondary_zone
  network_id     = yandex_vpc_network.main.id
  v4_cidr_blocks = [var.db_secondary_subnet_cidr]
}

resource "yandex_vpc_security_group" "app" {
  folder_id  = var.folder_id
  name       = "${var.project_name}-app-sg"
  network_id = yandex_vpc_network.main.id
  labels     = local.common_labels

  ingress {
    description    = "Public HTTP for pre-domain HOST-001 smoke and future redirect"
    protocol       = "TCP"
    port           = 80
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description    = "Public HTTPS for DOMAIN-001"
    protocol       = "TCP"
    port           = 443
    v4_cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description    = "Restricted administrative SSH"
    protocol       = "TCP"
    port           = 22
    v4_cidr_blocks = [var.admin_cidr]
  }

  egress {
    description    = "Application outbound HTTPS/provider/package traffic"
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "yandex_vpc_security_group" "database" {
  folder_id  = var.folder_id
  name       = "${var.project_name}-postgres-sg"
  network_id = yandex_vpc_network.main.id
  labels     = local.common_labels

  ingress {
    description       = "PostgreSQL only from the application security group"
    protocol          = "TCP"
    port              = 6432
    security_group_id = yandex_vpc_security_group.app.id
  }

  egress {
    description    = "Managed service control and replication traffic"
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "yandex_vpc_address" "app" {
  folder_id           = var.folder_id
  name                = "${var.project_name}-public-ip"
  deletion_protection = var.foundation_deletion_protection
  labels              = local.common_labels

  external_ipv4_address {
    zone_id = var.app_zone
  }
}

resource "yandex_iam_service_account" "app" {
  folder_id   = var.folder_id
  name        = "${var.project_name}-runtime"
  description = "HOST-001 VM identity; receives only secret-payload access in this package."
}

resource "yandex_lockbox_secret" "runtime" {
  folder_id           = var.folder_id
  name                = "${var.project_name}-runtime"
  description         = "Runtime application secrets. Payload is intentionally created outside Terraform."
  deletion_protection = var.foundation_deletion_protection
  labels              = local.common_labels
}

resource "yandex_lockbox_secret_iam_member" "runtime_payload" {
  secret_id = yandex_lockbox_secret.runtime.id
  role      = "lockbox.payloadViewer"
  member    = "serviceAccount:${yandex_iam_service_account.app.id}"
}

resource "yandex_mdb_postgresql_cluster" "main" {
  folder_id           = var.folder_id
  name                = "${var.project_name}-postgres"
  environment         = "PRODUCTION"
  network_id          = yandex_vpc_network.main.id
  security_group_ids  = [yandex_vpc_security_group.database.id]
  deletion_protection = var.foundation_deletion_protection
  labels              = local.common_labels

  config {
    version                   = 18
    backup_retain_period_days = var.postgresql_backup_retain_days

    resources {
      resource_preset_id = var.postgresql_resource_preset_id
      disk_type_id       = var.postgresql_disk_type_id
      disk_size          = var.postgresql_disk_size_gb
    }
  }

  host {
    zone             = var.app_zone
    subnet_id        = yandex_vpc_subnet.app.id
    assign_public_ip = false
  }

  dynamic "host" {
    for_each = var.postgresql_host_profile == "two" ? [1] : []
    content {
      zone             = var.db_secondary_zone
      subnet_id        = yandex_vpc_subnet.db_secondary.id
      assign_public_ip = false
    }
  }

  lifecycle {
    precondition {
      condition     = var.postgresql_host_profile == "single" || var.app_zone != var.db_secondary_zone
      error_message = "The two-host Managed PostgreSQL profile requires hosts in two different Russia availability zones."
    }
    precondition {
      condition     = !var.field_test_resources_enabled || !var.foundation_deletion_protection
      error_message = "Stage C field-test creation requires foundation_deletion_protection=false so the approved short test can be torn down without a second protection-disabling apply."
    }
    precondition {
      condition     = !var.field_test_resources_enabled || length(var.field_test_restore_password) >= 16
      error_message = "Stage C field-test creation requires a synthetic restore password of at least 16 characters supplied outside source control."
    }
  }
}

resource "yandex_mdb_postgresql_user" "app" {
  cluster_id          = yandex_mdb_postgresql_cluster.main.id
  name                = var.postgresql_username
  password_wo         = var.postgresql_app_password
  password_wo_version = var.postgresql_password_version
  conn_limit          = 50
  deletion_protection = var.foundation_deletion_protection
}

resource "yandex_mdb_postgresql_database" "app" {
  cluster_id = yandex_mdb_postgresql_cluster.main.id
  name       = var.postgresql_database_name
  owner      = yandex_mdb_postgresql_user.app.name

  depends_on = [yandex_mdb_postgresql_user.app]
}

resource "yandex_compute_instance" "app" {
  folder_id                 = var.folder_id
  name                      = "${var.project_name}-app-01"
  hostname                  = "${var.project_name}-app-01"
  zone                      = var.app_zone
  platform_id               = var.vm_platform_id
  service_account_id        = yandex_iam_service_account.app.id
  allow_stopping_for_update = true
  labels                    = local.common_labels

  resources {
    cores         = var.vm_cores
    memory        = var.vm_memory_gb
    core_fraction = 100
  }

  boot_disk {
    initialize_params {
      image_id = data.yandex_compute_image.ubuntu.id
      type     = "network-ssd"
      size     = var.vm_disk_gb
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.app.id
    nat                = true
    nat_ip_address     = yandex_vpc_address.app.external_ipv4_address[0].address
    security_group_ids = [yandex_vpc_security_group.app.id]
  }

  metadata = {
    serial-port-enable = "0"
    user-data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
      admin_username              = var.admin_username
      ssh_public_key              = var.ssh_public_key
      lockbox_secret_id              = yandex_lockbox_secret.runtime.id
      field_test_backup_secret_id    = var.field_test_resources_enabled ? yandex_lockbox_secret.field_test_storage[0].id : ""
      field_test_backup_bucket       = var.field_test_resources_enabled ? yandex_storage_bucket.field_test[0].bucket : ""
      primary_pg_rw_fqdn             = "c-${yandex_mdb_postgresql_cluster.main.id}.rw.mdb.yandexcloud.net"
      field_test_restore_rw_fqdn     = var.field_test_resources_enabled ? "c-${yandex_mdb_postgresql_cluster.field_test_restore[0].id}.rw.mdb.yandexcloud.net" : ""
    })
  }

  scheduling_policy {
    preemptible = false
  }

  depends_on = [yandex_lockbox_secret_iam_member.runtime_payload]
}

# Stage C field-test resources are explicitly opt-in. They are synthetic-only,
# bounded, and absent from the default launch plan.
resource "yandex_resourcemanager_folder_iam_member" "field_test_storage_uploader" {
  count       = var.field_test_resources_enabled ? 1 : 0
  folder_id   = var.folder_id
  role        = "storage.uploader"
  member      = "serviceAccount:${yandex_iam_service_account.app.id}"
  sleep_after = 5
}

resource "yandex_lockbox_secret" "field_test_storage" {
  count               = var.field_test_resources_enabled ? 1 : 0
  folder_id           = var.folder_id
  name                = "${var.project_name}-field-test-storage"
  description         = "Temporary Stage C Object Storage static access key; payload managed by Terraform provider output_to_lockbox."
  deletion_protection = false
  labels              = local.common_labels
}

resource "yandex_lockbox_secret_iam_member" "field_test_storage_payload" {
  count     = var.field_test_resources_enabled ? 1 : 0
  secret_id = yandex_lockbox_secret.field_test_storage[0].id
  role      = "lockbox.payloadViewer"
  member    = "serviceAccount:${yandex_iam_service_account.app.id}"
}

resource "yandex_iam_service_account_static_access_key" "field_test_storage" {
  count              = var.field_test_resources_enabled ? 1 : 0
  service_account_id = yandex_iam_service_account.app.id
  description        = "Temporary Stage C access key for synthetic encrypted backup uploads."

  output_to_lockbox {
    secret_id            = yandex_lockbox_secret.field_test_storage[0].id
    entry_for_access_key = "BACKUP_S3_ACCESS_KEY"
    entry_for_secret_key = "BACKUP_S3_SECRET_KEY"
  }

  depends_on = [
    yandex_resourcemanager_folder_iam_member.field_test_storage_uploader,
    yandex_lockbox_secret_iam_member.field_test_storage_payload,
  ]
}

resource "yandex_storage_bucket" "field_test" {
  count                 = var.field_test_resources_enabled ? 1 : 0
  folder_id             = var.folder_id
  bucket_prefix         = var.field_test_bucket_prefix
  default_storage_class = "STANDARD"
  max_size              = var.field_test_bucket_max_size_bytes
  force_destroy         = true

  anonymous_access_flags {
    read        = false
    list        = false
    config_read = false
  }

  lifecycle_rule {
    id      = "stage-c-expire-synthetic-backups"
    enabled = true

    expiration {
      days = 1
    }

    abort_incomplete_multipart_upload_days = 1
  }
}

resource "yandex_mdb_postgresql_cluster" "field_test_restore" {
  count               = var.field_test_resources_enabled ? 1 : 0
  folder_id           = var.folder_id
  name                = "${var.project_name}-restore-drill"
  environment         = "PRODUCTION"
  network_id          = yandex_vpc_network.main.id
  security_group_ids  = [yandex_vpc_security_group.database.id]
  deletion_protection = false
  labels              = merge(local.common_labels, { purpose = "stage-c-restore-drill" })

  config {
    version = 18

    resources {
      resource_preset_id = var.field_test_restore_resource_preset_id
      disk_type_id       = var.postgresql_disk_type_id
      disk_size          = var.field_test_restore_disk_size_gb
    }
  }

  host {
    zone             = var.app_zone
    subnet_id        = yandex_vpc_subnet.app.id
    assign_public_ip = false
  }
}

resource "yandex_mdb_postgresql_user" "field_test_restore" {
  count               = var.field_test_resources_enabled ? 1 : 0
  cluster_id          = yandex_mdb_postgresql_cluster.field_test_restore[0].id
  name                = "aca_restore"
  password_wo         = var.field_test_restore_password
  password_wo_version = 1
  conn_limit          = 10
  deletion_protection = false
}

resource "yandex_mdb_postgresql_database" "field_test_restore" {
  count      = var.field_test_resources_enabled ? 1 : 0
  cluster_id = yandex_mdb_postgresql_cluster.field_test_restore[0].id
  name       = "aca_restore"
  owner      = yandex_mdb_postgresql_user.field_test_restore[0].name

  depends_on = [yandex_mdb_postgresql_user.field_test_restore]
}
