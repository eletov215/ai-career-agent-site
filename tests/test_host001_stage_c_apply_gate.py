"""No-cloud tests for the privileged HOST-001 manual Stage C apply preflight."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from scripts import host001_stage_c_apply_gate as gate
from scripts.host001_stage_c_revision_gate import (
    ROOT,
    StageCRevisionGateError,
    check_revision_chain,
)


class Host001StageCApplyGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = (
            ROOT / ".github" / "workflows" / "host001-stage-c-apply.yml"
        ).read_text(encoding="utf-8")

    def test_live_source_fixture_remains_0023_before_successor(self):
        snapshot = check_revision_chain(ROOT)
        accepted = gate.verify_accepted_fixture(snapshot)
        self.assertEqual(accepted["revision"], "20261002_0023")
        self.assertEqual(accepted["matching_schema_coverage"], "NOT_PRESENT")

    def test_matching_successor_is_not_live_stage_c_acceptance(self):
        for revision, coverage in (
            ("20261009_0024", "SCHEMA_INVENTORY_ONLY"),
            ("20261009_0024", "NOT_PRESENT"),
            ("20261002_0023", "SCHEMA_INVENTORY_ONLY"),
            ("20991231_9999", "NOT_PRESENT"),
            ("20261002_0023", "UNKNOWN"),
        ):
            with self.subTest(revision=revision, coverage=coverage):
                with self.assertRaises(StageCRevisionGateError):
                    gate.verify_accepted_fixture({
                        "revision": revision,
                        "matching_schema_coverage": coverage,
                        "unique_head": True,
                        "fixture_uses_runtime_revision": True,
                    })

    def test_missing_or_false_chain_assertions_fail_closed(self):
        base = {
            "revision": "20261002_0023",
            "matching_schema_coverage": "NOT_PRESENT",
            "unique_head": True,
            "fixture_uses_runtime_revision": True,
        }
        for name in ("unique_head", "fixture_uses_runtime_revision"):
            for value in (False, None, "true"):
                with self.subTest(name=name, value=value):
                    case = {**base, name: value}
                    with self.assertRaises(StageCRevisionGateError):
                        gate.verify_accepted_fixture(case)

    def test_preflight_checks_exact_source_sha(self):
        approved_snapshot = {
            "revision": "20261002_0023",
            "matching_schema_coverage": "NOT_PRESENT",
            "unique_head": True,
            "fixture_uses_runtime_revision": True,
        }
        sha = "a" * 40
        with (
            mock.patch.object(gate, "check_revision_chain", return_value=approved_snapshot),
            mock.patch.object(gate, "check_checkout_sha", return_value=sha) as pinned,
        ):
            outcome = gate.preflight(Path("/unused"), sha)
            self.assertEqual(outcome["source_commit"], sha)
            pinned.assert_called_once_with(Path("/unused"), sha)

    def test_preflight_never_bypasses_rejected_schema(self):
        with (
            mock.patch.object(gate, "check_revision_chain", return_value={
                "revision": "20261009_0024",
                "matching_schema_coverage": "SCHEMA_INVENTORY_ONLY",
                "unique_head": True,
                "fixture_uses_runtime_revision": True,
            }),
            mock.patch.object(gate, "check_checkout_sha") as pinned,
        ):
            with self.assertRaisesRegex(StageCRevisionGateError, "not been reviewed"):
                gate.preflight(Path("/unused"), "a" * 40)
            pinned.assert_not_called()

    def test_apply_workflow_has_one_precredentials_readonly_gate(self):
        gate.verify_apply_workflow_binding(self.workflow)
        self.assertEqual(self.workflow.count(gate.WORKFLOW_GATE_CALL), 1)

    def test_removing_or_repositioning_gate_is_rejected(self):
        begin = "      - name: " + gate.WORKFLOW_GATE_NAME + "\n"
        block = (
            begin
            + "        shell: bash\n"
            + "        run: |\n"
            + "          set -euo pipefail\n"
            + "          " + gate.WORKFLOW_GATE_CALL + "\n\n"
        )
        self.assertIn(block, self.workflow)
        mutations = {
            "removed": self.workflow.replace(block, "", 1),
            "duplicated": self.workflow.replace(block, block + block, 1),
            "bypassed": self.workflow.replace(
                gate.WORKFLOW_GATE_CALL,
                gate.WORKFLOW_GATE_CALL + " || true",
                1,
            ),
            "different command": self.workflow.replace(
                gate.WORKFLOW_GATE_CALL,
                "python -m unittest tests.test_host001_stage_c_apply_gate -v",
                1,
            ),
            "after credentials": (
                self.workflow.replace(block, "", 1).replace(
                    "      - name: Initialize durable Yandex Object Storage backend\n",
                    block + "      - name: Initialize durable Yandex Object Storage backend\n",
                    1,
                )
            ),
        }
        for label, changed in mutations.items():
            with self.subTest(label=label):
                with self.assertRaises(StageCRevisionGateError):
                    gate.verify_apply_workflow_binding(changed)

    def test_gate_is_not_a_paid_authorization(self):
        # The operator acknowledgement is a separate manual action, and the
        # Stage C command is not made available to a pull_request event.
        self.assertIn('if: github.ref == \'refs/heads/main\'', self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("APPLY_STAGE_C_SYNTHETIC_1000_RUB_4H", self.workflow)
        self.assertNotIn("\n  pull_request:", self.workflow)
        self.assertNotIn("\n  push:", self.workflow)


if __name__ == "__main__":
    unittest.main()
