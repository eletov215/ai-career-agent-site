from __future__ import annotations

import json
import unittest
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

from evals.ai_bench.dataset import load_dataset
from evals.ai_bench.models import SourceFact
from evals.ai_bench.schema import validate_instance
from evals.ai_bench.scoring import (
    normalize_cover_letter_motivation_kind,
    normalize_structured_scenario_provenance,
    normalize_user_facing_evidence_markers,
    score_case,
)

ROOT = Path(__file__).resolve().parents[1]

STRICT_THRESHOLDS = {
    "min_required_path_coverage": 1.0,
    "min_grounding_score": 1.0,
    "min_quality_score": 1.0,
    "max_forbidden_claims": 0,
    "max_invalid_evidence_ids": 0,
    "max_unsupported_numbers": 0,
    "max_user_facing_technical_tokens": 0,
    "max_claim_evidence_violations": 0,
    "max_unsupported_impact_claims": 0,
    "max_cover_letter_presentation_violations": 0,
    "min_required_unverified_coverage": 1.0,
    "min_required_caveat_coverage": 1.0,
    "max_language_consistency_violations": 0,
    "max_scenario_provenance_violations": 0,
    "max_match_consistency_violations": 0,
}


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _, cls.cases, _ = load_dataset(ROOT / "evals/fixtures/manifest.json")
        cls.by_id = {case.case_id: case for case in cls.cases}
        cls.regressions = json.loads((ROOT / "evals/regressions/live-run-1.json").read_text(encoding="utf-8"))
        cls.regressions_v2 = json.loads((ROOT / "evals/regressions/live-run-2.json").read_text(encoding="utf-8"))
        cls.regressions_v3 = json.loads((ROOT / "evals/regressions/live-run-3.json").read_text(encoding="utf-8"))
        cls.regressions_v4 = json.loads((ROOT / "evals/regressions/live-run-4.json").read_text(encoding="utf-8"))
        cls.regressions_alice_final_1 = json.loads((ROOT / "evals/regressions/alice-final-run-1.json").read_text(encoding="utf-8"))
        cls.regressions_alice_final_2 = json.loads((ROOT / "evals/regressions/alice-final-run-2.json").read_text(encoding="utf-8"))
        cls.regressions_alice_final_3 = json.loads((ROOT / "evals/regressions/alice-final-run-3.json").read_text(encoding="utf-8"))
        cls.regressions_alice_final_4 = json.loads((ROOT / "evals/regressions/alice-final-run-4.json").read_text(encoding="utf-8"))
        cls.regressions_alice_final_5 = json.loads((ROOT / "evals/regressions/alice-final-run-5-human-review.json").read_text(encoding="utf-8"))

    def _reference(self, case_id: str) -> dict:
        return json.loads((ROOT / "evals/expected/reference" / f"{case_id}.json").read_text(encoding="utf-8"))

    def test_reference_outputs_pass_strict_gate(self) -> None:
        for case in self.cases:
            with self.subTest(case=case.case_id):
                score = score_case(case, self._reference(case.case_id), STRICT_THRESHOLDS)
                self.assertTrue(score["passed"], score)
                self.assertEqual(score["quality_score"], 1.0)

    def test_sourced_hypothetical_numbers_are_allowed(self) -> None:
        case = self.by_id["interview-en-01"]
        content = self._reference(case.case_id)
        score = score_case(case, content, {"max_unsupported_numbers": 0})
        self.assertEqual(score["unsupported_numbers"], [])
        self.assertNotIn("unsupported_numbers", score["gate_failures"])
        joined = json.dumps(content, ensure_ascii=False)
        for token in self.regressions["patterns"]["allowed_hypothetical_numbers"]:
            numeric = token.split()[0]
            self.assertIn(numeric, joined)

    def test_unsourced_number_is_reported_at_scalar_leaf_path(self) -> None:
        case = self.by_id["vacancy-match-en-01"]
        content = self._reference(case.case_id)
        content["recommendation"] += " Complete 99 exercises first."
        score = score_case(case, content, {"max_unsupported_numbers": 0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["unsupported_numbers"], [{"path": "$.recommendation", "value": "99"}])
        self.assertIn("unsupported_numbers", score["gate_failures"])

    def test_forbidden_claim_is_a_hard_failure(self) -> None:
        case = self.by_id["resume-analysis-ru-01"]
        content = self._reference(case.case_id)
        content["summary"] += " Кандидат руководил командой."
        score = score_case(case, content, {"max_forbidden_claims": 0})
        self.assertFalse(score["passed"])
        self.assertIn("fake_leadership", score["forbidden_claims"])

    def test_invalid_evidence_is_detected(self) -> None:
        case = self.by_id["cover-letter-en-01"]
        content = self._reference(case.case_id)
        content["paragraphs"][1]["evidence_ids"].append("invented-source")
        score = score_case(case, content, {"max_invalid_evidence_ids": 0})
        self.assertFalse(score["passed"])
        self.assertIn("invented-source", score["invalid_evidence_ids"])

    def test_schema_requires_raw_evidence_id_format(self) -> None:
        schema = json.loads((ROOT / "evals/schemas/interview_questions.schema.json").read_text(encoding="utf-8"))
        content = self._reference("interview-ru-01")
        content["questions"][0]["evidence_ids"] = ["[c1]"]
        errors = validate_instance(content, schema)
        self.assertTrue(any("pattern" in error for error in errors), errors)

    def test_live_run_serialized_technical_metadata_is_blocked_from_user_facing_text(self) -> None:
        samples = [
            sample
            for sample in self.regressions["patterns"]["user_facing_technical_metadata"]
            if "evidence" in sample["text"].casefold()
        ]
        self.assertTrue(samples)
        for sample in samples:
            case = self.by_id[sample["case_id"]]
            with self.subTest(case=case.case_id, sample=sample["text"]):
                content = self._reference(case.case_id)
                content["paragraphs"][1]["text"] = sample["text"]
                score = score_case(case, content, {"max_user_facing_technical_tokens": 0})
                self.assertFalse(score["passed"])
                self.assertTrue(score["user_facing_technical_tokens"], score)
                self.assertIn("user_facing_technical_tokens", score["gate_failures"])

    def test_live_run_unsupported_impact_is_blocked_even_without_number(self) -> None:
        case = self.by_id["cover-letter-ru-01"]
        content = self._reference(case.case_id)
        content["paragraphs"][2]["text"] = self.regressions["patterns"]["unsupported_impact"]
        content["paragraphs"][2]["evidence_ids"] = ["c4"]
        score = score_case(case, content, {"max_unsupported_impact_claims": 0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["unsupported_impact_claim_count"], 1)
        self.assertIn("unsupported_impact_claims", score["gate_failures"])

    def test_candidate_fit_paragraph_cannot_be_supported_only_by_vacancy_requirement(self) -> None:
        case = self.by_id["cover-letter-ru-01"]
        content = self._reference(case.case_id)
        content["paragraphs"][1]["evidence_ids"] = ["v2"]
        score = score_case(case, content, {"max_claim_evidence_violations": 0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["claim_evidence_violation_count"], 1)
        self.assertIn("claim_evidence", score["gate_failures"])

    def test_resume_unverified_fact_requires_structured_evidence(self) -> None:
        case = self.by_id["resume-analysis-en-01"]
        content = self._reference(case.case_id)
        content["facts_not_verified"] = [{"fact": "Production Python is not verified.", "evidence_ids": ["e1"]}]
        score = score_case(case, content, {"min_required_unverified_coverage": 1.0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["missing_unverified_evidence_ids"], ["e5"])
        self.assertIn("unverified_coverage", score["gate_failures"])

    def test_cover_letter_caveat_must_cover_unverified_requirement(self) -> None:
        case = self.by_id["cover-letter-en-01"]
        content = self._reference(case.case_id)
        content["caveats"][0]["evidence_ids"] = ["v3"]
        score = score_case(case, content, {"min_required_caveat_coverage": 1.0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["missing_caveat_evidence_ids"], ["c5"])
        self.assertIn("caveat_coverage", score["gate_failures"])

    def test_vacancy_match_score_is_derived_deterministically(self) -> None:
        ru_case = self.by_id["vacancy-match-ru-01"]
        en_case = self.by_id["vacancy-match-en-01"]
        ru_score = score_case(ru_case, self._reference(ru_case.case_id), STRICT_THRESHOLDS)
        en_score = score_case(en_case, self._reference(en_case.case_id), STRICT_THRESHOLDS)
        self.assertEqual(ru_score["match_evaluation"]["deterministic_match_score"], 67)
        self.assertEqual(en_score["match_evaluation"]["deterministic_match_score"], 71)
        self.assertEqual(ru_score["match_evaluation"]["deterministic_verdict"], "partial")
        self.assertEqual(en_score["match_evaluation"]["deterministic_verdict"], "partial")
        self.assertNotIn("match_score", self._reference(ru_case.case_id))

    def test_live_run_wrong_requirement_status_is_detected(self) -> None:
        case = self.by_id["vacancy-match-en-01"]
        content = self._reference(case.case_id)
        moved = next(item for item in content["matched_requirements"] if item["requirement_id"] == "v4")
        content["matched_requirements"] = [item for item in content["matched_requirements"] if item["requirement_id"] != "v4"]
        content["gaps"].append(moved)
        score = score_case(case, content, {"max_match_consistency_violations": 0})
        self.assertFalse(score["passed"])
        reasons = [item["reason"] for item in score["match_evaluation"]["violations"]]
        self.assertIn("expected_matched_got_gap", reasons)
        self.assertIn("match_consistency", score["gate_failures"])

    def test_live_run_duplicate_requirement_is_detected(self) -> None:
        case = self.by_id["vacancy-match-en-01"]
        content = self._reference(case.case_id)
        content["matched_requirements"].append(deepcopy(content["matched_requirements"][0]))
        score = score_case(case, content, {"max_match_consistency_violations": 0})
        self.assertFalse(score["passed"])
        reasons = [item["reason"] for item in score["match_evaluation"]["violations"]]
        self.assertIn("duplicate_classification", reasons)

    def test_match_requirement_must_cite_vacancy_and_candidate_evidence(self) -> None:
        case = self.by_id["vacancy-match-ru-01"]
        content = self._reference(case.case_id)
        content["matched_requirements"][0]["evidence_ids"] = ["c1"]
        score = score_case(case, content, {"max_match_consistency_violations": 0})
        self.assertFalse(score["passed"])
        reasons = [item["reason"] for item in score["match_evaluation"]["violations"]]
        self.assertTrue(any("vacancy_requirement_evidence" in reason for reason in reasons), reasons)


    def test_unicode_percent_spacing_is_normalized(self) -> None:
        ru_case = self.by_id["interview-ru-01"]
        ru_content = self._reference(ru_case.case_id)
        target = next(item for item in ru_content["questions"] if "20%" in item["question"])
        target["question"] = target["question"].replace("20%", "20\u202f%")
        score = score_case(ru_case, ru_content, STRICT_THRESHOLDS)
        self.assertTrue(score["passed"], score)
        self.assertEqual(score["unsupported_numbers"], [])

        en_case = self.by_id["interview-en-01"]
        en_content = self._reference(en_case.case_id)
        target = next(item for item in en_content["questions"] if "15%" in item["question"])
        target["question"] = target["question"].replace("15%", "15 %")
        score = score_case(en_case, en_content, STRICT_THRESHOLDS)
        self.assertTrue(score["passed"], score)
        self.assertEqual(score["unsupported_numbers"], [])

    def test_interview_scenario_number_requires_same_question_provenance(self) -> None:
        case = self.by_id["interview-en-01"]
        content = self._reference(case.case_id)
        target = next(item for item in content["questions"] if "15%" in item["question"])
        target["evidence_ids"] = [item for item in target["evidence_ids"] if item != "s1"]
        score = score_case(case, content, {"max_scenario_provenance_violations": 0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["scenario_provenance_violation_count"], 1)
        self.assertEqual(score["scenario_provenance_violations"][0]["number"], "15%")
        self.assertIn("scenario_provenance", score["gate_failures"])

    def test_unsourced_interview_30_days_remains_a_hard_failure(self) -> None:
        case = self.by_id["interview-en-01"]
        content = self._reference(case.case_id)
        content["questions"][0]["question"] += " What would you do after 30 days?"
        score = score_case(case, content, {"max_unsupported_numbers": 0})
        self.assertFalse(score["passed"])
        self.assertTrue(any(item["value"] == "30" for item in score["unsupported_numbers"]), score)

    def test_ru_case_written_in_english_fails_language_gate(self) -> None:
        case = self.by_id["cover-letter-ru-01"]
        content = self._reference(case.case_id)
        content["subject"] = "Application for Customer Success Specialist"
        for paragraph in content["paragraphs"]:
            paragraph["text"] = "I am applying for this role because my confirmed support experience is relevant to the position and I would welcome a conversation about the team."
        content["caveats"][0]["text"] = "English proficiency is required for the role but is not verified for the candidate."
        score = score_case(case, content, {"max_language_consistency_violations": 0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["language_consistency_violation_count"], 1)
        self.assertIn("language_consistency", score["gate_failures"])

    def test_en_case_written_in_russian_fails_language_gate(self) -> None:
        case = self.by_id["cover-letter-en-01"]
        content = self._reference(case.case_id)
        for paragraph in content["paragraphs"]:
            paragraph["text"] = "Меня заинтересовала эта вакансия, и я хотел бы обсудить подтвержденный опыт кандидата и требования позиции без добавления новых фактов."
        score = score_case(case, content, {"max_language_consistency_violations": 0})
        self.assertFalse(score["passed"])
        self.assertEqual(score["language_consistency_violation_count"], 1)

    def test_vacancy_grounded_motivation_paragraph_is_valid(self) -> None:
        case = self.by_id["cover-letter-en-01"]
        content = self._reference(case.case_id)
        motivation = next(item for item in content["paragraphs"] if item["kind"] == "motivation")
        self.assertEqual(motivation["evidence_ids"], ["v1", "v2"])
        score = score_case(case, content, STRICT_THRESHOLDS)
        self.assertTrue(score["passed"], score)

    def test_motivation_paragraph_requires_vacancy_evidence(self) -> None:
        case = self.by_id["cover-letter-en-01"]
        content = self._reference(case.case_id)
        motivation = next(item for item in content["paragraphs"] if item["kind"] == "motivation")
        motivation["evidence_ids"] = ["c1"]
        score = score_case(case, content, {"max_claim_evidence_violations": 0})
        self.assertFalse(score["passed"])
        reasons = [item["reason"] for item in score["claim_evidence_violations"]]
        self.assertIn("motivation_without_vacancy_evidence", reasons)

    def test_live_run_3_impact_phrases_are_hard_failures(self) -> None:
        case = self.by_id["cover-letter-ru-01"]
        for sample in self.regressions_v3["patterns"]["unsupported_impact_claims"]:
            with self.subTest(text=sample["text"]):
                content = self._reference(case.case_id)
                content["paragraphs"][1]["kind"] = "candidate_fit"
                content["paragraphs"][1]["text"] = sample["text"]
                content["paragraphs"][1]["evidence_ids"] = sample["evidence_ids"]
                score = score_case(case, content, {"max_unsupported_impact_claims": 0})
                self.assertFalse(score["passed"], score)
                self.assertEqual(score["unsupported_impact_claim_count"], 1)
                self.assertIn("unsupported_impact_claims", score["gate_failures"])

    def test_simple_evidence_markers_are_removed_before_user_display(self) -> None:
        case = self.by_id["interview-ru-01"]
        for sample in self.regressions_v3["patterns"]["simple_marker_cleanup"]:
            content = self._reference(case.case_id)
            content["questions"][0]["question"] = sample["input"]
            normalized, audit = normalize_user_facing_evidence_markers(case, content)
            self.assertEqual(normalized["questions"][0]["question"], sample["expected"])
            self.assertEqual(audit["user_facing_marker_cleanup_count"], 1)

    def test_grouped_known_evidence_markers_are_removed_before_user_display(self) -> None:
        for sample in self.regressions_alice_final_4["patterns"]["grouped_known_marker_cleanup"]:
            case = self.by_id[sample["case_id"]]
            with self.subTest(text=sample["input"]):
                content = self._reference(case.case_id)
                content["questions"][0]["purpose"] = sample["input"]
                normalized, audit = normalize_user_facing_evidence_markers(case, content)
                self.assertEqual(normalized["questions"][0]["purpose"], sample["expected"] )
                expected_removed = 4 if "v1, v2" in sample["input"] else 3
                self.assertEqual(audit["user_facing_marker_cleanup_count"], expected_removed)

    def test_grouped_marker_with_unknown_id_is_not_silently_cleaned(self) -> None:
        sample = self.regressions_alice_final_4["patterns"]["unknown_group_must_not_be_cleaned"]
        case = self.by_id[sample["case_id"]]
        content = self._reference(case.case_id)
        content["questions"][0]["purpose"] = sample["input"]
        normalized, audit = normalize_user_facing_evidence_markers(case, content)
        self.assertEqual(normalized["questions"][0]["purpose"], sample["input"] )
        self.assertEqual(audit["user_facing_marker_cleanup_count"], 0)
        score = score_case(case, normalized, {"max_user_facing_technical_tokens": 0})
        self.assertFalse(score["passed"], score)
        self.assertTrue(any(item["token"] == sample["unknown_id"] for item in score["user_facing_technical_tokens"]), score)
        self.assertIn("user_facing_technical_tokens", score["gate_failures"])

    def test_marker_cleanup_does_not_substitute_structured_scenario_provenance(self) -> None:
        case = self.by_id["interview-ru-01"]
        content = self._reference(case.case_id)
        content["questions"][0]["question"] = "Если 20 % ответов API ошибочны (s1), что вы проверите?"
        content["questions"][0]["evidence_ids"] = ["c3"]
        score = score_case(case, content, {"max_scenario_provenance_violations": 0, "max_user_facing_technical_tokens": 0})
        normalized, audit = normalize_user_facing_evidence_markers(case, content)
        self.assertEqual(audit["user_facing_marker_cleanup_count"], 1)
        self.assertNotIn("(s1)", normalized["questions"][0]["question"])
        self.assertFalse(score["passed"], score)
        self.assertIn("scenario_provenance", score["gate_failures"])

    def test_known_decorated_marker_is_repairable_not_hard_metadata(self) -> None:
        case = self.by_id["interview-ru-01"]
        content = self._reference(case.case_id)
        content["questions"][0]["question"] += " (c1)"
        score = score_case(case, content, {"max_user_facing_technical_tokens": 0})
        self.assertNotIn("user_facing_technical_tokens", score["gate_failures"])
        normalized, audit = normalize_user_facing_evidence_markers(case, content)
        self.assertEqual(audit["user_facing_marker_cleanup_count"], 1)
        self.assertNotIn("(c1)", normalized["questions"][0]["question"])

    def test_serious_metadata_label_is_not_silently_cleaned(self) -> None:
        case = self.by_id["interview-ru-01"]
        content = self._reference(case.case_id)
        content["questions"][0]["question"] += " evidence_ids: c1"
        normalized, audit = normalize_user_facing_evidence_markers(case, content)
        self.assertEqual(audit["user_facing_marker_cleanup_count"], 0)
        score = score_case(case, normalized, {"max_user_facing_technical_tokens": 0})
        self.assertFalse(score["passed"], score)
        self.assertIn("user_facing_technical_tokens", score["gate_failures"])

    def test_live_run_4_alice_impact_phrases_are_hard_failures(self) -> None:
        for sample in self.regressions_v4["patterns"]["alice_unsupported_impact_claims"]:
            case = self.by_id[sample["case_id"]]
            with self.subTest(case=case.case_id, text=sample["text"]):
                content = self._reference(case.case_id)
                content["paragraphs"][1]["kind"] = "candidate_fit"
                content["paragraphs"][1]["text"] = sample["text"]
                content["paragraphs"][1]["evidence_ids"] = sample["evidence_ids"]
                score = score_case(case, content, {"max_unsupported_impact_claims": 0})
                self.assertFalse(score["passed"], score)
                self.assertGreaterEqual(score["unsupported_impact_claim_count"], 1)
                self.assertIn("unsupported_impact_claims", score["gate_failures"])

    def test_causal_language_is_tracked_even_with_another_impact_family(self) -> None:
        case = self.by_id["cover-letter-ru-01"]
        content = self._reference(case.case_id)
        content["paragraphs"][1]["text"] = "Работа по SLA позволила мне улучшить качество обслуживания."
        content["paragraphs"][1]["evidence_ids"] = ["c2"]
        score = score_case(case, content, {"max_unsupported_impact_claims": 0})
        self.assertFalse(score["passed"], score)
        families = set(score["unsupported_impact_claims"][0]["unsupported_families"])
        self.assertIn("causal_effect", families)
        self.assertIn("quality_reliability", families)

    def test_live_run_4_safe_literal_rewrites_remain_allowed(self) -> None:
        for sample in self.regressions_v4["patterns"]["safe_literal_rewrites"]:
            case = self.by_id[sample["case_id"]]
            content = self._reference(case.case_id)
            content["paragraphs"][1]["kind"] = "candidate_fit"
            content["paragraphs"][1]["text"] = sample["text"]
            content["paragraphs"][1]["evidence_ids"] = sample["evidence_ids"]
            score = score_case(case, content, {"max_unsupported_impact_claims": 0})
            self.assertNotIn("unsupported_impact_claims", score["gate_failures"], score)

    def test_live_run_4_missing_scenario_provenance_remains_hard_failure(self) -> None:
        sample = self.regressions_v4["patterns"]["alice_missing_scenario_provenance"]
        case = self.by_id[sample["case_id"]]
        content = self._reference(case.case_id)
        target = content["questions"][1]
        target["question"] = sample["question"]
        target["purpose"] = sample["purpose"]
        target["follow_up_if_weak"] = sample["follow_up_if_weak"]
        target["evidence_ids"] = sample["evidence_ids"]
        score = score_case(case, content, {"max_scenario_provenance_violations": 0})
        self.assertFalse(score["passed"], score)
        self.assertEqual(score["scenario_provenance_violation_count"], 1)
        self.assertEqual(score["scenario_provenance_violations"][0]["required_evidence"], sample["required_evidence_id"])


    def test_alice_final_unique_scenario_provenance_is_repaired_before_machine_scoring(self) -> None:
        patterns = self.regressions_alice_final_1["patterns"]["repairable_scenario_provenance"]
        for sample in patterns:
            case = self.by_id[sample["case_id"]]
            content = self._reference(case.case_id)
            target = next(
                question
                for question in content["questions"]
                if sample["required_evidence_id"] in question["evidence_ids"]
            )
            target["evidence_ids"] = list(sample["evidence_ids_before"])
            if sample["number"] == "20%":
                target["follow_up_if_weak"] = "Если 20 % ответов API ошибочны, что вы проверите дальше?"
            elif sample["number"] == "15%":
                target["follow_up_if_weak"] = "Suppose actuals are 15 % below forecast. What would you check first?"
            else:
                target["follow_up_if_weak"] = "What would you prioritize during the first 90 days?"
            raw_score = score_case(case, content, {"max_scenario_provenance_violations": 0})
            self.assertIn("scenario_provenance", raw_score["gate_failures"], raw_score)
            normalized, audit = normalize_structured_scenario_provenance(case, content)
            self.assertGreaterEqual(audit["scenario_provenance_repair_count"], 1)
            repaired_question = next(
                question for question in normalized["questions"]
                if sample["required_evidence_id"] in question["evidence_ids"]
                and sample["number"].replace("%", "") in json.dumps(question, ensure_ascii=False)
            )
            self.assertIn(sample["required_evidence_id"], repaired_question["evidence_ids"])
            repaired_score = score_case(case, normalized, {"max_scenario_provenance_violations": 0})
            self.assertNotIn("scenario_provenance", repaired_score["gate_failures"], repaired_score)

    def test_ambiguous_scenario_number_is_never_auto_repaired(self) -> None:
        case = self.by_id["interview-en-01"]
        ambiguous_case = replace(
            case,
            source_facts=case.source_facts + (SourceFact("s9", "another hypothetical horizon 90 days", "scenario"),),
        )
        content = self._reference(case.case_id)
        target = content["questions"][0]
        target["follow_up_if_weak"] = "What would you prioritize during the first 90 days?"
        target["evidence_ids"] = ["c1", "c2", "v2"]
        normalized, audit = normalize_structured_scenario_provenance(ambiguous_case, content)
        self.assertEqual(audit["scenario_provenance_repair_count"], 0)
        self.assertNotIn("s2", normalized["questions"][0]["evidence_ids"])
        self.assertNotIn("s9", normalized["questions"][0]["evidence_ids"])
        score = score_case(ambiguous_case, normalized, {"max_scenario_provenance_violations": 0})
        self.assertIn("scenario_provenance", score["gate_failures"], score)

    def test_interview_response_cardinality_is_not_a_factual_number_claim(self) -> None:
        sample = self.regressions_alice_final_1["patterns"]["safe_response_cardinality"]
        case = self.by_id[sample["case_id"]]
        content = self._reference(case.case_id)
        content["questions"][0]["follow_up_if_weak"] = sample["text"]
        score = score_case(case, content, {"max_unsupported_numbers": 0})
        self.assertEqual(score["unsupported_numbers"], [], score)
        self.assertNotIn("unsupported_numbers", score["gate_failures"], score)

    def test_unsourced_interview_duration_remains_a_hard_failure(self) -> None:
        sample = self.regressions_alice_final_1["patterns"]["unsafe_unsourced_duration"]
        case = self.by_id[sample["case_id"]]
        content = self._reference(case.case_id)
        content["questions"][0]["follow_up_if_weak"] = sample["text"]
        score = score_case(case, content, {"max_unsupported_numbers": 0})
        self.assertTrue(any(item["value"] == sample["number"] for item in score["unsupported_numbers"]), score)
        self.assertIn("unsupported_numbers", score["gate_failures"], score)

    def test_schema_rejects_additional_property(self) -> None:
        schema = json.loads((ROOT / "evals/schemas/cover_letter.schema.json").read_text(encoding="utf-8"))
        content = self._reference("cover-letter-en-01")
        content["invented"] = True
        errors = validate_instance(content, schema)
        self.assertTrue(any("additional property" in error for error in errors))


    def test_alice_final_run_2_vacancy_only_future_intent_repairs_to_motivation(self) -> None:
        sample = self.regressions_alice_final_2["patterns"]["vacancy_only_future_intent"]
        case = self.by_id[sample["case_id"]]
        content = self._reference(case.case_id)
        content["paragraphs"][2]["kind"] = sample["kind_before"]
        content["paragraphs"][2]["text"] = sample["text"]
        content["paragraphs"][2]["evidence_ids"] = sample["evidence_ids"]
        raw_score = score_case(case, content, {"max_claim_evidence_violations": 0})
        self.assertIn("claim_evidence", raw_score["gate_failures"], raw_score)
        normalized, audit = normalize_cover_letter_motivation_kind(case, content)
        self.assertEqual(audit["cover_letter_kind_repair_count"], 1)
        self.assertEqual(normalized["paragraphs"][2]["kind"], sample["expected_kind_after"])
        repaired_score = score_case(case, normalized, {"max_claim_evidence_violations": 0})
        self.assertNotIn("claim_evidence", repaired_score["gate_failures"], repaired_score)

    def test_alice_final_run_2_existing_skill_claim_is_not_reclassified(self) -> None:
        sample = self.regressions_alice_final_2["patterns"]["vacancy_only_existing_skill_must_not_repair"]
        case = self.by_id[sample["case_id"]]
        content = self._reference(case.case_id)
        content["paragraphs"][2]["kind"] = sample["kind_before"]
        content["paragraphs"][2]["text"] = sample["text"]
        content["paragraphs"][2]["evidence_ids"] = sample["evidence_ids"]
        normalized, audit = normalize_cover_letter_motivation_kind(case, content)
        self.assertEqual(audit["cover_letter_kind_repair_count"], 0)
        self.assertEqual(normalized["paragraphs"][2]["kind"], "candidate_fit")
        score = score_case(case, normalized, {"max_claim_evidence_violations": 0})
        self.assertIn("claim_evidence", score["gate_failures"], score)

    def test_alice_final_run_2_unicode_nonbreaking_hyphen_matches_grounding_term(self) -> None:
        sample = self.regressions_alice_final_2["patterns"]["unicode_nonbreaking_hyphen_grounding"]
        case = self.by_id[sample["case_id"]]
        content = self._reference(case.case_id)
        content["questions"][0]["question"] = sample["text"]
        score = score_case(case, content, {"min_grounding_score": 0.0})
        self.assertNotIn(sample["required_grounding_id"], score["missing_grounding_requirements"], score)

    def test_interview_prompt_requires_role_evidence_coverage(self) -> None:
        for case_id in ("interview-ru-01", "interview-en-01"):
            case = self.by_id[case_id]
            system_prompt = case.messages[0]["content"]
            with self.subTest(case=case_id):
                self.assertIn("v1", system_prompt)
                self.assertIn("v2", system_prompt)
                self.assertIn("c1", system_prompt)
                self.assertIn("c4", system_prompt)
    def test_grounded_v26_unverified_gap_future_intent_is_not_repaired_into_visible_letter(self) -> None:
        sample = self.regressions_alice_final_3["patterns"]["unverified_gap_future_intent"]
        case = self.by_id[sample["case_id"]]
        content = self._reference(case.case_id)
        content["paragraphs"][3]["kind"] = sample["kind_before"]
        content["paragraphs"][3]["text"] = sample["text"]
        content["paragraphs"][3]["evidence_ids"] = sample["evidence_ids"]
        normalized, audit = normalize_cover_letter_motivation_kind(case, content)
        self.assertEqual(audit["cover_letter_kind_repair_count"], 0)
        self.assertEqual(normalized["paragraphs"][3]["kind"], sample["kind_before"])
        score = score_case(case, normalized, {
            "max_cover_letter_presentation_violations": 0,
            "max_unsupported_impact_claims": 0,
        })
        self.assertIn("cover_letter_presentation", score["gate_failures"], score)
        reasons = {item["reason"] for item in score["cover_letter_presentation_violations"]}
        self.assertIn("unverified_candidate_gap_must_remain_internal", reasons)
        self.assertIn("explicit_gap_disclosure_in_visible_letter", reasons)


    def test_cover_letter_presentation_omits_internal_caveats(self) -> None:
        for case_id in ("cover-letter-ru-01", "cover-letter-en-01"):
            case = self.by_id[case_id]
            content = self._reference(case_id)
            self.assertTrue(content.get("caveats"))
            presentation, audit = normalize_user_facing_evidence_markers(case, content)
            with self.subTest(case=case_id):
                self.assertNotIn("caveats", presentation)
                self.assertEqual(audit["presentation_internal_field_omission_count"], 1)
                self.assertEqual(audit["presentation_internal_field_omissions"], ["$.caveats"])

    def test_cover_letter_gap_disclosure_in_visible_paragraph_is_hard_failure(self) -> None:
        case = self.by_id["cover-letter-en-01"]
        content = self._reference(case.case_id)
        content["paragraphs"][3] = {
            "kind": "motivation",
            "text": "While I do not have verified experimentation experience, I am eager to develop it.",
            "evidence_ids": ["c5", "v3"],
        }
        score = score_case(case, content, {"max_cover_letter_presentation_violations": 0})
        self.assertFalse(score["passed"], score)
        self.assertIn("cover_letter_presentation", score["gate_failures"], score)
        reasons = {item["reason"] for item in score["cover_letter_presentation_violations"]}
        self.assertIn("unverified_candidate_gap_must_remain_internal", reasons)
        self.assertIn("explicit_gap_disclosure_in_visible_letter", reasons)

    def test_cover_letter_third_person_writer_reference_is_hard_failure(self) -> None:
        case = self.by_id["cover-letter-ru-01"]
        content = self._reference(case.case_id)
        content["paragraphs"][0]["text"] = "Кандидат заинтересован в вакансии Customer Success Specialist и хотел бы обсудить роль."
        score = score_case(case, content, {"max_cover_letter_presentation_violations": 0})
        self.assertFalse(score["passed"], score)
        self.assertIn("cover_letter_presentation", score["gate_failures"], score)
        self.assertTrue(any(item["reason"] == "third_person_writer_reference" for item in score["cover_letter_presentation_violations"]))

    def test_cover_letter_missing_first_person_voice_is_hard_failure(self) -> None:
        case = self.by_id["cover-letter-en-01"]
        content = self._reference(case.case_id)
        for paragraph in content["paragraphs"]:
            paragraph["text"] = "Relevant product design experience is presented for the B2B Product Designer role."
        score = score_case(case, content, {"max_cover_letter_presentation_violations": 0})
        self.assertFalse(score["passed"], score)
        self.assertTrue(any(item["reason"] == "missing_first_person_voice" for item in score["cover_letter_presentation_violations"]))

    def test_human_review_regression_provenance_is_versioned(self) -> None:
        self.assertEqual(self.regressions_alice_final_5["reviewer"], "Шекунов Д.С.")
        self.assertEqual(self.regressions_alice_final_5["decision"], "revision_required")
        self.assertEqual(
            set(self.regressions_alice_final_5["patterns"]),
            {
                "resume_ru_soft_coaching",
                "vacancy_ru_actionable_gap",
                "cover_letter_ru_internal_gap_only",
                "cover_letter_en_internal_gap_only",
            },
        )

    def test_alice_final_run_3_verified_growth_claim_is_not_reclassified(self) -> None:
        sample = self.regressions_alice_final_3["patterns"]["verified_candidate_growth_must_not_repair"]
        case = self.by_id[sample["case_id"]]
        content = self._reference(case.case_id)
        content["paragraphs"][1]["kind"] = sample["kind_before"]
        content["paragraphs"][1]["text"] = sample["text"]
        content["paragraphs"][1]["evidence_ids"] = sample["evidence_ids"]
        normalized, audit = normalize_cover_letter_motivation_kind(case, content)
        self.assertEqual(audit["cover_letter_kind_repair_count"], 0)
        self.assertEqual(normalized["paragraphs"][1]["kind"], "candidate_fit")
        score = score_case(case, normalized, {"max_unsupported_impact_claims": 0})
        self.assertIn("unsupported_impact_claims", score["gate_failures"], score)

    def test_alice_final_run_3_resource_count_is_safe_answer_cardinality(self) -> None:
        sample = self.regressions_alice_final_3["patterns"]["safe_response_cardinality_resources_approaches"]
        case = self.by_id[sample["case_id"]]
        content = self._reference(case.case_id)
        content["questions"][3]["follow_up_if_weak"] = sample["text"]
        score = score_case(case, content, {"max_unsupported_numbers": 0})
        self.assertEqual(score["unsupported_numbers"], [], score)
        self.assertNotIn("unsupported_numbers", score["gate_failures"], score)

    def test_alice_final_run_3_unsourced_duration_remains_hard_failure(self) -> None:
        sample = self.regressions_alice_final_3["patterns"]["unsafe_unsourced_duration"]
        case = self.by_id[sample["case_id"]]
        content = self._reference(case.case_id)
        content["questions"][3]["follow_up_if_weak"] = sample["text"]
        score = score_case(case, content, {"max_unsupported_numbers": 0})
        observed = {item["value"] for item in score["unsupported_numbers"]}
        self.assertTrue(set(sample["numbers"]).issubset(observed), score)
        self.assertIn("unsupported_numbers", score["gate_failures"], score)


if __name__ == "__main__":
    unittest.main()
