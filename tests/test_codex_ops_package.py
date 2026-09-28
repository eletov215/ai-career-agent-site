import tempfile
import unittest
from pathlib import Path

from scripts.check_codex_ops_package import ROOT, validate


class CodexOpsPackageTests(unittest.TestCase):
    def test_repository_package_is_valid(self):
        self.assertEqual(validate(), [])

    def test_real_data_boundary_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (
                "AGENTS.md",
                "domain/ai.py",
                "services/legal_policy.py",
            ):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")
            for name in ("issue-delivery", "package-guard-verification", "safety-boundaries"):
                target = root / ".agents" / "skills" / name / "SKILL.md"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    (ROOT / ".agents" / "skills" / name / "SKILL.md").read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            (root / "domain/ai.py").write_text("REAL_DATA_SUPPORTED = True\n", encoding="utf-8")
            self.assertIn("real-data AI boundary changed", validate(root))


if __name__ == "__main__":
    unittest.main()
