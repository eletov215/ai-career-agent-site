"""Synthetic-only checks for the AI004-M02 cost-control queue."""
import copy

import pytest

from services.matching_input import project_resume_version, project_saved_vacancy
from services.matching_prefilter import (
    MAX_INPUT_ITEMS, MAX_SCANNED, MAX_SHORTLIST, POLICY_VERSION,
    PrefilterError, VacancyCandidate, prefilter_vacancies,
)


def resume(*, role="Python developer", skills="Python, PostgreSQL", experience=""):
    return project_resume_version({"snapshot": {
        "schemaVersion": 1,
        "answers": {"role": role, "skills": skills, "experience": experience,
                    "name": "private person", "contacts": "private@example.test"},
    }})


def vacancy(key, title, requirements="", description="", **extra):
    snapshot = {
        "snapshot_version": "saved-vacancy-v1",
        "title": title, "company": "Example", "description": description,
        "requirements": requirements, **extra,
        "note": "private owner note", "url": "https://private.invalid",
    }
    return VacancyCandidate(
        stable_key=key, projection=project_saved_vacancy({"snapshot": snapshot})
    )


def test_role_title_and_skill_evidence_prioritised_without_ai():
    items = [
        vacancy("sales", "Sales manager", "Python, PostgreSQL"),
        vacancy("python", "Python developer", "Not specified"),
        vacancy("other", "Electrical engineer", "CAD"),
    ]
    result = prefilter_vacancies(resume(), items, shortlist_limit=2)
    assert result.shortlisted == ("python", "sales")
    assert result.deferred == ("other",)
    assert result.unscanned == ()
    assert result.total_items == 3 and result.scanned_items == 3
    assert result.policy_version == POLICY_VERSION
    assert result.scope_limited


def test_zero_overlap_does_not_exclude_candidates_or_claim_mismatch():
    items = [vacancy("a", "Бухгалтер", "1С"),
             vacancy("b", "Дизайнер", "Blender"),
             vacancy("c", "Сотрудник склада")]
    result = prefilter_vacancies(resume(), items, shortlist_limit=2)
    assert result.shortlisted == ("a", "b")
    assert result.deferred == ("c",)
    assert not hasattr(result, "score_percent")
    assert not hasattr(result, "matching_verdict")
    assert result.scope_limited


def test_requirements_missing_uses_description_as_cheap_signal():
    items = [vacancy("b", "Test role", "", "We value Python"),
             vacancy("a", "Test role", "", "Other stack")]
    result = prefilter_vacancies(resume(role="Other role"), items, shortlist_limit=1)
    assert result.shortlisted == ("b",)
    assert result.deferred == ("a",)


def test_input_order_breaks_all_signal_ties_reproducibly():
    items = [vacancy("first", "Unrelated A"),
             vacancy("second", "Unrelated B"),
             vacancy("third", "Unrelated C")]
    one = prefilter_vacancies(resume(role="Scientist", skills="Kotlin"), items, shortlist_limit=2)
    two = prefilter_vacancies(resume(role="Scientist", skills="Kotlin"), copy.deepcopy(items), shortlist_limit=2)
    assert one == two
    assert one.shortlisted == ("first", "second")


def test_all_items_preserved_in_explicit_bounded_groups():
    items = [vacancy(f"key-{index:03d}", "Neutral role")
             for index in range(MAX_SCANNED + 5)]
    result = prefilter_vacancies(resume(role="Scientist", skills="Kotlin"), items)
    assert len(result.shortlisted) == MAX_SHORTLIST
    assert len(result.deferred) == MAX_SCANNED - MAX_SHORTLIST
    assert len(result.unscanned) == 5
    assert len(set(result.shortlisted + result.deferred + result.unscanned)) == len(items)
    assert set(result.shortlisted + result.deferred + result.unscanned) == {
        item.stable_key for item in items
    }


