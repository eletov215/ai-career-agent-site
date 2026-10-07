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
    ".github/workflows/host001-stage-c-apply.yml",
    ".github/workflows/host001-stage-c-teardown.yml",
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

STAGE_C_APPLY_SECRET_BINDINGS = {
    "YC_STAGE_C_SERVICE_ACCOUNT_KEY_JSON": (
        "Materialize Yandex service-account key outside repository",
    ),
    "YC_STAGE_C_TFSTATE_BUCKET": (
        "Initialize durable Yandex Object Storage backend",
    ),
    "YC_STAGE_C_TFSTATE_ACCESS_KEY": (
        "Initialize durable Yandex Object Storage backend",
        "Fresh reviewed Stage C plan",
        "Apply reviewed Stage C plan",
    ),
    "YC_STAGE_C_TFSTATE_SECRET_KEY": (
        "Initialize durable Yandex Object Storage backend",
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
            errors.append("Stage C remote state key must be per apply run, not globally fixed")

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
            "group: host001-stage-c-recovery-teardown",
            "AUTO_TEARDOWN_STAGE_C_SYNTHETIC",
            "DESTROY_STAGE_C_SYNTHETIC_1000_RUB",
            'test "$HOLD_MINUTES" -le 90',
            "ref: ${{ inputs.source_sha }}",
            "Initialize durable Yandex Object Storage backend",
            'TFSTATE_KEY="host001/stage-c-${SOURCE_RUN_ID}.tfstate"',
            '-backend-config="key=$TFSTATE_KEY"',
            'echo "TFSTATE_KEY=$TFSTATE_KEY" >> "$GITHUB_ENV"',
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
            "manual_recovery_started",
            'deadline_mode="manual-recovery"',
            "Manual recovery destroy-plan deadline reached",
            "Manual recovery destroy deadline reached before destroy apply.",
            "Destroy provider deadline: **<=90 minutes from explicit manual recovery start**",
            "Absolute Stage C destroy-plan deadline reached",
            "Absolute Stage C destroy deadline reached before destroy apply.",
            "timeout --signal=INT --kill-after=30s",
            "-lock-timeout=10m",
            "Destroy reviewed Stage C resources from remote state",
            "terraform -chdir=infra/yandex-cloud plan",
            "-destroy",
            "Stage C teardown verified: no managed Terraform resources remain.",
        )
        for marker in required_teardown_markers:
            if marker not in stage_c_teardown:
                errors.append("Stage C teardown workflow missing control: " + marker)

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
, versions):
            errors.append("Stage C remote state key must be per apply run, not globally fixed")

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
            "group: host001-stage-c-recovery-teardown",
            "AUTO_TEARDOWN_STAGE_C_SYNTHETIC",
            "DESTROY_STAGE_C_SYNTHETIC_1000_RUB",
            'test "$HOLD_MINUTES" -le 90',
            "ref: ${{ inputs.source_sha }}",
            "Initialize durable Yandex Object Storage backend",
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
            "manual_recovery_started",
            'deadline_mode="manual-recovery"',
            "Manual recovery destroy-plan deadline reached",
            "Manual recovery destroy deadline reached before destroy apply.",
            "Destroy provider deadline: **<=90 minutes from explicit manual recovery start**",
            "Absolute Stage C destroy-plan deadline reached",
            "Absolute Stage C destroy deadline reached before destroy apply.",
            "timeout --signal=INT --kill-after=30s",
            "-lock-timeout=10m",
            "Destroy reviewed Stage C resources from remote state",
            "terraform -chdir=infra/yandex-cloud plan",
            "-destroy",
            "Stage C teardown verified: no managed Terraform resources remain.",
        )
        for marker in required_teardown_markers:
            if marker not in stage_c_teardown:
                errors.append("Stage C teardown workflow missing control: " + marker)

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
, versions):
            errors.append("Stage C remote state key must be per apply run, not globally fixed")

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
            "group: host001-stage-c-recovery-teardown",
            "AUTO_TEARDOWN_STAGE_C_SYNTHETIC",
            "DESTROY_STAGE_C_SYNTHETIC_1000_RUB",
            'test "$HOLD_MINUTES" -le 90',
            "ref: ${{ inputs.source_sha }}",
            "Initialize durable Yandex Object Storage backend",
            'TFSTATE_KEY="host001/stage-c-${SOURCE_RUN_ID}.tfstate"',
            '-backend-config="key=$TFSTATE_KEY"',
            'echo "TFSTATE_KEY=$TFSTATE_KEY" >> "$GITHUB_ENV"',
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
            "manual_recovery_started",
            'deadline_mode="manual-recovery"',
            "Manual recovery destroy-plan deadline reached",
            "Manual recovery destroy deadline reached before destroy apply.",
            "Destroy provider deadline: **<=90 minutes from explicit manual recovery start**",
            "Absolute Stage C destroy-plan deadline reached",
            "Absolute Stage C destroy deadline reached before destroy apply.",
            "timeout --signal=INT --kill-after=30s",
            "-lock-timeout=10m",
            "Destroy reviewed Stage C resources from remote state",
            "terraform -chdir=infra/yandex-cloud plan",
            "-destroy",
            "Stage C teardown verified: no managed Terraform resources remain.",
        )
        for marker in required_teardown_markers:
            if marker not in stage_c_teardown:
                errors.append("Stage C teardown workflow missing control: " + marker)

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
, versions):
            errors.append("Stage C remote state key must be per apply run, not globally fixed")

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
            "group: host001-stage-c-recovery-teardown",
            "AUTO_TEARDOWN_STAGE_C_SYNTHETIC",
            "DESTROY_STAGE_C_SYNTHETIC_1000_RUB",
            'test "$HOLD_MINUTES" -le 90',
            "ref: ${{ inputs.source_sha }}",
            "Initialize durable Yandex Object Storage backend",
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
            "manual_recovery_started",
            'deadline_mode="manual-recovery"',
            "Manual recovery destroy-plan deadline reached",
            "Manual recovery destroy deadline reached before destroy apply.",
            "Destroy provider deadline: **<=90 minutes from explicit manual recovery start**",
            "Absolute Stage C destroy-plan deadline reached",
            "Absolute Stage C destroy deadline reached before destroy apply.",
            "timeout --signal=INT --kill-after=30s",
            "-lock-timeout=10m",
            "Destroy reviewed Stage C resources from remote state",
            "terraform -chdir=infra/yandex-cloud plan",
            "-destroy",
            "Stage C teardown verified: no managed Terraform resources remain.",
        )
        for marker in required_teardown_markers:
            if marker not in stage_c_teardown:
                errors.append("Stage C teardown workflow missing control: " + marker)

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
