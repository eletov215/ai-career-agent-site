"""Dependency-free defense-in-depth for the credentialed HOST-001 plan-only workflow.

This is a conservative static contract, not a general YAML or Bash interpreter.
Unreviewed commands/actions must fail CI rather than be silently permitted.
No cloud credentials or provider calls are needed.
"""
from __future__ import annotations

from collections import Counter
import re


# Each GitHub secret must be bound to exactly this environment variable
# in exactly this reviewed trusted-shell step.
EXPECTED_SECRET_ENV = {
    "YC_STAGE_C_SERVICE_ACCOUNT_KEY_JSON": (
        "Materialize Yandex service-account key outside repository",
        "YC_STAGE_C_SERVICE_ACCOUNT_KEY_JSON",
    ),
    "YC_STAGE_C_TFSTATE_BUCKET": ("Credentialed Stage C plan", "TFSTATE_BUCKET"),
    "YC_STAGE_C_TFSTATE_ACCESS_KEY": ("Credentialed Stage C plan", "AWS_ACCESS_KEY_ID"),
    "YC_STAGE_C_TFSTATE_SECRET_KEY": ("Credentialed Stage C plan", "AWS_SECRET_ACCESS_KEY"),
    "YC_STAGE_C_CLOUD_ID": ("Credentialed Stage C plan", "TF_VAR_cloud_id"),
    "YC_STAGE_C_FOLDER_ID": ("Credentialed Stage C plan", "TF_VAR_folder_id"),
    "YC_STAGE_C_ADMIN_CIDR": ("Credentialed Stage C plan", "TF_VAR_admin_cidr"),
    "YC_STAGE_C_SSH_PUBLIC_KEY": ("Credentialed Stage C plan", "TF_VAR_ssh_public_key"),
    "YC_STAGE_C_POSTGRES_PASSWORD": (
        "Credentialed Stage C plan",
        "TF_VAR_postgresql_app_password",
    ),
    "YC_STAGE_C_RESTORE_PASSWORD": (
        "Credentialed Stage C plan",
        "TF_VAR_field_test_restore_password",
    ),
}

REVIEWED_ACTIONS = Counter(("actions/checkout", "hashicorp/setup-terraform"))
REVIEWED_TERRAFORM_OPERATIONS = Counter(("init", "validate", "plan", "show"))
PLAN_COMMAND = (
    'terraform -chdir=infra/yandex-cloud plan -input=false '
    '-lock-timeout=30s -no-color -detailed-exitcode '
    '-out="$plan_file" >"$plan_log" 2>&1'
)

_SECRET_REF = re.compile(
    r"\x24\x7b\x7b[ \t]*secrets\.([a-zA-Z_][a-zA-Z0-9_]*)[ \t]*\x7d\x7d"
)
_ACTION_LINE = re.compile(r"(?m)^[ \t]*(?:-[ \t]*)?uses[ \t]*:[ \t]*(\S+)")
_TERRAFORM = re.compile(r"(?<![\w./-])terraform[ \t]+([^\r\n;|&]*)")


def _active_source(source: str) -> str:
    # Matches the existing package guard convention: YAML comments are not active.
    return "\n".join(line.split("#", 1)[0] for line in source.splitlines())


def _steps(workflow: str) -> dict[str, str]:
    markers = list(re.finditer(r"(?m)^      - (?=\S)", workflow))
    output: dict[str, str] = {}
    for index, marker in enumerate(markers):
        limit = markers[index + 1].start() if index + 1 < len(markers) else len(workflow)
        block = workflow[marker.start():limit]
        match = re.match(r"      - name: ([^\n]+)", block)
        if match:
            # Duplicate names are not acceptable as identity for secret bindings.
            if match.group(1) in output:
                raise ValueError("Duplicate Stage C step name.")
            output[match.group(1)] = block
    return output


def _shell_scripts(steps: dict[str, str]) -> str:
    scripts = []
    for block in steps.values():
        start = re.search(r"(?m)^        run: \|[ \t]*$", block)
        if start is not None:
            scripts.append(block[start.end():])
        elif re.search(r"(?m)^        run:", block):
            # An inline or folded run is not part of the reviewed shell contract.
            raise ValueError("Unreviewed Stage C shell run syntax.")
    return "\n".join(scripts)


