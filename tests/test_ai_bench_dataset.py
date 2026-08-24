from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evals.ai_bench.dataset import load_dataset
from evals.ai_bench.errors import DatasetError

ROOT = Path(__file__).resolve().parents[1]


class DatasetTests(unittest.TestCase):
    def test_golden_dataset_is_bilingual_and_complete(self) -> None:
        manifest, cases, fingerprint = load_dataset(ROOT / "evals/fixtures/manifest.json")
        self.assertTrue(manifest["synthetic"])
        self.assertEqual({case.language for case in cases}, {"ru", "en"})
        self.assertEqual(
            {case.task for case in cases},
            {"resume_analysis", "vacancy_match", "cover_letter", "interview_questions"},
        )
        self.assertGreaterEqual(len(cases), 8)
        self.assertEqual(len(fingerprint), 64)

    def test_dataset_rejects_contact_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "schema.json").write_text(json.dumps({"type": "object"}), encoding="utf-8")
            case = {
                "case_id": "bad",
                "task": "resume_analysis",
                "language": "ru",
                "synthetic": True,
                "schema": "schema.json",
                "messages": [{"role": "user", "content": "mail person@example.com"}],
                "source_facts": [],
            }
            (root / "case.json").write_text(json.dumps(case), encoding="utf-8")
            (root / "manifest.json").write_text(
                json.dumps({"dataset_id": "bad", "version": "1", "synthetic": True, "cases": ["case.json"]}),
                encoding="utf-8",
            )
            with self.assertRaises(DatasetError):
                load_dataset(root / "manifest.json")


if __name__ == "__main__":
    unittest.main()
