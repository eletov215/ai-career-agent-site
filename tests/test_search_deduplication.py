from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import inspect, select

from database import create_database, downgrade_database, upgrade_database
from models import Vacancy, VacancySourceRecord
from services.vacancy_deduplication import (
    DEDUP_VERSION,
    build_dedup_identity,
    compare_vacancies,
    deduplicate_vacancies,
)
from services.vacancy_store import VacancyStore


def _vacancy(
    *,
    source: str,
    external_id: str,
    title: str = "Python backend developer",
    company: str = "ACME",
    location: str = "Москва",
    work_format: str = "hybrid",
    employment_code: str = "full",
    experience_code: str = "between_1_and_3",
    salary_from: int | None = 180000,
    salary_to: int | None = 240000,
    currency: str = "RUB",
    description: str = "Разработка Python API, PostgreSQL и интеграций",
    requirements: str = "Python SQL REST",
    published_at: str = "2026-08-08T10:00:00Z",
) -> dict:
    return {
        "source": source,
        "source_title": {
            "hh": "HeadHunter",
            "reed": "Reed.co.uk",
            "superjob": "SuperJob",
            "trudvsem": "Работа России",
        }.get(source, source),
        "external_id": external_id,
        "title": title,
        "company": company,
        "location": location,
        "work_format": work_format,
        "employment_code": employment_code,
        "experience_code": experience_code,
        "salary_from": salary_from,
        "salary_to": salary_to,
        "currency": currency,
        "description": description,
        "requirements": requirements,
        "published_at": published_at,
        "url": f"https://{source}.example.test/{external_id}",
        "source_status": "active",
    }


def _sqlite_url(path) -> str:  # noqa: ANN001
    return f"sqlite:///{path.resolve().as_posix()}"


def test_exact_cross_source_duplicates_merge_and_preserve_source_records():
    result = deduplicate_vacancies(
        [
            _vacancy(source="hh", external_id="hh-1"),
            _vacancy(source="trudvsem", external_id="tv-1", company='ООО "ACME"'),
        ]
    )

    assert result.stats.input_count == 2
    assert result.stats.output_count == 1
    assert result.stats.duplicate_count == 1
    assert result.stats.cross_source_groups == 1
    merged = result.items[0]
    assert merged["source_count"] == 2
    assert merged["duplicate_count"] == 1
    assert merged["is_cross_source_duplicate"] is True
    assert {row["source"] for row in merged["source_records"]} == {"hh", "trudvsem"}
    assert merged["deduplication"]["method"] == "exact_fingerprint"
    assert merged["deduplication"]["confidence"] >= 0.9




def test_same_provider_identity_is_collapsed_before_cross_source_grouping():
    result = deduplicate_vacancies(
        [
            _vacancy(source="hh", external_id="hh-1"),
            _vacancy(
                source="hh",
                external_id="hh-1",
                description="Более полное описание Python API PostgreSQL integrations",
            ),
        ]
    )

    assert result.stats.input_count == 2
    assert result.stats.output_count == 1
    assert result.stats.identity_duplicate_count == 1
    assert result.stats.cross_source_duplicate_count == 0
    assert result.items[0]["source_count"] == 1


def test_unsafe_provider_urls_are_not_exposed_on_merged_card():
    result = deduplicate_vacancies(
        [
            {**_vacancy(source="hh", external_id="hh-unsafe"), "url": "javascript:alert(1)"},
            _vacancy(source="trudvsem", external_id="tv-safe"),
        ]
    )

    merged = result.items[0]
    assert merged["url"] == "https://trudvsem.example.test/tv-safe"
    assert {record["url"] for record in merged["source_records"]} == {
        "",
        "https://trudvsem.example.test/tv-safe",
    }

def test_same_source_distinct_publications_do_not_merge():
    result = deduplicate_vacancies(
        [
            _vacancy(source="hh", external_id="hh-1"),
            _vacancy(source="hh", external_id="hh-2"),
        ]
    )
    assert result.stats.output_count == 2
    assert result.stats.duplicate_count == 0


def test_seniority_conflict_prevents_merge():
    junior = _vacancy(source="hh", external_id="hh-1", title="Junior Python developer")
    senior = _vacancy(source="trudvsem", external_id="tv-1", title="Senior Python developer")
    decision = compare_vacancies(junior, senior)
    assert decision.matched is False
    assert decision.reasons == ("seniority_conflict",)


