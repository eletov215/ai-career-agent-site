from __future__ import annotations

import runpy
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackageLayoutTests(unittest.TestCase):
    def test_visible_gate_inputs_are_browser_upload_safe(self) -> None:
        namespace = runpy.run_path(str(ROOT / "scripts/check_ai_bench_package.py"))
        required_visible = tuple(namespace["REQUIRED_VISIBLE"])
        hidden = [
            item
            for item in required_visible
            if any(part.startswith(".") for part in Path(item).parts)
        ]
        self.assertEqual(hidden, [])
        self.assertIn("evals/artifacts/README.md", required_visible)
        self.assertNotIn("evals/.gitignore", required_visible)
        self.assertNotIn("evals/artifacts/.gitkeep", required_visible)

    def test_live_repository_controls_remain_required(self) -> None:
        namespace = runpy.run_path(str(ROOT / "scripts/check_ai_bench_package.py"))
        required_repository = tuple(namespace["REQUIRED_REPOSITORY"])
        self.assertIn(".github/workflows/ai-bench-live.yml", required_repository)
        self.assertIn("scripts/check_ai_bench_live_result.py", required_repository)

    def test_live_workflow_uses_node24_artifact_action(self) -> None:
        workflow = (ROOT / ".github/workflows/ai-bench-live.yml").read_text(encoding="utf-8")
        self.assertIn("uses: actions/upload-artifact@v7", workflow)
        self.assertNotIn("uses: actions/upload-artifact@v4", workflow)
        self.assertIn("timeout-minutes: 45", workflow)

    def test_visible_artifact_scaffold_exists(self) -> None:
        readme = ROOT / "evals/artifacts/README.md"
        self.assertTrue(readme.is_file())
        self.assertIn("must not be committed", readme.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
