#!/usr/bin/env python3
"""Offline-only HOST-001 CI release gate: attest *denial* of unaccepted Stage C.

This unprivileged CI checker is deliberately distinct from the real,
credentialed Stage C apply preflight. It NEVER authorizes paid infrastructure.
For accepted 0023 it requires the real gate to succeed; for an exact, signed
M04B 0024 successor it requires the SAME real gate to fail with precisely the
known 'no paid apply' result, on PR and main alike. Other revisions fail closed.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ai004_m04b_successor import (  # noqa: E402
    M04BSuccessorError, SCHEMA_FROM, SCHEMA_TO, validate_successor,
)
from scripts.host001_stage_c_apply_gate import (  # noqa: E402
    APPROVED_STAGE_C_REVISION, verify_apply_workflow_binding,
)
from scripts.host001_stage_c_revision_gate import (  # noqa: E402
    StageCRevisionGateError, check_checkout_sha, check_revision_chain,
)

DENIAL_REASON = (
    "Stage C synthetic data/restore acceptance has not been reviewed "
    "for the new Alembic revision. No paid apply."
)


class StageCOfflineCIGateError(ValueError):
    """Fixed, secret-free CI failure codes."""


def _run_privileged_preflight(root: Path, expected_sha: str) -> tuple[int, dict[str, Any]]:
    """Invoke the actual credential-free preflight, not a copy of its logic."""
    try:
        process = subprocess.run(
            [
                sys.executable,
                str(root / "scripts/host001_stage_c_apply_gate.py"),
                "--expected-sha", expected_sha,
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        output = json.loads(process.stdout)
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired):
        raise StageCOfflineCIGateError("preflight_unreadable") from None
    if not isinstance(output, dict):
        raise StageCOfflineCIGateError("preflight_unreadable")
    return process.returncode, output


def attest(root: Path, expected_sha: str) -> dict[str, Any]:
    """Only acceptance of a documented safe rejection can make 0024 CI green."""
    snapshot = check_revision_chain(root)
    # 0024's privileged preflight deliberately stops on revision before it
    # checks SHA, therefore CI MUST independently verify the actual checkout.
    check_checkout_sha(root, expected_sha)
    workflow = (root / ".github/workflows/host001-stage-c-apply.yml").read_text(
        encoding="utf-8"
    )
    verify_apply_workflow_binding(workflow)

    if snapshot.get("unique_head") is not True or snapshot.get("fixture_uses_runtime_revision") is not True:
        raise StageCOfflineCIGateError("invalid_revision_chain")

    revision = snapshot.get("revision")
    if revision == SCHEMA_FROM:
        if (APPROVED_STAGE_C_REVISION != SCHEMA_FROM
                or snapshot.get("matching_schema_coverage") != "NOT_PRESENT"):
            raise StageCOfflineCIGateError("legacy_release_boundary_changed")
        expected_code = 0
        expected_json = {
            "package": "HOST-001",
            "gate": "synthetic-apply-preflight",
            "ok": True,
            "revision": SCHEMA_FROM,
            "matching_schema_coverage": "NOT_PRESENT",
            "fixture_release_contract": "APPROVED_LEGACY_SYNTHETIC_ONLY",
            "source_commit": expected_sha,
            "cloud_calls": 0,
            "database_changes": 0,
            "authorizes_paid_apply": False,
        }
        stage_status = "LEGACY_FIXTURE_ACCEPTED_PAID_APPLY_NOT_AUTHORIZED_BY_CI"
    elif revision == SCHEMA_TO:
        if (APPROVED_STAGE_C_REVISION != SCHEMA_FROM
                or snapshot.get("matching_schema_coverage") != "SCHEMA_INVENTORY_ONLY"):
            raise StageCOfflineCIGateError("m04b_privileged_boundary_changed")
        successor = validate_successor(root)
        if (
            successor.get("schema_from") != SCHEMA_FROM
            or successor.get("schema_to") != SCHEMA_TO
            or successor.get("public_real_data_enabled") is not False
            or successor.get("legal_state") != "DRAFT"
            or successor.get("provider_calls") != 0
        ):
            raise StageCOfflineCIGateError("invalid_successor_contract")
        expected_code = 1
        expected_json = {
            "package": "HOST-001",
            "gate": "synthetic-apply-preflight",
            "ok": False,
            "reason": DENIAL_REASON,
            "cloud_calls": 0,
            "database_changes": 0,
            "authorizes_paid_apply": False,
        }
        stage_status = "M04B_SUCCESSOR_ATTESTED_PRIVILEGED_APPLY_DENIED"
    else:
        raise StageCOfflineCIGateError("unreviewed_schema_head")

    rc, output = _run_privileged_preflight(root, expected_sha)
    if rc != expected_code or output != expected_json:
        raise StageCOfflineCIGateError("unexpected_privileged_preflight_result")
    return {
        "package": "HOST-001",
        "gate": "offline-ci-boundary",
        "ok": True,
        "revision": revision,
        "stage_c_status": stage_status,
        "cloud_calls": 0,
        "database_changes": 0,
        "authorizes_paid_apply": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    try:
        result = attest(ROOT, args.expected_sha)
    except (StageCOfflineCIGateError, StageCRevisionGateError,
            M04BSuccessorError, OSError, ValueError) as exc:
        print(json.dumps({
            "package": "HOST-001",
            "gate": "offline-ci-boundary",
            "ok": False,
            "error": str(exc) if isinstance(exc, StageCOfflineCIGateError) else "invalid_release_boundary",
            "cloud_calls": 0,
            "database_changes": 0,
            "authorizes_paid_apply": False,
        }))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