def test_empty_and_fewer_than_limit_have_no_missing_items():
    assert prefilter_vacancies(resume(), []).shortlisted == ()
    assert not prefilter_vacancies(resume(), []).scope_limited
    only = prefilter_vacancies(resume(), [vacancy("only", "Python dev")])
    assert only.shortlisted == ("only",)
    assert only.deferred == ()
    assert only.unscanned == ()
    assert not only.scope_limited


def test_vacancy_fields_dont_become_pii_or_a_relevance_percentage():
    result = prefilter_vacancies(resume(), [
        vacancy("public-key", "Python", "private document code")
    ])
    text = repr(result)
    for forbidden in ("private@example.test", "private owner note",
                      "private document code", "private person", "Python"):
        assert forbidden not in text


def test_currency_or_salary_do_not_silently_reject_a_candidate():
    items = [
        vacancy("a", "Python developer", "Python", salary_from=100, currency="GBP"),
        vacancy("b", "Other role", "", salary_from=None, currency="RUB"),
    ]
    result = prefilter_vacancies(resume(), items, shortlist_limit=1)
    assert result.shortlisted == ("a",)
    assert result.deferred == ("b",)


@pytest.mark.parametrize("limits", [
    {"shortlist_limit": 0},
    {"shortlist_limit": 21},
    {"shortlist_limit": True},
    {"scan_limit": 0},
    {"scan_limit": 201},
    {"scan_limit": True},
    {"scan_limit": 1, "shortlist_limit": 2},
])
def test_limits_fail_closed(limits):
    with pytest.raises(PrefilterError):
        prefilter_vacancies(resume(), [], **limits)


def test_maximum_source_size_is_enforced():
    item = vacancy("fixed", "Python")
    with pytest.raises(PrefilterError, match="invalid_limits"):
        prefilter_vacancies(resume(), [
            VacancyCandidate(stable_key=f"job-{index}", projection=item.projection)
            for index in range(MAX_INPUT_ITEMS + 1)
        ])


@pytest.mark.parametrize("keys", [
    ("same", "same"), ("a", "bad\nkey"), ("a", " "), ("a", "x" * 257),
])
def test_invalid_or_duplicate_stable_keys_fail_closed(keys):
    with pytest.raises(PrefilterError, match="invalid_candidate"):
        prefilter_vacancies(resume(), [
            vacancy(keys[0], "Test"), vacancy(keys[1], "Test")
        ])


@pytest.mark.parametrize("mutate", [
    lambda item: item.pop("content_hash"),
    lambda item: item.update(content_hash="0" * 64),
    lambda item: item["fields"].update(title="changed"),
    lambda item: item["fields"].update(contacts="private@example.test"),
    lambda item: item.update(kind="resume_version"),
])
def test_changed_or_invalid_vacancy_projection_fails_closed(mutate):
    item = vacancy("key", "Python")
    payload = copy.deepcopy(item.projection)
    mutate(payload)
    with pytest.raises(PrefilterError, match="invalid_projection"):
        prefilter_vacancies(resume(), [VacancyCandidate("key", payload)])


def test_corrupt_resume_and_untyped_candidates_fail_closed():
    source = resume()
    source["facts"][0]["text"] = "wrong"
    with pytest.raises(PrefilterError, match="invalid_projection"):
        prefilter_vacancies(source, [])
    with pytest.raises(PrefilterError, match="invalid_candidate"):
        prefilter_vacancies(resume(), [{"stable_key": "a"}])


def test_scan_window_does_not_evaluate_or_validate_unscanned_text():
    items = [vacancy("visible", "Python")]
    broken = copy.deepcopy(vacancy("unscanned", "Python").projection)
    broken["fields"]["title"] = "tampered"
    items.append(VacancyCandidate("unscanned", broken))
    result = prefilter_vacancies(resume(), items, scan_limit=1, shortlist_limit=1)
    assert result.shortlisted == ("visible",)
    assert result.unscanned == ("unscanned",)
    with pytest.raises(PrefilterError, match="invalid_projection"):
        prefilter_vacancies(resume(), items, scan_limit=2, shortlist_limit=1)
