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
        (root / "operations").mkdir()
        shutil.copyfile(
            ROOT / "operations" / "backup.py",
            root / "operations" / "backup.py",
        )
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

    @staticmethod
    def _minimal_matching_tree(path: Path) -> Path:
        # Independent synthetic baseline; must keep working after M04B merges.
        root = path / "m04b_isolated"
        versions = root / "migrations" / "versions"
        versions.mkdir(parents=True)
        (root / "operations").mkdir()
        (root / "scripts").mkdir()
        (root / "database.py").write_text(
            'CURRENT_REVISION = "20261002_0023"\n', encoding="utf-8"
        )
        (versions / "20261002_0023_base.py").write_text(
            'revision = "20261002_0023"\ndown_revision = None\n',
            encoding="utf-8",
        )
        (root / "operations" / "backup.py").write_text(
            '_INVENTORY_TABLES = ("users",)\n', encoding="utf-8"
        )
        (root / "scripts" / "host001_stage_c_fixture.py").write_text(
            "from database import CURRENT_REVISION\n"
            "def _schema_report(runtime):\n"
            "    selected_tables = (\n"
            '        "users",\n'
            '        "ai_consents",\n'
            "    )\n",
            encoding="utf-8",
        )
        return root

    @staticmethod
    def _add_mock_m04b_migration(root: Path, *, include_cache: bool = True) -> None:
        previous = check_revision_chain(root)["revision"]
        new_revision = "20991231_9999"
        create_cache = '    op.create_table("user_match_cache")\n' if include_cache else ""
        new_migration = (
            f'revision = "{new_revision}"\n'
            f'down_revision = "{previous}"\n'
            "from alembic import op\n"
            "def upgrade():\n"
            '    op.create_table("user_match_reports")\n'
            f"{create_cache}"
        )
        (root / "migrations" / "versions" / f"{new_revision}_m04b.py").write_text(
            new_migration, encoding="utf-8"
        )
        db_file = root / "database.py"
        db_file.write_text(
            db_file.read_text(encoding="utf-8").replace(
                f'CURRENT_REVISION = "{previous}"',
                f'CURRENT_REVISION = "{new_revision}"',
            ),
            encoding="utf-8",
        )

    def test_current_repo_matching_schema_coverage_is_explicit(self):
        result = check_revision_chain(ROOT)
        self.assertIn(
            result["matching_schema_coverage"],
            {"NOT_PRESENT", "SCHEMA_INVENTORY_ONLY"},
        )

    def test_partial_m04b_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._minimal_matching_tree(Path(tmp))
            self._add_mock_m04b_migration(root, include_cache=False)
            with self.assertRaisesRegex(StageCRevisionGateError, "Partial AI004-M04B"):
                check_revision_chain(root)

    def test_m04b_requires_backup_inventory_and_stage_c_schema_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._minimal_matching_tree(Path(tmp))
            self._add_mock_m04b_migration(root)
            with self.assertRaisesRegex(StageCRevisionGateError, "backup inventory"):
                check_revision_chain(root)

            # Simulate M04B's existing backup inventory, without modifying
            # any accepted fixture or the production database.
            (root / "operations" / "backup.py").write_text(
                '_INVENTORY_TABLES = ("user_match_reports", "user_match_cache")\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(StageCRevisionGateError, "schema digest omits"):
                check_revision_chain(root)

            fixture = root / "scripts" / "host001_stage_c_fixture.py"
            before = fixture.read_text(encoding="utf-8")
            anchor = '        "ai_consents",\n    )'
            self.assertIn(anchor, before)
            fixture.write_text(
                before.replace(
                    anchor,
                    '        "ai_consents",\n'
                    '        "user_match_reports",\n'
                    '        "user_match_cache",\n    )',
                ),
                encoding="utf-8",
            )
            result = check_revision_chain(root)
            self.assertEqual(result["matching_schema_coverage"], "SCHEMA_INVENTORY_ONLY")

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