def test_location_and_currency_conflicts_prevent_merge():
    moscow = _vacancy(source="hh", external_id="hh-1", location="Москва", work_format="onsite")
    kazan = _vacancy(source="trudvsem", external_id="tv-1", location="Казань", work_format="onsite")
    assert compare_vacancies(moscow, kazan).reasons == ("location_conflict",)

    rub = _vacancy(source="hh", external_id="hh-1", currency="RUB")
    gbp = _vacancy(source="reed", external_id="reed-1", currency="GBP")
    assert compare_vacancies(rub, gbp).reasons == ("currency_conflict",)


def test_remote_duplicates_can_merge_despite_location_label_difference():
    left = _vacancy(
        source="hh",
        external_id="hh-1",
        location="Москва",
        work_format="remote",
    )
    right = _vacancy(
        source="trudvsem",
        external_id="tv-1",
        location="Россия",
        work_format="remote",
    )
    assert compare_vacancies(left, right).matched is True


def test_generic_titles_require_extra_evidence():
    left = _vacancy(
        source="hh",
        external_id="hh-1",
        title="Менеджер",
        description="Продажи корпоративным клиентам, холодные звонки и CRM",
        requirements="B2B продажи",
        salary_from=100000,
        salary_to=140000,
    )
    right = _vacancy(
        source="trudvsem",
        external_id="tv-1",
        title="Менеджер",
        description="Управление рестораном, закупки, персонал и кассовая дисциплина",
        requirements="Опыт в общепите",
        salary_from=55000,
        salary_to=70000,
    )
    decision = compare_vacancies(left, right)
    assert decision.matched is False
    assert "generic_title_insufficient_evidence" in decision.reasons or "salary_conflict" in decision.reasons


def test_conservative_similarity_merges_small_title_variation():
    left = _vacancy(
        source="hh",
        external_id="hh-1",
        title="Python backend developer",
        company="ООО ACME",
    )
    right = _vacancy(
        source="superjob",
        external_id="sj-1",
        title="Python backend-разработчик",
        company='ACME, ООО',
    )
    decision = compare_vacancies(left, right)
    assert decision.matched is True
    assert decision.method in {"exact_fingerprint", "conservative_similarity"}
    assert "same_company" in decision.reasons


def test_grouping_uses_complete_link_and_does_not_chain_ambiguous_roles():
    items = [
        _vacancy(source="hh", external_id="1", title="Senior Python developer"),
        _vacancy(source="reed", external_id="2", title="Python developer"),
        _vacancy(source="superjob", external_id="3", title="Junior Python developer"),
    ]
    result = deduplicate_vacancies(items)
    assert result.stats.output_count >= 2
    assert not any(group.get("source_count") == 3 for group in result.items)


def test_dedup_identity_is_deterministic_and_non_unique_candidate_key():
    first = build_dedup_identity(_vacancy(source="hh", external_id="1"))
    second = build_dedup_identity(_vacancy(source="reed", external_id="2"))
    assert first.strict_key == second.strict_key
    assert first.strict_key is not None
    assert len(first.strict_key) == 64


def test_store_persists_search002_dedup_metadata(tmp_path):
    store = VacancyStore(tmp_path / "dedup.db")
    store.init()
    store.upsert_many([_vacancy(source="trudvsem", external_id="tv-1")])

    source = store.repository.get_source("trudvsem", "tv-1")
    assert source is not None
    assert source.dedup_key
    assert source.dedup_version == DEDUP_VERSION
    canonical = store.repository.get_canonical(source.vacancy_id)
    assert canonical is not None
    assert canonical.dedup_key == source.dedup_key
    assert canonical.dedup_version == DEDUP_VERSION

    items = store.search(keyword="", sources=["trudvsem"], period_days=0)
    assert items[0]["dedup_key"] == source.dedup_key
    assert items[0]["dedup_version"] == DEDUP_VERSION



