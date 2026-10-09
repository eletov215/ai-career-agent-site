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
    "infra/yandex-cloud/stage_c_state_guard.py",
    "infra/yandex-cloud/stage_c_apply_diagnostics.py",
    "infra/yandex-cloud/run_with_lockbox.py",
    "scripts/host001_stage_c_fixture.py",
    "infra/yandex-cloud/README.md",
    "docs/LEGAL001_OWNER_DECISIONS_20260924.md",
    "docs/HOST001_SCOPE.md",
    "docs/HOST001_IMPLEMENTATION.md",
    "docs/HOST001_STAGE_B_IMPLEMENTATION_20261006.md",
    "docs/HOST001_STAGE_C_FIELD_TEST_PLAN_20261006.md",
    "docs/HOST001_STAGE_C_OPERATOR_CHECKLIST_20261008.md",
    "docs/HOST001_RUNBOOK.md",
    "docs/HOST001_VERIFICATION_STATUS.md",
    ".github/workflows/host001-yandex-cloud.yml",
    ".github/workflows/host001-stage-c-plan.yml",
    ".github/workflows/host001-stage-c-apply.yml",
    ".github/workflows/host001-stage-c-teardown.yml",
)

STAGE_C_SECRET_BINDINGS = {
    "YC_STAGE_C_SERVICE_ACCOUNT_KEY_JSON": "Materialize Yandex service-account key outside repository",
    "YC_STAGE_C_TFSTATE_BUCKET": "Credentialed Stage C plan",
    "YC_STAGE_C_TFSTATE_ACCESS_KEY": "Credentialed Stage C plan",
    "YC_STAGE_C_TFSTATE_SECRET_KEY": "Credentialed Stage C plan",
    "YC_STAGE_C_CLOUD_ID": "Credentialed Stage C plan",
    "YC_STAGE_C_FOLDER_ID": "Credentialed Stage C plan",
    "YC_STAGE_C_ADMIN_CIDR": "Credentialed Stage C plan",
    "YC_STAGE_C_SSH_PUBLIC_KEY": "Credentialed Stage C plan",
    "YC_STAGE_C_POSTGRES_PASSWORD": "Credentialed Stage C plan",
    "YC_STAGE_C_RESTORE_PASSWORD": "Credentialed Stage C plan",
}

STAGE_C_APPLY_SECRET_BINDINGS = {
    "YC_STAGE_C_SERVICE_ACCOUNT_KEY_JSON": (
        "Materialize Yandex service-account key outside repository",
    ),
    "YC_STAGE_C_TFSTATE_BUCKET": (
        "Initialize durable Yandex Object Storage backend",
        "Refuse overlapping Stage C lifecycle from durable remote state",
        "Fresh reviewed Stage C plan",
    ),
    "YC_STAGE_C_TFSTATE_ACCESS_KEY": (
        "Initialize durable Yandex Object Storage backend",
        "Refuse overlapping Stage C lifecycle from durable remote state",
        "Fresh reviewed Stage C plan",
        "Apply reviewed Stage C plan",
    ),
    "YC_STAGE_C_TFSTATE_SECRET_KEY": (
        "Initialize durable Yandex Object Storage backend",
        "Refuse overlapping Stage C lifecycle from durable remote state",
        "Fresh reviewed Stage C plan",
        "Apply reviewed Stage C plan",
    ),
    "YC_STAGE_C_CLOUD_ID": (
        "Fresh reviewed Stage C plan",
    ),
    "YC_STAGE_C_FOLDER_ID": (
        "Fresh reviewed Stage C plan",
    ),
    "YC_STAGE_C_ADMIN_CIDR": (
        "Fresh reviewed Stage C plan",
    ),
    "YC_STAGE_C_SSH_PUBLIC_KEY": (
        "Fresh reviewed Stage C plan",
    ),
    "YC_STAGE_C_POSTGRES_PASSWORD": (
        "Fresh reviewed Stage C plan",
    ),
    "YC_STAGE_C_RESTORE_PASSWORD": (
        "Fresh reviewed Stage C plan",
    ),
}

