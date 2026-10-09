#!/usr/bin/env python3
"""Fail-closed, credential-free preflight for HOST-001 bounded Stage C apply.

This preflight is only a source/fixture contract. It does not authorize billing,
migrate any database, connect to Yandex/Render/Neon, or run Terraform.
It deliberately blocks any successor Alembic revision until the owner has
separately approved the matching synthetic backup/restore acceptance.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Mapping

if __package__:
    from .host001_stage_c_revision_gate import (
        ROOT,
        StageCRevisionGateError,
        check_checkout_sha,
        check_revision_chain,
    )
else:
    from host001_stage_c_revision_gate import (
        ROOT,
        StageCRevisionGateError,
        check_checkout_sha,
        check_revision_chain,
    )

# Historical Stage C fixture/backup/restore evidence accepts THIS schema.
# Extending this list without independently reviewed synthetic restore evidence
# would turn a schema check into a misleading success claim.
APPROVED_STAGE_C_REVISION = "20261002_0023"

WORKFLOW_GATE_NAME = (
    "Verify synthetic-only Stage C application schema before credentials"
)
WORKFLOW_GATE_CALL = (
    'python scripts/host001_stage_c_apply_gate.py --expected-sha "$GITHUB_SHA"'
)


def verify_accepted_fixture(snapshot: Mapping[str, object]) -> dict[str, str]:
    """Refuse new DB schema/unknown coverage rather than silently broadening Stage C."""
    revision = snapshot.get("revision")
    if revision != APPROVED_STAGE_C_REVISION:
        raise StageCRevisionGateError(
            "Stage C synthetic data/restore acceptance has not been reviewed "
            "for the new Alembic revision. No paid apply."
        )
    if snapshot.get("matching_schema_coverage") != "NOT_PRESENT":
        raise StageCRevisionGateError(
            "M04B matching tables need independent populated-row synthetic "
            "backup/restore acceptance before Stage C apply."
        )
    if snapshot.get("unique_head") is not True:
        raise StageCRevisionGateError("Stage C needs exactly one verified Alembic head.")
    if snapshot.get("fixture_uses_runtime_revision") is not True:
        raise StageCRevisionGateError(
            "Stage C fixture must use the same revision as the application runtime."
        )
    return {
        "revision": APPROVED_STAGE_C_REVISION,
        "matching_schema_coverage": "NOT_PRESENT",
        "fixture_release_contract": "APPROVED_LEGACY_SYNTHETIC_ONLY",
    }


def verify_apply_workflow_binding(source: str) -> None:
    """Check that the same offline preflight runs before any cloud credential use."""
    header = "      - name: " + WORKFLOW_GATE_NAME + "\n"
    if source.count(header) != 1:
        raise StageCRevisionGateError(
            "Stage C manual apply must contain exactly one named offline schema gate."
        )
    pos = source.index(header)
    next_step = re.search(r"(?m)^      - (?=\S)", source[pos + len(header):])
    step = source[pos:pos + len(header) + next_step.start()] if next_step else source[pos:]
    expected_step = (
        header
        + "        shell: bash\n"
        + "        run: |\n"
        + "          set -euo pipefail\n"
        + "          " + WORKFLOW_GATE_CALL + "\n"
    )
    if step.strip() != expected_step.strip():
        raise StageCRevisionGateError(
            "Stage C manual apply preflight command or trusted shell contract changed."
        )
    order = [
        "      - name: Verify exact main execution boundary\n",
        header,
        "      - name: Materialize Yandex service-account key outside repository\n",
        "      - name: Initialize durable Yandex Object Storage backend\n",
        "      - name: Fresh reviewed Stage C plan\n",
        "      - name: Dispatch cancellation-surviving teardown before apply\n",
        "      - name: Apply reviewed Stage C plan\n",
    ]
    if any(source.count(item) != 1 for item in order):
        raise StageCRevisionGateError(
            "Stage C workflow lacks an unambiguous reviewed execution step."
        )
    positions = [source.index(item) for item in order]
    if positions != sorted(positions):
        raise StageCRevisionGateError(
            "Stage C schema gate must precede credentials, Terraform and paid apply."
        )


def preflight(root: Path, expected_sha: str) -> dict[str, str]:
    """Validate source, its release evidence and exact checkout SHA offline."""
    snapshot = check_revision_chain(root)
    accepted = verify_accepted_fixture(snapshot)
    # Keep checkout verification independent of the caller's chosen Git ref.
    exact_sha = check_checkout_sha(root, expected_sha)
    return {
        **accepted,
        "source_commit": exact_sha,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-sha",
        required=True,
        help="Exact full 40-character main Git SHA checked out by the workflow.",
    )
    args = parser.parse_args()
    try:
        result = preflight(ROOT, args.expected_sha)
        workflow_file = ROOT / ".github" / "workflows" / "host001-stage-c-apply.yml"
        verify_apply_workflow_binding(workflow_file.read_text(encoding="utf-8"))
    except (StageCRevisionGateError, OSError) as exc:
        print(json.dumps({
            "package": "HOST-001",
            "gate": "synthetic-apply-preflight",
            "ok": False,
            "reason": str(exc),
            "cloud_calls": 0,
            "database_changes": 0,
            "authorizes_paid_apply": False,
        }, ensure_ascii=False))
        return 1
    print(json.dumps({
        "package": "HOST-001",
        "gate": "synthetic-apply-preflight",
        "ok": True,
        **result,
        "cloud_calls": 0,
        "database_changes": 0,
        "authorizes_paid_apply": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
