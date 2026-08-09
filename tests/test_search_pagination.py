from __future__ import annotations

from datetime import datetime, timedelta, timezone

from database import (
    CURRENT_REVISION,
    create_database,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from repositories import SearchSnapshotRepository
from services.base_provider import SearchResult
from services.search_aggregation import (
    SearchAggregationService,
    deterministic_sort_key,
    search_query_fingerprint,
)
from services.search_filters import VacancySearchFilters


def _iso(minutes_ago: int) -> str:
    return (
        datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _vacancy(
    *,
    source: str,
    external_id: str,
    title: str,
    minutes_ago: int,
    salary: int = 100_000,
    company: str = "ACME",
) -> dict:
    return {
        "source": source,
        "source_title": source,
        "external_id": external_id,
        "title": title,
        "company": company,
        "location": "Москва",
        "work_format": "remote",
        "employment_code": "full",
        "experience_code": "between_1_and_3",
        "salary_from": salary,
        "salary_to": salary,
        "currency": "RUB",
        "description": f"{title} Python PostgreSQL",
        "requirements": "Python SQL",
        "published_at": _iso(minutes_ago),
        "url": f"https://{source}.example.test/{external_id}",
        "source_status": "active",
    }


def _runtime(tmp_path):
    url = f"sqlite:///{(tmp_path / 'search.db').resolve().as_posix()}"
    upgrade_database(url)
    return url, create_database(url)


def test_query_fingerprint_is_stable_and_changes_with_filters():
    filters = VacancySearchFilters(keyword="Python", sort="date")
    first = search_query_fingerprint(filters, ["hh", "superjob"], page_size=2)
    second = search_query_fingerprint(filters, ["superjob", "hh"], page_size=2)
    changed = search_query_fingerprint(
        VacancySearchFilters(keyword="Python", sort="salary_desc"),
        ["hh", "superjob"],
        page_size=2,
    )

    assert first == second
    assert first != changed
    assert len(first) == 64


def test_deterministic_sort_has_explicit_tie_breakers():
    left = _vacancy(
        source="hh",
        external_id="2",
        title="Python Developer B",
        minutes_ago=1,
        salary=200_000,
    )
    right = _vacancy(
        source="superjob",
        external_id="1",
        title="Python Developer A",
        minutes_ago=1,
        salary=200_000,
    )

    ordered = sorted(
        [left, right],
        key=lambda item: deterministic_sort_key(
            item,
            sort_code="salary_desc",
            keyword="Python",
        ),
    )
    assert [item["title"] for item in ordered] == [
        "Python Developer A",
        "Python Developer B",
    ]


def test_snapshot_pages_are_stable_and_survive_service_restart(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        repository = SearchSnapshotRepository(runtime)
        service = SearchAggregationService(
            repository,
            page_size=2,
            ttl_seconds=900,
            max_candidates=50,
            max_rounds_per_request=1,
        )
        pages = {
            ("hh", 0): [
                _vacancy(source="hh", external_id="h1", title="A", minutes_ago=1),
                _vacancy(source="hh", external_id="h2", title="C", minutes_ago=3),
            ],
            ("superjob", 0): [
                _vacancy(source="superjob", external_id="s1", title="B", minutes_ago=2),
                _vacancy(source="superjob", external_id="s2", title="D", minutes_ago=4),
            ],
            ("hh", 1): [
                _vacancy(source="hh", external_id="h3", title="E", minutes_ago=5),
            ],
            ("superjob", 1): [
                _vacancy(source="superjob", external_id="s3", title="F", minutes_ago=6),
            ],
        }

        def fetch(source: str, page: int) -> SearchResult:
            items = pages.get((source, page), [])
            return SearchResult(
                items=items,
                total=3,
                page=page,
                pages=2,
                has_next=page == 0,
            )

        filters = VacancySearchFilters(keyword="", sort="date", period_days=30)
        first = service.search(
            filters=filters,
            selected_sources=["hh", "superjob"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )
        assert [item["title"] for item in first.items] == ["A", "B"]
        snapshot_id = first.snapshot.id

        second = service.search(
            filters=filters,
            selected_sources=["hh", "superjob"],
            page=1,
            snapshot_id=snapshot_id,
            fetch_source=fetch,
        )
        assert [item["title"] for item in second.items] == ["C", "D"]

        # Recreate the service to model a new Gunicorn process after restart.
        restarted_service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=2,
            ttl_seconds=900,
            max_candidates=50,
            max_rounds_per_request=1,
        )
        first_again = restarted_service.search(
            filters=filters,
            selected_sources=["hh", "superjob"],
            page=0,
            snapshot_id=snapshot_id,
            fetch_source=fetch,
        )
        assert [item["title"] for item in first_again.items] == ["A", "B"]
        assert first_again.snapshot.id == snapshot_id
    finally:
        runtime.dispose()


def test_totals_are_exact_only_after_all_source_cursors_exhausted(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=2,
            ttl_seconds=900,
            max_candidates=20,
            max_rounds_per_request=1,
        )

        def fetch(source: str, page: int) -> SearchResult:
            assert page == 0
            return SearchResult(
                items=[
                    _vacancy(
                        source=source,
                        external_id=f"{source}-1",
                        title=f"{source} role",
                        minutes_ago=1,
                    )
                ],
                total=1,
                page=0,
                pages=1,
                has_next=False,
            )

        result = service.search(
            filters=VacancySearchFilters(period_days=30),
            selected_sources=["hh", "superjob"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )
        assert result.provider_reported_total == 2
        assert result.known_unique_total == 2
        assert result.total_is_exact is True
        assert result.has_next is False
    finally:
        runtime.dispose()


def test_cross_source_duplicate_reduces_known_unique_total(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=10,
            ttl_seconds=900,
            max_candidates=50,
            max_rounds_per_request=1,
        )
        shared = {
            "title": "Python backend developer",
            "company": "ООО ACME",
            "location": "Москва",
            "work_format": "remote",
            "employment_code": "full",
            "experience_code": "between_1_and_3",
            "salary_from": 180_000,
            "salary_to": 220_000,
            "currency": "RUB",
            "description": "Python API PostgreSQL integrations",
            "requirements": "Python SQL REST",
            "published_at": _iso(1),
            "source_status": "active",
        }

        def fetch(source: str, page: int) -> SearchResult:
            item = {
                **shared,
                "source": source,
                "source_title": source,
                "external_id": f"{source}-1",
                "url": f"https://{source}.example.test/1",
            }
            return SearchResult(items=[item], total=1, page=page, pages=1, has_next=False)

        result = service.search(
            filters=VacancySearchFilters(keyword="Python", period_days=30),
            selected_sources=["hh", "superjob"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )
        assert result.snapshot.candidate_count == 2
        assert result.known_unique_total == 1
        assert result.deduplication_stats["cross_source_duplicate_count"] == 1
        assert result.items[0]["source_count"] == 2
    finally:
        runtime.dispose()


def test_provider_failure_keeps_materialized_page_available(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        repository = SearchSnapshotRepository(runtime)
        service = SearchAggregationService(
            repository,
            page_size=1,
            ttl_seconds=900,
            max_candidates=20,
            max_rounds_per_request=1,
        )
        calls = {"count": 0}

        def fetch(source: str, page: int) -> SearchResult:
            calls["count"] += 1
            if page > 0:
                raise RuntimeError("upstream unavailable")
            return SearchResult(
                items=[
                    _vacancy(
                        source=source,
                        external_id="1",
                        title="Stable role",
                        minutes_ago=1,
                    )
                ],
                total=10,
                page=0,
                pages=10,
                has_next=True,
            )

        filters = VacancySearchFilters(period_days=30)
        first = service.search(
            filters=filters,
            selected_sources=["hh"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )
        second = service.search(
            filters=filters,
            selected_sources=["hh"],
            page=0,
            snapshot_id=first.snapshot.id,
            fetch_source=fetch,
        )
        assert second.items[0]["title"] == "Stable role"
        assert second.snapshot.id == first.snapshot.id
    finally:
        runtime.dispose()


def test_migration_0007_round_trip(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'migrate.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        tables = set(__import__("sqlalchemy").inspect(runtime.engine).get_table_names())
        assert {
            "search_snapshots",
            "search_snapshot_sources",
            "search_snapshot_candidates",
            "search_snapshot_items",
        } <= tables
        assert current_revision(runtime.engine) == "20260809_0007"
    finally:
        runtime.dispose()

    downgrade_database(database_url, "20260809_0006")
    runtime = create_database(database_url)
    try:
        tables = set(__import__("sqlalchemy").inspect(runtime.engine).get_table_names())
        assert "search_snapshots" not in tables
        assert current_revision(runtime.engine) == "20260809_0006"
    finally:
        runtime.dispose()

    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == CURRENT_REVISION
    finally:
        runtime.dispose()


def test_late_cross_page_duplicate_updates_committed_card_without_overlap(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=1,
            ttl_seconds=900,
            max_candidates=50,
            max_rounds_per_request=1,
            buffer_items=1,
        )
        shared_hh = _vacancy(
            source="hh",
            external_id="hh-shared",
            title="Python backend developer",
            company="ООО ACME",
            minutes_ago=1,
            salary=200_000,
        )
        shared_sj = {
            **shared_hh,
            "source": "superjob",
            "source_title": "superjob",
            "external_id": "sj-shared",
            "url": "https://superjob.example.test/sj-shared",
        }
        pages = {
            ("hh", 0): [shared_hh],
            ("superjob", 0): [
                _vacancy(
                    source="superjob",
                    external_id="sj-b",
                    title="Data engineer",
                    minutes_ago=2,
                )
            ],
            ("hh", 1): [
                _vacancy(
                    source="hh",
                    external_id="hh-c",
                    title="QA engineer",
                    minutes_ago=3,
                )
            ],
            ("superjob", 1): [shared_sj],
        }

        def fetch(source: str, page: int) -> SearchResult:
            return SearchResult(
                items=pages.get((source, page), []),
                total=2,
                page=page,
                pages=2,
                has_next=page == 0,
            )

        filters = VacancySearchFilters(period_days=30, sort="date")
        first = service.search(
            filters=filters,
            selected_sources=["hh", "superjob"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )
        first_key = first.items[0]["external_id"]

        second = service.search(
            filters=filters,
            selected_sources=["hh", "superjob"],
            page=1,
            snapshot_id=first.snapshot.id,
            fetch_source=fetch,
        )
        first_again = service.search(
            filters=filters,
            selected_sources=["hh", "superjob"],
            page=0,
            snapshot_id=first.snapshot.id,
            fetch_source=fetch,
        )

        assert first_again.items[0]["external_id"] == first_key
        assert first_again.items[0]["source_count"] == 2
        assert second.items[0]["external_id"] != first_key
        assert second.known_unique_total == 3
        assert second.deduplication_stats["cross_source_duplicate_count"] == 1
    finally:
        runtime.dispose()


def test_mismatched_snapshot_restarts_from_first_page(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=1,
            ttl_seconds=900,
            max_candidates=20,
            max_rounds_per_request=1,
        )

        def fetch(source: str, page: int) -> SearchResult:
            title = "Python developer" if page == 0 else "Java developer"
            return SearchResult(
                items=[
                    _vacancy(
                        source=source,
                        external_id=f"{source}-{page}",
                        title=title,
                        minutes_ago=page + 1,
                    )
                ],
                total=1,
                page=page,
                pages=1,
                has_next=False,
            )

        first = service.search(
            filters=VacancySearchFilters(keyword="Python", period_days=30),
            selected_sources=["hh"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )
        replaced = service.search(
            filters=VacancySearchFilters(keyword="Java", period_days=30),
            selected_sources=["hh"],
            page=5,
            snapshot_id=first.snapshot.id,
            fetch_source=fetch,
        )

        assert replaced.snapshot.id != first.snapshot.id
        assert replaced.page == 0
        assert replaced.snapshot_restarted is True
    finally:
        runtime.dispose()


def test_provider_reported_total_stays_approximate_until_exhaustion(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=1,
            ttl_seconds=900,
            max_candidates=20,
            max_rounds_per_request=1,
        )

        def fetch(source: str, page: int) -> SearchResult:
            return SearchResult(
                items=[
                    _vacancy(
                        source=source,
                        external_id=f"{source}-{page}",
                        title=f"Role {page}",
                        minutes_ago=page + 1,
                    )
                ],
                total=100,
                page=page,
                pages=100,
                has_next=True,
            )

        result = service.search(
            filters=VacancySearchFilters(period_days=30),
            selected_sources=["hh"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )
        assert result.provider_reported_total == 100
        assert result.known_unique_total >= 1
        assert result.total_is_exact is False
        assert result.has_next is True
    finally:
        runtime.dispose()


def test_snapshot_ttl_cleanup_does_not_touch_vacancy_cache(tmp_path):
    from services.vacancy_store import VacancyStore

    _url, runtime = _runtime(tmp_path)
    try:
        store = VacancyStore(runtime)
        store.upsert_many(
            [
                _vacancy(
                    source="trudvsem",
                    external_id="keep-me",
                    title="Persistent vacancy",
                    minutes_ago=1,
                )
            ],
            seen_at=100,
        )
        repository = SearchSnapshotRepository(runtime)
        snapshot = repository.create(
            query_fingerprint="b" * 64,
            selected_sources=["hh"],
            sort_code="date",
            page_size=20,
            ttl_seconds=60,
            now=100,
        )
        assert repository.get(snapshot.id, now=120) is not None
        assert repository.cleanup_expired(now=161) == 1
        assert repository.get(snapshot.id, now=161, include_expired=True) is None
        assert store.count(
            keyword="",
            sources=["trudvsem"],
            period_days=30,
        ) == 1
    finally:
        runtime.dispose()


def test_late_arrival_is_appended_and_counted_once(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=1,
            ttl_seconds=900,
            max_candidates=20,
            max_rounds_per_request=1,
            buffer_items=1,
        )
        pages = {
            0: [
                _vacancy(
                    source="hh",
                    external_id="old",
                    title="Old committed role",
                    minutes_ago=10,
                )
            ],
            1: [
                _vacancy(
                    source="hh",
                    external_id="late-new",
                    title="Newer late role",
                    minutes_ago=1,
                )
            ],
        }

        def fetch(_source: str, page: int) -> SearchResult:
            return SearchResult(
                items=pages.get(page, []),
                total=2,
                page=page,
                pages=2,
                has_next=page == 0,
            )

        filters = VacancySearchFilters(period_days=30, sort="date")
        first = service.search(
            filters=filters,
            selected_sources=["hh"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )
        second = service.search(
            filters=filters,
            selected_sources=["hh"],
            page=1,
            snapshot_id=first.snapshot.id,
            fetch_source=fetch,
        )
        repeated = service.search(
            filters=filters,
            selected_sources=["hh"],
            page=0,
            snapshot_id=first.snapshot.id,
            fetch_source=fetch,
        )

        assert first.items[0]["external_id"] == "old"
        assert second.items[0]["external_id"] == "late-new"
        assert second.late_arrival_count == 1
        assert repeated.items[0]["external_id"] == "old"
        assert repeated.late_arrival_count == 1
    finally:
        runtime.dispose()


def test_anonymous_provider_rows_on_different_pages_do_not_overwrite(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=1,
            ttl_seconds=900,
            max_candidates=20,
            max_rounds_per_request=1,
            buffer_items=1,
        )

        def anonymous(location: str, minutes_ago: int) -> dict:
            item = _vacancy(
                source="hh",
                external_id=f"temporary-{location}",
                title="Anonymous analyst",
                company="ACME",
                minutes_ago=minutes_ago,
            )
            item.pop("external_id", None)
            item.pop("url", None)
            item["location"] = location
            return item

        pages = {
            0: [anonymous("Москва", 1)],
            1: [anonymous("Санкт-Петербург", 2)],
        }

        def fetch(_source: str, page: int) -> SearchResult:
            return SearchResult(
                items=pages.get(page, []),
                total=2,
                page=page,
                pages=2,
                has_next=page == 0,
            )

        filters = VacancySearchFilters(period_days=30, sort="date")
        first = service.search(
            filters=filters,
            selected_sources=["hh"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )
        second = service.search(
            filters=filters,
            selected_sources=["hh"],
            page=1,
            snapshot_id=first.snapshot.id,
            fetch_source=fetch,
        )

        assert first.items[0]["location"] == "Москва"
        assert second.items[0]["location"] == "Санкт-Петербург"
        assert second.snapshot.candidate_count == 2
        assert second.known_unique_total == 2
    finally:
        runtime.dispose()


def test_candidate_ceiling_does_not_make_naturally_exhausted_total_approximate(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=2,
            ttl_seconds=900,
            max_candidates=2,
            max_rounds_per_request=1,
        )

        def fetch(source: str, page: int) -> SearchResult:
            assert page == 0
            return SearchResult(
                items=[
                    _vacancy(
                        source=source,
                        external_id=f"{source}-1",
                        title=f"{source} exact role",
                        minutes_ago=1,
                    )
                ],
                total=1,
                page=0,
                pages=1,
                has_next=False,
            )

        result = service.search(
            filters=VacancySearchFilters(period_days=30),
            selected_sources=["hh", "superjob"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )

        assert result.snapshot.candidate_count == 2
        assert result.known_unique_total == 2
        assert result.bounded is False
        assert result.total_is_exact is True
        assert result.has_next is False
    finally:
        runtime.dispose()


def test_per_source_page_ceiling_is_reported_as_bounded_not_exact(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=1,
            ttl_seconds=900,
            max_pages_per_source=1,
            max_candidates=20,
            max_rounds_per_request=3,
        )

        def fetch(source: str, page: int) -> SearchResult:
            return SearchResult(
                items=[
                    _vacancy(
                        source=source,
                        external_id=f"{source}-{page}",
                        title=f"Bounded role {page}",
                        minutes_ago=page + 1,
                    )
                ],
                total=100,
                page=page,
                pages=100,
                has_next=True,
            )

        result = service.search(
            filters=VacancySearchFilters(period_days=30),
            selected_sources=["hh"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )

        assert result.bounded is True
        assert result.total_is_exact is False
        assert result.has_next is False
        assert result.source_results["hh"].bounded is True
        assert result.source_results["hh"].fetched_pages == 1
    finally:
        runtime.dispose()


def test_public_snapshot_summary_omits_query_fingerprint_and_payload(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        repository = SearchSnapshotRepository(runtime)
        service = SearchAggregationService(
            repository,
            page_size=1,
            ttl_seconds=900,
            max_candidates=20,
            max_rounds_per_request=1,
        )

        def fetch(source: str, page: int) -> SearchResult:
            return SearchResult(
                items=[
                    _vacancy(
                        source=source,
                        external_id="private-query-result",
                        title="Confidential keyword role",
                        minutes_ago=1,
                    )
                ],
                total=1,
                page=page,
                pages=1,
                has_next=False,
            )

        result = service.search(
            filters=VacancySearchFilters(
                keyword="Confidential keyword",
                region="Secret region",
                salary_from=123456,
                period_days=30,
            ),
            selected_sources=["hh"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )
        summary = repository.aggregate_summary(result.snapshot.id)
        encoded = __import__("json").dumps(summary, ensure_ascii=False)

        assert summary is not None
        assert "query_fingerprint" not in summary
        assert "selected_sources_json" not in summary
        assert "Confidential keyword" not in encoded
        assert "Secret region" not in encoded
        assert "123456" not in encoded
        assert "payload_json" not in encoded
    finally:
        runtime.dispose()


def test_global_page_boundary_fetches_required_depth_from_each_provider(tmp_path):
    """Aggregate cardinality must not hide a shallow provider cursor.

    With a global page size of two, HeadHunter's second result outranks Reed's
    first result. The service therefore has to fetch two accepted identities
    from each non-terminal provider before committing page zero, even though
    the first fetch round already produced enough aggregate rows.
    """

    _url, runtime = _runtime(tmp_path)
    try:
        service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=2,
            ttl_seconds=900,
            max_candidates=20,
            max_rounds_per_request=2,
            buffer_items=1,
        )
        pages = {
            ("hh", 0): [
                _vacancy(
                    source="hh",
                    external_id="hh-1",
                    title="HH newest",
                    minutes_ago=1,
                )
            ],
            ("hh", 1): [
                _vacancy(
                    source="hh",
                    external_id="hh-2",
                    title="HH second",
                    minutes_ago=2,
                )
            ],
            ("reed", 0): [
                _vacancy(
                    source="reed",
                    external_id="reed-1",
                    title="Reed old",
                    minutes_ago=100,
                )
            ],
            ("reed", 1): [
                _vacancy(
                    source="reed",
                    external_id="reed-2",
                    title="Reed older",
                    minutes_ago=101,
                )
            ],
        }
        calls: list[tuple[str, int]] = []

        def fetch(source: str, page: int) -> SearchResult:
            calls.append((source, page))
            return SearchResult(
                items=pages.get((source, page), []),
                total=2,
                page=page,
                pages=2,
                has_next=page == 0,
            )

        result = service.search(
            filters=VacancySearchFilters(period_days=30, sort="date"),
            selected_sources=["hh", "reed"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )

        assert ("hh", 1) in calls
        assert ("reed", 1) in calls
        assert [item["external_id"] for item in result.items] == ["hh-1", "hh-2"]
        assert result.total_is_exact is True
    finally:
        runtime.dispose()


def test_identical_anonymous_rows_keep_distinct_snapshot_stable_keys(tmp_path):
    _url, runtime = _runtime(tmp_path)
    try:
        service = SearchAggregationService(
            SearchSnapshotRepository(runtime),
            page_size=1,
            ttl_seconds=900,
            max_candidates=20,
            max_rounds_per_request=1,
            buffer_items=1,
        )

        def anonymous(minutes_ago: int) -> dict:
            item = _vacancy(
                source="hh",
                external_id="temporary",
                title="Anonymous analyst",
                company="ACME",
                minutes_ago=minutes_ago,
            )
            item.pop("external_id", None)
            item.pop("url", None)
            return item

        pages = {0: [anonymous(1)], 1: [anonymous(2)]}

        def fetch(_source: str, page: int) -> SearchResult:
            return SearchResult(
                items=pages.get(page, []),
                total=2,
                page=page,
                pages=2,
                has_next=page == 0,
            )

        filters = VacancySearchFilters(period_days=30, sort="date")
        first = service.search(
            filters=filters,
            selected_sources=["hh"],
            page=0,
            snapshot_id=None,
            fetch_source=fetch,
        )
        second = service.search(
            filters=filters,
            selected_sources=["hh"],
            page=1,
            snapshot_id=first.snapshot.id,
            fetch_source=fetch,
        )

        rows = SearchSnapshotRepository(runtime).items(first.snapshot.id)
        assert len(rows) == 2
        assert len({row.stable_key for row in rows}) == 2
        assert first.items[0]["published_at"] != second.items[0]["published_at"]
    finally:
        runtime.dispose()
