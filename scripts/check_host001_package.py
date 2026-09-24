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
    "infra/yandex-cloud/Caddyfile",
    "infra/yandex-cloud/compose.yaml",
    "infra/yandex-cloud/run_with_lockbox.py",
    "infra/yandex-cloud/README.md",
    "docs/LEGAL001_OWNER_DECISIONS_20260924.md",
    "docs/HOST001_SCOPE.md",
    "docs/HOST001_IMPLEMENTATION.md",
    "docs/HOST001_RUNBOOK.md",
    "docs/HOST001_VERIFICATION_STATUS.md",
    ".github/workflows/host001-yandex-cloud.yml",
)


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
            'var.admin_cidr != "0.0.0.0/0"',
            'sensitive   = true',
            'default     = "ubuntu-2404-lts"',
        ):
            if marker not in variables:
                errors.append("HOST-001 variables missing control: " + marker)

        main = _read("infra/yandex-cloud/main.tf")
        required_main = (
            'resource "yandex_vpc_address" "app"',
            "deletion_protection = true",
            'resource "yandex_mdb_postgresql_cluster" "main"',
            "version                   = 17",
            "assign_public_ip = false",
            'port              = 6432',
            "security_group_id = yandex_vpc_security_group.app.id",
            'resource "yandex_mdb_postgresql_user" "app"',
            "password_wo         = var.postgresql_app_password",
            'resource "yandex_lockbox_secret" "runtime"',
            'role      = "lockbox.payloadViewer"',
            "service_account_id        = yandex_iam_service_account.app.id",
            "nat_ip_address     = yandex_vpc_address.app.external_ipv4_address[0].address",
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
            "yandex-cloud-ca.pem",
        ):
            if marker not in compose:
                errors.append("Yandex Compose missing fail-closed control: " + marker)
        if "postgres:17" in compose or "\n  db:" in compose:
            errors.append("Yandex Compose must use Managed PostgreSQL, not a local db service")

        loader = _read("infra/yandex-cloud/run_with_lockbox.py")
        for marker in (
            "169.254.169.254",
            "payload.lockbox.api.cloud.yandex.net",
            "os.execvpe",
            "Metadata-Flavor",
        ):
            if marker not in loader:
                errors.append("Lockbox runtime loader missing: " + marker)
        if "print(" in loader:
            errors.append("Lockbox runtime loader must not print payload or environment")

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
        for marker in ("fmt -check -recursive", "init -backend=false", "terraform -chdir=infra/yandex-cloud validate", "check_host001_package.py"):
            if marker not in workflow:
                errors.append("HOST-001 workflow missing: " + marker)
        if re.search(r"(?m)^\s*terraform\s+apply\b", workflow):
            errors.append("HOST-001 CI must never terraform apply")
        if "YC_TOKEN" in workflow or "TF_VAR_postgresql_app_password" in workflow:
            errors.append("HOST-001 validation CI must not require cloud/provider secrets")

        return errors
    finally:
        ROOT = previous


def main() -> int:
    errors = validate()
    print(json.dumps({"package": "HOST-001", "ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