def validate_plan_only_hardening(workflow: str) -> list[str]:
    """Enforce Issue #80 without executing workflow or interpreting secrets."""
    errors: list[str] = []
    active = _active_source(workflow)
    try:
        steps = _steps(active)
        shell_source = _shell_scripts(steps)
    except ValueError as exc:
        return [str(exc)]

    # 1. Every active uses: must be an approved repository action at an immutable
    # commit, not an unknown/local/container action or an expression.
    uses = _ACTION_LINE.findall(active)
    if len(uses) != len(re.findall(r"\buses[ \t]*:", active)):
        errors.append("Stage C action syntax is not explicitly reviewed.")
    actions: list[str] = []
    for value in uses:
        match = re.fullmatch(r"([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)@([0-9a-f]{40})", value)
        if match is None:
            errors.append("Stage C contains an unpinned or unsupported action.")
        else:
            actions.append(match.group(1))
    if Counter(actions) != REVIEWED_ACTIONS:
        errors.append("Stage C action set differs from reviewed checkout/terraform setup.")

    # 2. Enforce exact secret-to-env mapping; presence in a trusted step alone
    # does not prove that Terraform receives the intended credential.
    referenced = _SECRET_REF.findall(active)
    if Counter(referenced) != Counter(EXPECTED_SECRET_ENV.keys()):
        errors.append("Stage C contains missing, duplicated or unexpected secrets.")
    if re.search(r"\bsecrets[ \t]*\[", active):
        errors.append("Stage C contains an unreviewed indexed secrets expression.")
    for secret, (step, env_name) in EXPECTED_SECRET_ENV.items():
        block = steps.get(step, "")
        expression = chr(36) + "{{ secrets." + secret + " }}"
        expected_line = "          " + env_name + ": " + expression
        if len(re.findall(r"(?m)^" + re.escape(expected_line) + r"[ \t]*$", block)) != 1:
            errors.append(f"Stage C secret {secret} must map to exact env key {env_name}.")

    # 3. Strip only explicit Bash line continuations: this catches commands
    # appended via semicolons, &&, |, and Terraform subcommands on new lines.
    shell = re.sub(r"\\\r?\n[ \t]*", " ", shell_source)
    operations: list[str] = []
    for match in _TERRAFORM.finditer(shell):
        tokens = match.group(1).strip().split()
        while tokens and tokens[0].startswith("-"):
            tokens.pop(0)  # reviewed -chdir=... or future flags are bounded by op count
        operation = tokens[0] if tokens else "UNKNOWN"
        operations.append(operation)
        if operation not in REVIEWED_TERRAFORM_OPERATIONS:
            errors.append("Stage C plan-only contains unreviewed Terraform operation.")
    if Counter(operations) != REVIEWED_TERRAFORM_OPERATIONS:
        errors.append("Stage C plan-only Terraform operation set changed.")

    # 4. Refuse any change to the reviewed single private-log plan command.
    # stdout/stderr must not flow to the Actions log or through tee/pipe.
    plan_step = steps.get("Credentialed Stage C plan", "")
    plan_shell = re.sub(r"\\\r?\n[ \t]*", " ", _shell_scripts(
        {"Credentialed Stage C plan": plan_step}
    ))
    plan_commands = [
        " ".join(line.strip().split())
        for line in plan_shell.splitlines()
        if re.search(r"(?<![\w./-])terraform[ \t]+-chdir=infra/yandex-cloud[ \t]+plan\b", line)
    ]
    if plan_commands != [PLAN_COMMAND]:
        errors.append("Stage C plan stdout/stderr redirection differs from reviewed private log.")
    if len(re.findall(
        r'(?m)^[ \t]*plan_log="\$RUNNER_TEMP/stage-c-plan\.stdout"[ \t]*$',
        plan_shell,
    )) != 1:
        errors.append("Stage C plan private log destination changed.")
    if re.search(r"(?m)^[ \t]*set[ \t]+-[a-zA-Z]*x[a-zA-Z]*\b", shell):
        errors.append("Stage C plan-only may not enable Bash xtrace.")
    if re.search(
        r'(?m)\b(?:cat|tail|head|less|more|tee)\b[^\n]*\bplan_log\b', shell
    ):
        errors.append("Stage C plan-only may not expose unredacted plan logs.")
    return errors