def test_store_links_proven_cross_source_duplicates_to_one_canonical(tmp_path):
    store = VacancyStore(tmp_path / "dedup-merge.db")
    store.init()
    store.upsert_many(
        [
            _vacancy(source="hh", external_id="hh-merge-1"),
            _vacancy(
                source="trudvsem",
                external_id="tv-merge-1",
                company='ООО "ACME"',
            ),
        ]
    )

    hh = store.repository.get_source("hh", "hh-merge-1")
    trudvsem = store.repository.get_source("trudvsem", "tv-merge-1")
    assert hh is not None and trudvsem is not None
    assert hh.vacancy_id == trudvsem.vacancy_id
    sources = store.repository.list_sources(hh.vacancy_id)
    assert {(row.source, row.external_id) for row in sources} == {
        ("hh", "hh-merge-1"),
        ("trudvsem", "tv-merge-1"),
    }



def test_store_splits_a_source_when_a_merged_publication_changes_role(tmp_path):
    store = VacancyStore(tmp_path / "dedup-split.db")
    store.init()
    store.upsert_many(
        [
            _vacancy(source="hh", external_id="hh-split-1"),
            _vacancy(source="trudvsem", external_id="tv-split-1"),
        ]
    )
    initial_hh = store.repository.get_source("hh", "hh-split-1")
    initial_tv = store.repository.get_source("trudvsem", "tv-split-1")
    assert initial_hh is not None and initial_tv is not None
    assert initial_hh.vacancy_id == initial_tv.vacancy_id

    store.upsert_many(
        [
            _vacancy(
                source="trudvsem",
                external_id="tv-split-1",
                title="Senior Java developer",
                description="Java Spring Kafka",
                requirements="Java Spring",
            )
        ]
    )

    updated_hh = store.repository.get_source("hh", "hh-split-1")
    updated_tv = store.repository.get_source("trudvsem", "tv-split-1")
    assert updated_hh is not None and updated_tv is not None
    assert updated_hh.vacancy_id != updated_tv.vacancy_id
    assert store.repository.get_canonical(updated_hh.vacancy_id).title == "Python backend developer"
    assert store.repository.get_canonical(updated_tv.vacancy_id).title == "Senior Java developer"

def test_migration_0006_is_additive_and_does_not_guess_historical_matches(tmp_path):
    url = _sqlite_url(tmp_path / "migration.db")
    upgrade_database(url, "20260808_0005")
    runtime = create_database(url)
    try:
        with runtime.engine.begin() as connection:
            connection.execute(
                Vacancy.__table__.insert().values(
                    id="legacy-v",
                    fingerprint="source:hh:1",
                    title="Python developer",
                    remote=False,
                    is_active=True,
                    created_at=1,
                    updated_at=1,
                )
            )
            connection.execute(
                VacancySourceRecord.__table__.insert().values(
                    vacancy_id="legacy-v",
                    source="hh",
                    external_id="1",
                    title="Python developer",
                    remote=False,
                    source_status="active",
                    first_seen_at=1,
                    last_seen_at=1,
                    fetched_at=1,
                    updated_at=1,
                )
            )
    finally:
        runtime.dispose()

    upgrade_database(url, "20260809_0006")
    runtime = create_database(url)
    try:
        inspector = inspect(runtime.engine)
        vacancy_columns = {column["name"] for column in inspector.get_columns("vacancies")}
        source_columns = {
            column["name"] for column in inspector.get_columns("vacancy_source_records")
        }
        assert {"dedup_key", "dedup_version"} <= vacancy_columns
        assert {"dedup_key", "dedup_version"} <= source_columns
        with runtime.session() as session:
            vacancy = session.get(Vacancy, "legacy-v")
            source = session.scalar(select(VacancySourceRecord))
            assert vacancy is not None and vacancy.dedup_key is None
            assert source is not None and source.dedup_key is None
    finally:
        runtime.dispose()

    downgrade_database(url, "20260808_0005")
    runtime = create_database(url)
    try:
        inspector = inspect(runtime.engine)
        assert "dedup_key" not in {
            column["name"] for column in inspector.get_columns("vacancies")
        }
    finally:
        runtime.dispose()


def test_anonymous_same_provider_rows_keep_distinct_group_ids():
    first = _vacancy(source="hh", external_id="anonymous-1")
    second = _vacancy(source="hh", external_id="anonymous-2")
    for item in (first, second):
        item.pop("external_id", None)
        item.pop("url", None)

    result = deduplicate_vacancies([first, second])

    assert len(result.items) == 2
    assert len({item["dedup_group_id"] for item in result.items}) == 2
    assert all("_dedup_anonymous_key" not in item for item in result.items)
