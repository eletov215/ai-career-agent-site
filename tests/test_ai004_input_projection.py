"""AI004-M01 projection is source-bound, deterministic and never dispatches AI."""
import copy
import json
import pytest

from services.matching_input import (
    MatchInputError, project_resume_version, project_saved_vacancy,
)


def resume():
    return {"snapshot_json": json.dumps({"schemaVersion": 1, "answers": {
        "role": "Backend engineer", "skills": "Python, PostgreSQL",
        "experience": "Built internal APIs", "contacts": "private@example.test",
        "name": "Private Name", "goal": "private preferences",
    }, "messages": [{"type": "user", "text": "private conversation"}],
    "photoAssetId": "private-photo"})}


def vacancy():
    return {"id": "synthetic-only", "note": "private owner note",
            "snapshot": {"snapshot_version": "saved-vacancy-v1",
                         "title": "Backend engineer", "company": "Example",
                         "requirements": "Python", "description": "APIs",
                         "source_records": [{"url": "https://private.invalid"}],
                         "salary_from": None, "salary_to": None}}


def test_resume_projection_excludes_sensitive_and_unrelated_fields():
    result = project_resume_version(resume())
    encoded = json.dumps(result)
    for forbidden in ("Private Name", "private@example.test", "private conversation",
                      "private-photo", "private preferences"):
        assert forbidden not in encoded
    assert result["kind"] == "resume_version"
    assert [row["id"] for row in result["facts"]] == [
        "resume.role", "resume.experience", "resume.skills",
    ]


def test_vacancy_projection_ignores_notes_and_urls():
    result = project_saved_vacancy(vacancy())
    encoded = json.dumps(result)
    assert "private owner note" not in encoded
    assert "private.invalid" not in encoded
    assert result["fields"]["requirements"] == "Python"


def test_hash_is_stable_for_irrelevant_changes_and_changes_for_facts():
    a = resume()
    b = copy.deepcopy(a)
    b["snapshot_json"] = json.dumps({"photoAssetId": "another", "answers": {
        "skills": "Python, PostgreSQL", "role": "Backend engineer",
        "experience": "Built internal APIs", "name": "Someone else"},
        "schemaVersion": 1})
    assert project_resume_version(a)["content_hash"] == project_resume_version(b)["content_hash"]
    b["snapshot_json"] = json.dumps({"schemaVersion": 1, "answers": {
        "role": "Backend engineer", "skills": "Python, Go",
        "experience": "Built internal APIs"}})
    assert project_resume_version(a)["content_hash"] != project_resume_version(b)["content_hash"]


@pytest.mark.parametrize("value", [None, {}, {"snapshot_json": "not-json"},
    {"snapshot": {"schemaVersion": 1, "answers": {"name": "only identity"}}},
    {"snapshot": {"schemaVersion": 2, "answers": {"skills": "Python"}}}])
def test_invalid_or_empty_resume_fails_closed(value):
    with pytest.raises(MatchInputError):
        project_resume_version(value)


@pytest.mark.parametrize("mutate", [
    lambda x: x["snapshot"].update(snapshot_version="invalid"),
    lambda x: x["snapshot"].update(title=""),
    lambda x: x["snapshot"].update(salary_from=float("nan")),
    lambda x: x["snapshot"].update(salary_to=float("inf")),
    lambda x: x["snapshot"].update(requirements="x"*33000),
])
def test_invalid_vacancy_fails_closed(mutate):
    value = vacancy()
    mutate(value)
    with pytest.raises(MatchInputError):
        project_saved_vacancy(value)


def test_no_match_score_or_provider_side_effects():
    result = project_saved_vacancy(vacancy())
    assert "score_percent" not in result
    assert "match" not in result
