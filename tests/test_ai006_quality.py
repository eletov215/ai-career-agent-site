import copy
import json

from ai_quality.ai006 import HARD_THRESHOLDS, run_gate


def test_reference_gate_is_exact_and_provider_free(tmp_path):
    result = run_gate(tmp_path)
    assert result["status"] == "failed"
    assert result["provider_calls"] == 0
    assert result["synthetic_only"] is True
    assert len(result["positive_cases"]) == 6
    assert len(result["negative_cases"]) == 18
    failures = [row for row in result["negative_cases"] if row["status"] == "failed"]
    assert failures == [{"id": "invented-skill", "expected_reason": "validation_evidence_quote",
                         "reason": "accepted", "status": "failed"}]
    assert result["metrics"]["unsupported_candidate_claims"] == 0
    assert result["metrics"]["negative_rejection_rate"] == 17 / 18
    by_id = {row["id"]: row for row in result["positive_cases"]}
    assert by_id["ru-full-professional"]["body_length"] > by_id["ru-short-professional"]["body_length"]
    assert by_id["en-full-professional"]["body_length"] > by_id["en-short-professional"]["body_length"]
    assert all(row["schema_pass"] and row["structure_pass"] and row["grounding_pass"]
               and row["validation_reason"] is None for row in result["positive_cases"])
    assert {path.name for path in tmp_path.iterdir()} == {
        "run.json", "report.md", "manual_review_template.json"}


def test_critical_failure_cannot_be_hidden_by_other_metrics(monkeypatch, tmp_path):
    from ai_quality import ai006
    suite = json.loads(ai006.SUITE_PATH.read_text())
    suite["negative_cases"][0]["expected_reason"] = "validation_structure"
    changed = tmp_path / "suite.json"
    changed.write_text(json.dumps(suite))
    monkeypatch.setattr(ai006, "SUITE_PATH", changed)
    result = run_gate()
    assert result["metrics"]["negative_rejection_rate"] < 1.0
    assert result["status"] == "failed"


def test_positive_safety_metrics_are_derived_from_validation(monkeypatch, tmp_path):
    from ai_quality import ai006
    suite = json.loads(ai006.SUITE_PATH.read_text())
    suite["positive_cases"][3]["expected"]["paragraphs"][1]["text"] = "I maintain 99 APIs."
    changed = tmp_path / "suite.json"
    changed.write_text(json.dumps(suite))
    monkeypatch.setattr(ai006, "SUITE_PATH", changed)
    result = run_gate()
    assert result["metrics"]["unsupported_numbers"] == 1
    assert result["metrics"]["critical_validator_failures"] == 1
    assert result["status"] == "failed"


def test_public_negative_results_only_contain_fixed_reasons():
    result = run_gate()
    allowlist = set(result["validator_reason_allowlist"])
    assert all(row["reason"] in allowlist or row["reason"] == "accepted"
               for row in result["negative_cases"])
    assert all("exception" not in json.dumps(row).lower() for row in result["negative_cases"])


def test_human_review_cannot_override_machine_gate():
    result = run_gate()
    assert result["soft_writing_quality"] == {
        "status": "manual_review_required", "can_override_machine_failure": False}


def test_invented_skill_with_valid_unrelated_quote_exposes_production_gap():
    result = run_gate()
    row = next(item for item in result["negative_cases"] if item["id"] == "invented-skill")
    assert row["reason"] == "accepted"
    assert row["status"] == "failed"
    assert result["metrics"]["unsupported_candidate_claims"] == 0
    assert result["status"] == "failed"
