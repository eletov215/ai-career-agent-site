from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import inspect, select, text

from database import create_database, downgrade_database, upgrade_database
from domain import (
    EMPLOYMENT_VALUES,
    EXPERIENCE_VALUES,
    WORK_FORMAT_VALUES,
    NormalizedVacancy,
)
from models import Vacancy, VacancySourceRecord
from services.search_filters import VacancySearchFilters, filter_vacancies
from services.vacancy_normalizer import (
    canonical_currency,
    normalize_hh_vacancy,
    normalize_reed_vacancy,
    normalize_superjob_vacancy,
    normalize_trudvsem_vacancy,
    normalize_vacancy_mapping,
)
from services.vacancy_store import VacancyStore


def _sqlite_url(path) -> str:  # noqa: ANN001
    return f"sqlite:///{path.resolve().as_posix()}"


def test_contract_codes_and_mapping_are_explicit():
    vacancy = NormalizedVacancy(
        external_id="1",
        source="test",
        source_title="Test",
        title="Role",
        company="Company",
        salary_from=None,
        salary_to=None,
        currency="",
        location="",
        work_format="unknown",
        employment_code="unknown",
        experience_code="unknown",
        schedule="",
        employment="",
        experience="",
        description="",
        requirements="",
        published_at=None,
        url="",
    )
    payload = vacancy.as_mapping()
    assert payload["contract_version"] == 1
    assert payload["remote"] is False
    assert payload["work_format"] in WORK_FORMAT_VALUES
    assert payload["employment_code"] in EMPLOYMENT_VALUES
    assert payload["experience_code"] in EXPERIENCE_VALUES


def test_hh_adapter_prefers_structured_contract_fields():
    normalized = normalize_hh_vacancy(
        {
            "id": "hh-1",
            "name": "<b>Python developer</b>",
            "employer": {"name": "ACME"},
            "salary": {"from": 200000, "to": 150000, "currency": "RUR"},
            "area": {"name": "Москва"},
            "work_format": [{"id": "HYBRID", "name": "Гибрид"}],
            "schedule": {"id": "fullDay", "name": "Полный день"},
            "employment_form": {"id": "FULL", "name": "Полная занятость"},
            "experience": {"id": "between1And3", "name": "От 1 года до 3 лет"},
            "snippet": {"requirement": "<b>Python</b>", "responsibility": "APIs"},
            "published_at": "2026-08-08T12:00:00+03:00",
            "alternate_url": "https://hh.test/1",
        }
    ).as_mapping()

    assert normalized["title"] == "Python developer"
    assert normalized["salary_from"] == 150000.0
    assert normalized["salary_to"] == 200000.0
    assert normalized["currency"] == "RUB"
    assert normalized["work_format"] == "hybrid"
    assert normalized["employment_code"] == "full"
    assert normalized["experience_code"] == "between_1_and_3"
    assert normalized["published_at"] == "2026-08-08T09:00:00Z"


def test_reed_adapter_does_not_invent_format_without_evidence():
    unknown = normalize_reed_vacancy(
        {
            "jobId": 1,
            "jobTitle": "Data analyst",
            "employerName": "ACME",
            "locationName": "London",
            "jobDescription": "Analytics role",
        }
    ).as_mapping()
    hybrid = normalize_reed_vacancy(
        {
            "jobId": 2,
            "jobTitle": "Data analyst",
            "employerName": "ACME",
            "locationName": "London",
            "jobDescription": "Hybrid analytics role",
            "jobType": "Full time",
            "contractType": "Permanent",
        }
    ).as_mapping()

    assert unknown["work_format"] == "unknown"
    assert unknown["currency"] == "GBP"
    assert hybrid["work_format"] == "hybrid"
    assert hybrid["employment_code"] == "full"


def test_superjob_adapter_uses_place_and_type_fields():
    normalized = normalize_superjob_vacancy(
        {
            "id": 10,
            "profession": "Инженер",
            "firm_name": "Завод",
            "payment_from": 100000,
            "payment_to": 0,
            "currency": "rub",
            "town": {"title": "Самара"},
            "place_of_work": {"id": 2, "title": "Работа на дому"},
            "type_of_work": {"id": 6, "title": "Неполный рабочий день"},
            "experience": {"title": "Без опыта"},
            "date_published": 1786190400,
        }
    ).as_mapping()

    assert normalized["work_format"] == "remote"
    assert normalized["employment_code"] == "part"
    assert normalized["experience_code"] == "no_experience"
    assert normalized["salary_to"] is None
    assert normalized["currency"] == "RUB"


def test_trudvsem_adapter_preserves_lifecycle_and_codes():
    normalized = normalize_trudvsem_vacancy(
        {
            "vacancy": {
                "id": "tv-1",
                "job-name": "Инженер",
                "company": {"name": "Завод"},
                "region": {"name": "Самара"},
                "schedule": "Удалённая работа",
                "employment": "Полная занятость",
                "required_experience": "Без опыта",
                "status": "closed",
                "modified-date": "2026-08-08T10:00:00Z",
            }
        }
    )
    assert normalized is not None
    payload = normalized.as_mapping()
    assert payload["work_format"] == "remote"
    assert payload["employment_code"] == "full"
    assert payload["experience_code"] == "no_experience"
    assert payload["source_status"] == "closed"
    assert payload["closed_reason"] == "provider_status"
    assert payload["source_modified_at"] == "2026-08-08T10:00:00Z"


