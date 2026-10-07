#!/usr/bin/env python3
"""Dependency-free HOST-001 Yandex Cloud Russia package guard."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "infra/yandex-cloud/versions.tf",
    "infra/yandex-cloud/variables.tf",
    "infra/yandex-cloud/main.tf",
    "infra/yandex-cloud/outputs.tf",
    "infra/yandex-cloud/cloud-init.yaml.tftpl",
    "infra/yandex-cloud/terraform.tfvars.example",
    "infra/yandex-cloud/terraform.stage-c.tfvars.example",
    "infra/yandex-cloud/Caddyfile",
    "infra/yandex-cloud/compose.yaml",
    "infra/yandex-cloud/Dockerfile.ops",
    "infra/yandex-cloud/export_backup_s3.py",
    "infra/yandex-cloud/run_with_lockbox.py",
    "infra/yandex-cloud/README.md",
    "docs/LEGAL001_OWNER_DECISIONS_20260924.md",
    "docs/HOST001_SCOPE.md",
    "docs/HOST001_IMPLEMENTATION.md",
    "docs/HOST001_STAGE_B_IMPLEMENTATION_20261006.md",
    "docs/HOST001_STAGE_C_FIELD_TEST_PLAN_20261006.md",
    "docs/HOST001_RUNBOOK.md",
    "docs/HOST001_VERIFICATION_STATUS.md",
    ".github/workflows/host001-yandex-cloud.yml",
    ".github/workflows/host001-stage-c-plan.yml",
)

STAGE_C_SECRET_BINDINGS = {
    "YC_STAGE_C_SERVICE_ACCOUNT_KEY_JSON": "Materialize Yandex service-account key outside repository",
    "YC_STAGE_C_CLOUD_ID": "Credentialed Stage C plan",
    "YC_STAGE_C_FOLDER_ID": "Credentialed Stage C plan",
    "YC_STAGE_C_ADMIN_CIDR": "Credentialed Stage C plan",
    "YC_STAGE_C_SSH_PUBLIC_KEY": "Credentialed Stage C plan",
    "YC_STAGE_C_POSTGRES_PASSWORD": "Credentialed Stage C plan",
    "YC_STAGE_C_RESTORE_PASSWORD": "Credentialed Stage C plan",
}


def _stage_c_steps(workflow: str) -> dict[str, str]:
    """Return named Stage C step blocks without requiring a YAML dependency."""
    matches = list(re.finditer(r"(?m)^      - name: (.+)$", workflow))
    return {
        match.group(1): workflow[match.start() : matches[index + 1].start()]
        if index + 1 < len(matches)
        else workflow[match.start() :]
        for index, match in enumerate(matches)
    }


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def validate(root: Path = ROOT) -> list[str]:
    global ROOT
    previous = ROOT
    ROOT = root.resolve()
    errors: list[str] = []
    try:
        for relative in REQUIRED:
            if not (ROOT / relative).is_file():
                errors.append("missing required HOST-001 file: " + relative)
        if errors:
            return errors

        versions = _read("infra/yandex-cloud/versions.tf")
        if 'version = "= 0.229.0"' not in versions:
            errors.append("Yandex Terraform provider must be pinned to reviewed 0.229.0")
        if ">= 1.11.0" not in versions:
            errors.append("Terraform 1.11+ is required for password_wo")

        variables = _read("infra/yandex-cloud/variables.tf")
        for marker in (
            'default     = "ru-central1-d"',
            'default     = "ru-central1-b"',
            'default     = "single"',
            'contains(["single", "two"], var.postgresql_host_profile)',
            'variable "foundation_deletion_protection"',
            'variable "field_test_resources_enabled"',
            'variable "field_test_restore_password"',
            'field_test_bucket_max_size_bytes',
            'var.admin_cidr != "0.0.0.0/0"',
            'sensitive   = true',
            'default     = "ubuntu-2404-lts"',
        ):
            if marker not in variables:
                errors.append("HOST-001 variables missing control: " + marker)

        main = _read("infra/yandex-cloud/main.tf")
        required_main = (
            'resource "yandex_vpc_address" "app"',
            "deletion_protection = var.foundation_deletion_protection",
            'resource "yandex_mdb_postgresql_cluster" "main"',
            "version                   = 18",
            'dynamic "host"',
            'var.postgresql_host_profile == "two"',
            "assign_public_ip = false",
            'port              = 6432',
            "security_group_id = yandex_vpc_security_group.app.id",
            'resource "yandex_mdb_postgresql_user" "app"',
            "password_wo         = var.postgresql_app_password",
            'resource "yandex_lockbox_secret" "runtime"',
            'role      = "lockbox.payloadViewer"',
            "service_account_id        = yandex_iam_service_account.app.id",
            "nat_ip_address     = yandex_vpc_address.app.external_ipv4_address[0].address",
            'resource "yandex_storage_bucket" "field_test"',
            'resource "yandex_iam_service_account_static_access_key" "field_test_storage"',
            'output_to_lockbox {',
            'role        = "storage.uploader"',
            'resource "yandex_mdb_postgresql_cluster" "field_test_restore"',
            'name                = "${var.project_name}-restore-drill"',
            'field_test_resources_enabled ? 1 : 0',
            'force_destroy         = true',
            'deletion_protection = false',
            '!var.field_test_resources_enabled || !var.foundation_deletion_protection',
        )
        for marker in required_main:
            if marker not in main:
                errors.append("HOST-001 Terraform missing control: " + marker)
        if "yandex_lockbox_secret_version" in main:
            errors.append("Terraform must not create Lockbox payload values")
        if re.search(r'(?i)(api[_-]?key|client_secret|password)\s*=\s*"[^"$\n]+?"', main):
            errors.append("Terraform main contains an apparent hard-coded secret")

        compose = _read("infra/yandex-cloud/compose.yaml")
        for marker in (
            "DATABASE_URL: ${DATABASE_URL:?Load DATABASE_URL from Lockbox}",
            'AI_ENABLED: "0"',
            'AI_KILL_SWITCH: "1"',
            'AI_SYNTHETIC_ACCESS_ENABLED: "0"',
            'profiles: ["migration"]',
            'profiles: ["writers"]',
            'profiles: ["backup-export"]',
            "PGSSLMODE: verify-full",
            "PGSSLROOTCERT: /etc/ssl/certs/yandex-cloud-ca.pem",
            "PGTARGETSESSIONATTRS: read-write",
            "yandex-cloud-ca.pem",
        ):
            if marker not in compose:
                errors.append("Yandex Compose missing fail-closed control: " + marker)
        if "postgres:17" in compose or "\n  db:" in compose:
            errors.append("Yandex Compose must use Managed PostgreSQL, not a local db service")

        if "depends_on:\n      migrate:" in compose:
            errors.append("Default Yandex services must not auto-run schema migration before restore verification")
        for export_name in (
            "BACKUP_EXPORT_FILE",
            "BACKUP_EXPORT_MANIFEST",
            "BACKUP_S3_PRESIGNED_URL",
            "BACKUP_S3_MANIFEST_PRESIGNED_URL",
            "BACKUP_S3_BUCKET",
            "BACKUP_S3_ACCESS_KEY",
            "BACKUP_S3_SECRET_KEY",
        ):
            if "${" + export_name + ":?" in compose:
                errors.append("Inactive backup-export profile must not require " + export_name + " during Compose interpolation")
            if "${" + export_name + ":-}" not in compose:
                errors.append("Backup-export variable must be deferred to runtime validation: " + export_name)

        ops_docker = _read("infra/yandex-cloud/Dockerfile.ops")
        for marker in ("FROM postgres:18-bookworm", "USER app", "curl"):
            if marker not in ops_docker:
                errors.append("Yandex PG18 ops image missing: " + marker)

        caddy = _read("infra/yandex-cloud/Caddyfile")
        for marker in ("header_up -CF-Connecting-IP", "header_up X-Forwarded-For {http.request.remote.host}"):
            if marker not in caddy:
                errors.append("Yandex proxy hardening missing: " + marker)

        loader = _read("infra/yandex-cloud/run_with_lockbox.py")
        for marker in (
            "169.254.169.254",
            "payload.lockbox.api.cloud.yandex.net",
            "os.execvpe",
            "Metadata-Flavor",
            "validate_database_url",
            "verify-full",
            "sslrootcert",
            "target_session_attrs",
        ):
            if marker not in loader:
                errors.append("Lockbox runtime loader missing: " + marker)
        if "print(" in loader:
            errors.append("Lockbox runtime loader must not print payload or environment")

        exporter = _read("infra/yandex-cloud/export_backup_s3.py")
        for marker in (
            "https",
            "encrypted",
            "curl",
            "sha256",
            "ACAOPS1",
            "AES-GCM",
            "BACKUP_ENCRYPTION_KEY",
            "authenticate_encrypted_backup",
            "TimeoutExpired",
            "validate_distinct_object_targets",
            ".storage.yandexcloud.net",
            "storage.yandexcloud.net",
            "AWS4-HMAC-SHA256",
            "generate_presigned_put_url",
            "BACKUP_S3_ACCESS_KEY",
            "BACKUP_S3_SECRET_KEY",
        ):
            if marker not in exporter:
                errors.append("Off-VM encrypted backup exporter missing: " + marker)

        for document in (
            _read("infra/yandex-cloud/README.md"),
            _read("docs/HOST001_RUNBOOK.md"),
        ):
            if "run --rm --build migrate" not in document:
                errors.append("HOST-001 migration instructions must target only the migrate service")
            if "--profile migration up" in document and "Do not use" not in document:
                errors.append("HOST-001 must not recommend broad migration-profile startup")

        stage_b = _read("docs/HOST001_STAGE_B_IMPLEMENTATION_20261006.md")
        for marker in ("PostgreSQL 18", "single", "two", "NOT_RUN", "20261002_0023"):
            if marker not in stage_b:
                errors.append("HOST-001 Stage B successor record missing: " + marker)

        stage_c = _read("docs/HOST001_STAGE_C_FIELD_TEST_PLAN_20261006.md")
        for marker in (
            "field_test_resources_enabled",
            "foundation_deletion_protection=false",
            "500 RUB",
            "Object Storage",
            "restore",
            "Trudvsem",
            "NOT_AUTHORIZED",
        ):
            if marker not in stage_c:
                errors.append("HOST-001 Stage C plan missing: " + marker)

        stage_c_tfvars = _read("infra/yandex-cloud/terraform.stage-c.tfvars.example")
        for marker in (
            "field_test_resources_enabled  = true",
            "foundation_deletion_protection = false",
            "TF_VAR_field_test_restore_password",
        ):
            if marker not in stage_c_tfvars:
                errors.append("HOST-001 Stage C tfvars example missing: " + marker)

        decisions = _read("docs/LEGAL001_OWNER_DECISIONS_20260924.md")
        for marker in (
            "Россия",
            "**18+**",
            "Free + платный Standard",
            "eletov215@gmail.com",
            "**Yandex Cloud, регион Россия**",
            "PENDING / не выбран",
            "PENDING / не определены",
        ):
            if marker not in decisions:
                errors.append("Owner decision record missing: " + marker)

        if "REAL_DATA_SUPPORTED = False" not in _read("domain/ai.py"):
            errors.append("HOST-001 must not open real-data AI")
        policy = _read("services/legal_policy.py")
        if 'release_state="DRAFT"' not in policy:
            errors.append("HOST-001 must not activate legal policy")

        workflow = _read(".github/workflows/host001-yandex-cloud.yml")
        for marker in (
            "cryptography==48.0.1",
            "fmt -check -diff -recursive",
            "init -backend=false",
            "terraform -chdir=infra/yandex-cloud validate",
            "check_host001_package.py",
        ):
            if marker not in workflow:
                errors.append("HOST-001 workflow missing: " + marker)
        if re.search(r"(?m)^\s*terraform\s+apply\b", workflow):
            errors.append("HOST-001 CI must never terraform apply")
        if "YC_TOKEN" in workflow or "TF_VAR_postgresql_app_password" in workflow:
            errors.append("HOST-001 validation CI must not require cloud/provider secrets")

        stage_c_workflow = _read(".github/workflows/host001-stage-c-plan.yml")
        job_env = stage_c_workflow.split("    env:\n", 1)[1].split("    steps:\n", 1)[0]
        if "secrets." in job_env:
            errors.append("Stage C credentials must not be scoped at job level")

        stage_c_steps = _stage_c_steps(stage_c_workflow)
        for secret, expected_step in STAGE_C_SECRET_BINDINGS.items():
            binding = "${{ secrets." + secret + " }}"
            if stage_c_workflow.count(binding) != 1:
                errors.append(f"Stage C secret {secret} must be bound exactly once")
            elif binding not in stage_c_steps.get(expected_step, ""):
                errors.append(f"Stage C secret {secret} is bound to the wrong step")

        for action, revision in re.findall(r"(?m)^\s*- uses: ([^@\s]+)@([^\s#]+)", stage_c_workflow):
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                errors.append(f"Stage C action {action} must use an immutable commit SHA")
        if re.search(r"(?m)^\s*(?:sudo\s+)?terraform(?:\s+-chdir=\S+)?\s+(?:apply|destroy)\b", stage_c_workflow):
            errors.append("Stage C workflow must never run terraform apply or destroy")
        if re.search(r"(?m)^\s*- uses: actions/upload-artifact@", stage_c_workflow):
            errors.append("Stage C workflow must not upload artifacts")

        return errors
    finally:
        ROOT = previous


def main() -> int:
    errors = validate()
    print(json.dumps({"package": "HOST-001", "ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