STAGE_C_TEARDOWN_SECRET_BINDINGS = {
    "YC_STAGE_C_SERVICE_ACCOUNT_KEY_JSON": (
        "Materialize Yandex service-account key outside repository",
    ),
    "YC_STAGE_C_TFSTATE_BUCKET": (
        "Initialize durable Yandex Object Storage backend",
    ),
    "YC_STAGE_C_TFSTATE_ACCESS_KEY": (
        "Initialize durable Yandex Object Storage backend",
        "Destroy reviewed Stage C resources from remote state",
    ),
    "YC_STAGE_C_TFSTATE_SECRET_KEY": (
        "Initialize durable Yandex Object Storage backend",
        "Destroy reviewed Stage C resources from remote state",
    ),
    "YC_STAGE_C_CLOUD_ID": (
        "Destroy reviewed Stage C resources from remote state",
    ),
    "YC_STAGE_C_FOLDER_ID": (
        "Destroy reviewed Stage C resources from remote state",
    ),
    "YC_STAGE_C_ADMIN_CIDR": (
        "Destroy reviewed Stage C resources from remote state",
    ),
    "YC_STAGE_C_SSH_PUBLIC_KEY": (
        "Destroy reviewed Stage C resources from remote state",
    ),
    "YC_STAGE_C_POSTGRES_PASSWORD": (
        "Destroy reviewed Stage C resources from remote state",
    ),
    "YC_STAGE_C_RESTORE_PASSWORD": (
        "Destroy reviewed Stage C resources from remote state",
    ),
}

def _stage_c_steps(workflow: str) -> dict[str, str]:
    """Return named Stage C steps, bounded by every YAML step entry."""
    boundaries = list(re.finditer(r"(?m)^      - (?=\S)", workflow))
    steps: dict[str, str] = {}
    for index, boundary in enumerate(boundaries):
        end = boundaries[index + 1].start() if index + 1 < len(boundaries) else len(workflow)
        block = workflow[boundary.start() : end]
        name = re.match(r"      - name: (.+)$", block.splitlines()[0])
        if name:
            steps[name.group(1)] = block
    return steps


