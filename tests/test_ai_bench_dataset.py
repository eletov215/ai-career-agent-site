from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evals.ai_bench.dataset import load_dataset
from evals.ai_bench.errors import DatasetError

ROOT = Path(__file__).resolve().parents[1]


class DatasetTests(unittest.TestCase):
    def test_golden_dataset_is_bilingual_complete_and_grounded_v2(self) -> None:
        manifest, cases, fingerprint = load_dataset(ROOT / "evals/fixtures/manifest.json")
        self.assertTrue(manifest["synthetic"])
        self.assertEqual(manifest["version"], "1.3.5")
        self.assertEqual(manifest["contract"], "grounded-v2.6")
        self.assertEqual({case.language for case in cases}, {"ru", "en"})
        self.assertEqual(
            {case.task for case in cases},
            {"resume_analysis", "vacancy_match", "cover_letter", "interview_questions"},
        )
        self.assertGreaterEqual(len(cases), 8)
        self.assertEqual(len(fingerprint), 64)
        self.assertTrue(all(fact.kind in {"candidate", "vacancy", "scenario"} for case in cases for fact in case.source_facts))
        self.assertTrue(all(case.match_requirements for case in cases if case.task == "vacancy_match"))

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

    def test_dataset_rejects_source_fact_without_kind(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "schema.json").write_text(json.dumps({"type": "object"}), encoding="utf-8")
            case = {
                "case_id": "bad-kind",
                "task": "resume_analysis",
                "language": "en",
                "synthetic": True,
                "schema": "schema.json",
                "messages": [{"role": "user", "content": "synthetic"}],
                "source_facts": [{"id": "c1", "text": "synthetic fact"}],
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
