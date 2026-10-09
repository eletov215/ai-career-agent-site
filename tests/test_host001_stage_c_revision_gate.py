"""No-cloud regressions for the HOST-001 Stage C Alembic checkout gate."""
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts.host001_stage_c_revision_gate import (
    ROOT,
    StageCRevisionGateError,
    _static_assignment,
    check_checkout_sha,
    check_revision_chain,
)


class Host001StageCRevisionGateTests(unittest.TestCase):
    def test_current_repo_has_one_alembic_head_matching_runtime_and_fixture(self):
        result = check_revision_chain(ROOT)
        self.assertGreaterEqual(result["migration_count"], 23)
        self.assertTrue(result["unique_head"])
        self.assertTrue(result["fixture_uses_runtime_revision"])

    def _isolated_tree(self, path: Path) -> Path:
        root = path / "app"
        (root / "migrations").mkdir(parents=True)
        shutil.copytree(
            ROOT / "migrations" / "versions",
            root / "migrations" / "versions",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        shutil.copyfile(ROOT / "database.py", root / "database.py")
        (root / "scripts").mkdir()
        shutil.copyfile(
            ROOT / "scripts" / "host001_stage_c_fixture.py",
            root / "scripts" / "host001_stage_c_fixture.py",
        )
        return root

    def test_new_alembic_revision_requires_runtime_revision_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._isolated_tree(Path(tmp))
            previous = check_revision_chain(root)["revision"]
            new = "20991231_9999"
            (root / "migrations" / "versions" / f"{new}_synthetic.py").write_text(
                f"revision = '{new}'\ndown_revision = '{previous}'\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                StageCRevisionGateError, "CURRENT_REVISION differs"
            ):
                check_revision_chain(root)

            (root / "database.py").write_text(
                f'CURRENT_REVISION = "{new}"\n', encoding="utf-8"
            )
            self.assertEqual(check_revision_chain(root)["revision"], new)

    def test_parallel_migration_heads_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._isolated_tree(Path(tmp))
            # A second independent head is an unsafe Stage C baseline.
            new = "20991231_9999"
            root_head = check_revision_chain(root)["revision"]
            revision_path = next(
                p
                for p in (root / "migrations" / "versions").glob("*.py")
                if p.name.startswith(root_head + "_")
            )
            old_parent = _static_assignment(revision_path, "down_revision")
            (root / "migrations" / "versions" / f"{new}_fork.py").write_text(
                f"revision = '{new}'\ndown_revision = '{old_parent}'\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(StageCRevisionGateError, "one Alembic head"):
                check_revision_chain(root)

    def test_missing_parent_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._isolated_tree(Path(tmp))
            new = "20991231_9999"
            (root / "migrations" / "versions" / f"{new}_orphan.py").write_text(
                f"revision = '{new}'\ndown_revision = '20000101_0000'\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(StageCRevisionGateError, "missing parent"):
                check_revision_chain(root)

    def test_unpinned_fixture_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._isolated_tree(Path(tmp))
            (root / "scripts" / "host001_stage_c_fixture.py").write_text(
                "CURRENT_REVISION = '20000101_0000'\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(StageCRevisionGateError, "dynamically"):
                check_revision_chain(root)

    def test_checkout_sha_must_match_reviewed_exact_commit(self):
        sha = "a" * 40
        with mock.patch(
            "scripts.host001_stage_c_revision_gate.subprocess.run",
            return_value=SimpleNamespace(stdout=sha + "\n"),
        ) as run:
            self.assertEqual(check_checkout_sha(ROOT, sha), sha)
            with self.assertRaisesRegex(StageCRevisionGateError, "differs"):
                check_checkout_sha(ROOT, "b" * 40)
            self.assertEqual(run.call_count, 2)

    def test_short_or_invalid_commit_is_rejected_before_git(self):
        with mock.patch(
            "scripts.host001_stage_c_revision_gate.subprocess.run"
        ) as run:
            with self.assertRaisesRegex(StageCRevisionGateError, "full 40-character"):
                check_checkout_sha(ROOT, "main")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