def _active_yaml(workflow: str) -> str:
    """Return YAML source with YAML comment text excluded."""
    return "\n".join(line.split("#", 1)[0] for line in workflow.splitlines())


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
            "1,000 RUB",
            "OWNER_AUTHORIZED",
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
        active_stage_c_workflow = _active_yaml(stage_c_workflow)
        for secret, expected_step in STAGE_C_SECRET_BINDINGS.items():
            binding = "${{ secrets." + secret + " }}"
            active_step = _active_yaml(stage_c_steps.get(expected_step, ""))
            if active_stage_c_workflow.count(binding) != 1:
                errors.append(f"Stage C secret {secret} must be bound exactly once")
            elif binding not in active_step:
                errors.append(f"Stage C secret {secret} is bound to the wrong step")
            if (
                not re.search(r"(?m)^        shell:\s*\S+", active_step)
                or not re.search(r"(?m)^        run:\s*", active_step)
                or re.search(r"(?m)^        uses:\s*", active_step)
            ):
                errors.append(f"Stage C secret {secret} must be bound to a trusted shell step")

        actions = re.findall(
            r"(?m)^\s+(?:-\s+)?uses:\s*([^@\s]+)@([^\s#]+)", active_stage_c_workflow
        )
        for action, revision in actions:
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                errors.append(f"Stage C action {action} must use an immutable commit SHA")
        if re.search(r"(?m)^\s*(?:sudo\s+)?terraform(?:\s+-chdir=\S+)?\s+(?:apply|destroy)\b", stage_c_workflow):
            errors.append("Stage C workflow must never run terraform apply or destroy")
        if any(action == "actions/upload-artifact" for action, _ in actions):
            errors.append("Stage C workflow must not upload artifacts")
        if 'echo "- Commit: \\`$GITHUB_SHA\\`"' not in stage_c_workflow:
            errors.append("Stage C summary must preserve escaped Markdown around the commit SHA")
        for marker in (
            'TFSTATE_KEY="host001/plan-only-${GITHUB_RUN_ID}.tfstate"',
            '-backend-config="bucket=$TFSTATE_BUCKET"',
            '-backend-config="key=$TFSTATE_KEY"',
            "-lock-timeout=30s",
            "terraform_wrapper: false",
            "Sanitized diagnostic excerpt",
            "rm -rf infra/yandex-cloud/.terraform",
        ):
            if marker not in stage_c_workflow:
                errors.append(
                    "Stage C plan-only workflow missing remote-backend diagnostic control: " + marker
                )
        if "init -backend=false" in stage_c_workflow:
            errors.append("Stage C plan-only workflow must initialize the real remote backend")


        stage_c_apply = _read(".github/workflows/host001-stage-c-apply.yml")
        apply_job_env = stage_c_apply.split("    env:\n", 1)[1].split("    steps:\n", 1)[0]
        if "secrets." in apply_job_env:
            errors.append("Stage C apply credentials must not be scoped at job level")

        apply_steps = _stage_c_steps(stage_c_apply)
        active_stage_c_apply = _active_yaml(stage_c_apply)
        for secret, expected_steps in STAGE_C_APPLY_SECRET_BINDINGS.items():
            binding = "${{ secrets." + secret + " }}"
            if active_stage_c_apply.count(binding) != len(expected_steps):
                errors.append(
                    f"Stage C apply secret {secret} must be bound exactly {len(expected_steps)} time(s)"
                )
                continue
            for expected_step in expected_steps:
                active_step = _active_yaml(apply_steps.get(expected_step, ""))
                if binding not in active_step:
                    errors.append(
                        f"Stage C apply secret {secret} is missing from {expected_step}"
                    )
                if (
                    not re.search(r"(?m)^        shell:\s*\S+", active_step)
                    or not re.search(r"(?m)^        run:\s*", active_step)
                    or re.search(r"(?m)^        uses:\s*", active_step)
                ):
                    errors.append(
                        f"Stage C apply secret {secret} must be bound only to trusted shell steps"
                    )

        apply_actions = re.findall(
            r"(?m)^\s+(?:-\s+)?uses:\s*([^@\s]+)@([^\s#]+)", active_stage_c_apply
        )
        for action, revision in apply_actions:
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                errors.append(
                    f"Stage C apply action {action} must use an immutable commit SHA"
                )
        if any(action in {"actions/upload-artifact", "actions/download-artifact"} for action, _ in apply_actions):
            errors.append("Stage C apply workflow must use remote state, not artifact-carried state")

        required_apply_markers = (
            "workflow_dispatch:",
            "actions: write",
            "group: host001-stage-c-bounded-apply",
            "if: github.ref == 'refs/heads/main'",
            "environment: stage-c-yandex",
            "timeout-minutes: 50",
            "APPLY_STAGE_C_SYNTHETIC_1000_RUB_4H",
            'test "$STAGE_C_HOLD_MINUTES" -le 90',
            'TF_VAR_field_test_resources_enabled: "true"',
            'TF_VAR_foundation_deletion_protection: "false"',
            "Initialize durable Yandex Object Storage backend",
            'TFSTATE_KEY="host001/stage-c-${GITHUB_RUN_ID}.tfstate"',
            '-backend-config="bucket=$TFSTATE_BUCKET"',
            '-backend-config="key=$TFSTATE_KEY"',
            'echo "TFSTATE_KEY=$TFSTATE_KEY" >> "$GITHUB_ENV"',
            "Refuse overlapping Stage C lifecycle from durable remote state",
            "stage_c_state_guard.py --bucket",
            "Sanitized Stage C apply plan diagnostic:",
            "actual exit code: $plan_code",
            "terraform_wrapper: false",
            "Fresh credentialed create-only plan passed.",
            "Dispatch cancellation-surviving teardown before apply",
            "host001-stage-c-teardown.yml/dispatches",
            "AUTO_TEARDOWN_STAGE_C_SYNTHETIC",
            "Apply reviewed Stage C plan",
            'stage_c_apply_diagnostics.py "$apply_log"',
            'apply_code=$?',
            'exit "$apply_code"',
            "Remote Terraform state: **Yandex Object Storage backend active before apply**",
        )
        for marker in required_apply_markers:
            if marker not in stage_c_apply:
                errors.append("Stage C apply workflow missing control: " + marker)

        if re.search(r"(?m)^\s+(?:push|pull_request|schedule):", active_stage_c_apply):
            errors.append("Stage C apply workflow must remain manual workflow_dispatch only")
        if re.search(r"(?m)^\s*terraform(?:\s+-chdir=\S+)?\s+destroy\b", active_stage_c_apply):
            errors.append("Stage C apply workflow must not contain direct destroy")
        apply_commands = re.findall(
            r"(?m)^\s*terraform -chdir=infra/yandex-cloud apply\b", active_stage_c_apply
        )
        if len(apply_commands) != 1:
            errors.append("Stage C apply workflow must have exactly one reviewed create apply")

        apply_step = _active_yaml(apply_steps.get("Apply reviewed Stage C plan", ""))
        if (
            'stage_c_apply_diagnostics.py "$apply_log"' not in apply_step
            or 'exit "$apply_code"' not in apply_step
        ):
            errors.append("Stage C apply failure must print safe classified diagnostics before exiting")

        diagnostic_source = _read("infra/yandex-cloud/stage_c_apply_diagnostics.py")
        for marker in ("REVIEWED_RESOURCES", "ERROR_CLASSES", "Raw provider output withheld"):
            if marker not in diagnostic_source:
                errors.append("Stage C apply diagnostics missing fail-closed control: " + marker)

        dispatch_pos = stage_c_apply.find("Dispatch cancellation-surviving teardown before apply")
        apply_pos = stage_c_apply.find("Apply reviewed Stage C plan")
        if dispatch_pos < 0 or apply_pos < 0 or dispatch_pos >= apply_pos:
            errors.append("Stage C teardown dispatch must occur before Terraform apply")

        versions = _read("infra/yandex-cloud/versions.tf")
        for marker in (
            'backend "s3"',
            's3 = "https://storage.yandexcloud.net"',
            "skip_region_validation      = true",
            "skip_credentials_validation = true",
            "skip_requesting_account_id  = true",
            "skip_s3_checksum            = true",
            "use_lockfile                = true",
        ):
            if marker not in versions:
                errors.append("Stage C remote state backend missing control: " + marker)
        if re.search(r'(?m)^\s*key\s*=\s*"host001/stage-c\.tfstate"\s*$', versions):
            errors.append("Stage C remote state key must be supplied per apply run")

        stage_c_teardown = _read(".github/workflows/host001-stage-c-teardown.yml")
        teardown_job_env = stage_c_teardown.split("    env:\n", 1)[1].split("    steps:\n", 1)[0]
        if "secrets." in teardown_job_env:
            errors.append("Stage C teardown credentials must not be scoped at job level")

        teardown_steps = _stage_c_steps(stage_c_teardown)
        active_stage_c_teardown = _active_yaml(stage_c_teardown)
        for secret, expected_steps in STAGE_C_TEARDOWN_SECRET_BINDINGS.items():
            binding = "${{ secrets." + secret + " }}"
            if active_stage_c_teardown.count(binding) != len(expected_steps):
                errors.append(
                    f"Stage C teardown secret {secret} must be bound exactly {len(expected_steps)} time(s)"
                )
                continue
            for expected_step in expected_steps:
                active_step = _active_yaml(teardown_steps.get(expected_step, ""))
                if binding not in active_step:
                    errors.append(
                        f"Stage C teardown secret {secret} is missing from {expected_step}"
                    )
                if (
                    not re.search(r"(?m)^        shell:\s*\S+", active_step)
                    or not re.search(r"(?m)^        run:\s*", active_step)
                    or re.search(r"(?m)^        uses:\s*", active_step)
                ):
                    errors.append(
                        f"Stage C teardown secret {secret} must be bound only to trusted shell steps"
                    )

        teardown_actions = re.findall(
            r"(?m)^\s+(?:-\s+)?uses:\s*([^@\s]+)@([^\s#]+)", active_stage_c_teardown
        )
        for action, revision in teardown_actions:
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                errors.append(
                    f"Stage C teardown action {action} must use an immutable commit SHA"
                )
        if any(action in {"actions/upload-artifact", "actions/download-artifact"} for action, _ in teardown_actions):
            errors.append("Stage C teardown workflow must recover from remote state, not artifacts")

        required_teardown_markers = (
            "workflow_dispatch:",
            "actions: read",
            "if: github.ref == 'refs/heads/main'",
            "environment: stage-c-yandex",
            "timeout-minutes: 225",
            'group: host001-stage-c-recovery-teardown-${{ inputs.source_run_id }}',
            "AUTO_TEARDOWN_STAGE_C_SYNTHETIC",
            "DESTROY_STAGE_C_SYNTHETIC_1000_RUB",
            'test "$HOLD_MINUTES" -le 90',
            "ref: ${{ inputs.source_sha }}",
            "Initialize durable Yandex Object Storage backend",
            'echo "MANUAL_RECOVERY_STARTED_EPOCH=$(date -u +%s)" >> "$GITHUB_ENV"',
            'grep -Eq',
            "Legacy fixed-key source revisions are not automatically recoverable",
            'TFSTATE_KEY="host001/stage-c-${SOURCE_RUN_ID}.tfstate"',
            "Manual recovery setup deadline reached before Terraform init.",
            "Manual recovery setup deadline reached before Terraform validate.",
            'MANUAL_RECOVERY_STARTED_EPOCH: ${{ env.MANUAL_RECOVERY_STARTED_EPOCH }}',
            "actions/runs/$SOURCE_RUN_ID",
            "Validate source apply run identity before checkout",
            '(data.get("path") or "").split("@", 1)[0] == ".github/workflows/host001-stage-c-apply.yml"',
            "--connect-timeout 5 --max-time 10",
            "Source apply status lookup attempt",
            "SOURCE_RUN_TERMINAL_CONFIRMED=1",
            "Field window shortened to preserve the 90-minute teardown reserve.",
            "Source apply concluded $conclusion; skipping field window and tearing down immediately.",
            "Stale Terraform lock detected after the exact source apply run became terminal",
            "actions/workflows/host001-stage-c-apply.yml/runs?event=workflow_dispatch",
            "Another Stage C apply run is active or queued; refusing force-unlock",
            "force-unlock -force",
            "destroy_plan_deadline",
            "destroy_apply_deadline",
            'STAGE_C_ACKNOWLEDGEMENT: ${{ inputs.acknowledgement }}',
            'if [ "$STAGE_C_ACKNOWLEDGEMENT" = "DESTROY_STAGE_C_SYNTHETIC_1000_RUB" ]; then',
            "MANUAL_RECOVERY_STARTED_EPOCH",
            'deadline_mode="manual-recovery"',
            "Manual recovery destroy-plan deadline reached",
            "Manual recovery destroy deadline reached before destroy apply.",
            "Destroy provider deadline: **<=90 minutes from explicit manual recovery start**",
            "Absolute Stage C destroy-plan deadline reached",
            "Absolute Stage C destroy deadline reached before destroy apply.",
            "timeout --signal=INT --kill-after=30s",
            "-lock-timeout=10m",
            "terraform_wrapper: false",
            "Destroy reviewed Stage C resources from remote state",
            "terraform -chdir=infra/yandex-cloud plan",
            "-destroy",
            "Stage C teardown verified: no managed Terraform resources remain.",
        )
        for marker in required_teardown_markers:
            if marker not in stage_c_teardown:
                errors.append("Stage C teardown workflow missing control: " + marker)

        destroy_step = _active_yaml(
            teardown_steps.get("Destroy reviewed Stage C resources from remote state", "")
        )
        if (
            'SOURCE_RUN_STARTED_AT: ${{ env.SOURCE_APPLY_RUN_STARTED_AT }}' not in destroy_step
            or 'test -n "${SOURCE_RUN_STARTED_AT:-}"' not in destroy_step
        ):
            errors.append(
                "Stage C automatic teardown destroy step must receive the validated source start time"
            )

        if re.search(r"(?m)^\s+(?:push|pull_request|schedule):", active_stage_c_teardown):
            errors.append("Stage C teardown workflow must remain manual workflow_dispatch only")
        if re.search(r"(?m)^\s*terraform(?:\s+-chdir=\S+)?\s+destroy\b", active_stage_c_teardown):
            errors.append("Stage C teardown workflow must use reviewed destroy-plan apply")
        teardown_apply_commands = re.findall(
            r"(?m)^\s*terraform -chdir=infra/yandex-cloud apply\b", active_stage_c_teardown
        )
        if len(teardown_apply_commands) != 1:
            errors.append("Stage C teardown workflow must have exactly one reviewed destroy-plan apply")

        if '"^(data\\\\.yandex_compute_image\\\\.ubuntu' not in stage_c_teardown:
            errors.append("Stage C teardown allowlist regex must preserve jq-safe escaping")

        source_validation_pos = stage_c_teardown.find(
            "Validate source apply run identity before checkout"
        )
        checkout_pos = stage_c_teardown.find(
            "      - uses: actions/checkout@"
        )
        if (
            source_validation_pos < 0
            or checkout_pos < 0
            or source_validation_pos >= checkout_pos
        ):
            errors.append(
                "Stage C teardown must validate the source apply run before checkout"
            )

        return errors
    finally:
        ROOT = previous


def main() -> int:
    errors = validate()
    print(json.dumps({"package": "HOST-001", "ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