def test_generic_normalizer_keeps_unknown_and_canonicalizes_values():
    normalized = normalize_vacancy_mapping(
        {
            "source": "custom",
            "external_id": "x",
            "title": " Role ",
            "salary_from": "0",
            "salary_to": "1 500,50",
            "currency": "BYR",
            "schedule": "Flexible hours",
            "published_at": "not-a-date",
        }
    ).as_mapping()
    assert normalized["work_format"] == "unknown"
    assert normalized["employment_code"] == "unknown"
    assert normalized["experience_code"] == "unknown"
    assert normalized["salary_from"] is None
    assert normalized["salary_to"] == 1500.5
    assert normalized["currency"] == "BYN"
    assert normalized["published_at"] is None
    assert canonical_currency("rur") == "RUB"


def test_common_filter_uses_codes_and_excludes_unknown():
    now = datetime(2026, 8, 8, 12, 0, tzinfo=timezone.utc)
    items = [
        normalize_vacancy_mapping(
            {
                "source": "test",
                "external_id": "remote",
                "title": "Python",
                "work_format": "remote",
                "employment_code": "full",
                "experience_code": "between_1_and_3",
                "currency": "RUB",
                "salary_from": 100000,
                "published_at": "2026-08-08T10:00:00Z",
            }
        ).as_mapping(),
        normalize_vacancy_mapping(
            {
                "source": "test",
                "external_id": "unknown",
                "title": "Python",
                "work_format": "unknown",
                "employment_code": "unknown",
                "experience_code": "unknown",
                "published_at": "2026-08-08T10:00:00Z",
            }
        ).as_mapping(),
    ]
    filters = VacancySearchFilters(
        work_format="remote",
        employment="full",
        experience="between_1_and_3",
        currency="RUB",
        salary_from=90000,
        period_days=7,
    )
    assert [item["external_id"] for item in filter_vacancies(items, filters)] == ["remote"]


def test_store_persists_contract_and_uses_exact_codes(tmp_path):
    store = VacancyStore(tmp_path / "search001.db")
    store.init()
    assert store.upsert_many(
        [
            {
                "source": "trudvsem",
                "external_id": "hybrid-1",
                "title": "Аналитик",
                "company": "ACME",
                "location": "Казань",
                "work_format": "hybrid",
                "employment_code": "full",
                "experience_code": "between_1_and_3",
                "schedule": "Гибрид",
                "employment": "Полная занятость",
                "experience": "Опыт 1-3 года",
                "published_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "source": "trudvsem",
                "external_id": "unknown-1",
                "title": "Аналитик",
                "location": "Казань",
                "work_format": "unknown",
                "employment_code": "unknown",
                "experience_code": "unknown",
                "published_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
    ) == 2

    items = store.search(
        keyword="",
        sources=["trudvsem"],
        work_format="hybrid",
        employment="full",
        experience="between_1_and_3",
        period_days=30,
    )
    assert [item["external_id"] for item in items] == ["hybrid-1"]
    source = store.repository.get_source("trudvsem", "hybrid-1")
    assert source is not None
    assert source.work_format == "hybrid"
    assert source.employment_code == "full"
    canonical = store.repository.get_canonical(source.vacancy_id)
    assert canonical is not None
    assert canonical.experience_code == "between_1_and_3"


def test_migration_0005_is_additive_and_remote_backfill_is_conservative(tmp_path):
    url = _sqlite_url(tmp_path / "migration.db")
    upgrade_database(url, "20260807_0004")
    runtime = create_database(url)
    try:
        with runtime.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO vacancies (
                        id, fingerprint, title, remote, is_active, created_at, updated_at
                    ) VALUES ('legacy-v', 'legacy', 'Legacy', 1, 1, 1, 1)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO vacancy_source_records (
                        vacancy_id, source, external_id, title, remote,
                        source_status, first_seen_at, last_seen_at, fetched_at, updated_at
                    ) VALUES (
                        'legacy-v', 'legacy', 'legacy-1', 'Legacy', 1,
                        'active', 1, 1, 1, 1
                    )
                    """
                )
            )
    finally:
        runtime.dispose()

    upgrade_database(url)
    runtime = create_database(url)
    try:
        inspector = inspect(runtime.engine)
        vacancy_columns = {column["name"] for column in inspector.get_columns("vacancies")}
        source_columns = {
            column["name"] for column in inspector.get_columns("vacancy_source_records")
        }
        assert {"work_format", "employment_code", "experience_code"} <= vacancy_columns
        assert {"work_format", "employment_code", "experience_code"} <= source_columns
        with runtime.session() as session:
            source = session.scalar(
                select(VacancySourceRecord).where(
                    VacancySourceRecord.external_id == "legacy-1"
                )
            )
            assert source is not None
            assert source.work_format == "remote"
            assert source.employment_code is None
            assert session.get(Vacancy, "legacy-v").work_format == "remote"
    finally:
        runtime.dispose()

    downgrade_database(url, "20260807_0004")
    runtime = create_database(url)
    try:
        source_columns = {
            column["name"]
            for column in inspect(runtime.engine).get_columns("vacancy_source_records")
        }
        assert "work_format" not in source_columns
        assert "employment_code" not in source_columns
        assert "experience_code" not in source_columns
    finally:
        runtime.dispose()
