"""JOB-004 deterministic metrics, cohort, isolation and query-bound tests."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import event

from database import create_database, upgrade_database
from models import User, SavedVacancy, SavedVacancySource, SavedVacancyTracker, SavedVacancyTrackerEvent
from repositories.job_analytics import JobAnalyticsRepository
from services.job_analytics import JobAnalyticsService, conversion

NOW = 2_000_000_000


@pytest.fixture
def analytics_env(tmp_path):
    url = f"sqlite:///{tmp_path}/analytics.db"
    upgrade_database(url)
    db = create_database(url)
    owner, other = str(uuid4()), str(uuid4())
    with db.session() as session, session.begin():
        for uid in (owner, other):
            session.add(User(id=uid, status="active", email_verified_at=1, password_hash="hash", created_at=1, updated_at=1))
    repo = JobAnalyticsRepository(db)
    yield SimpleNamespace(db=db, owner=owner, other=other, repo=repo, svc=JobAnalyticsService(repo, clock=lambda: NOW))
    db.dispose()


def add_saved(env, owner, *, age_days, sources=(), state=None, milestones=()):
    saved_id = str(uuid4())
    with env.db.session() as session, session.begin():
        # Deliberately invalid JSON proves analytics never loads/deserializes snapshots.
        session.add(SavedVacancy(id=saved_id, user_id=owner, snapshot_json="not-json", snapshot_hash="0" * 64,
            snapshot_version="saved-vacancy-v1", title="Role", company="Co", location="Remote", search_text="role",
            note="", revision=1, created_at=NOW-age_days*86400, updated_at=NOW))
        session.flush()
        for index, source in enumerate(sources):
            session.add(SavedVacancySource(id=str(uuid4()), saved_vacancy_id=saved_id, user_id=owner,
                source=source, external_id=f"{saved_id}-{index}", identity_hash=f"{uuid4().hex}{uuid4().hex}",
                url="https://example.invalid", created_at=NOW))
        if state:
            session.add(SavedVacancyTracker(saved_vacancy_id=saved_id, user_id=owner, state=state,
                revision=max(1, len(milestones)), created_at=NOW, updated_at=NOW))
            session.flush()
            current = "saved"
            for revision, target in enumerate(milestones, 1):
                session.add(SavedVacancyTrackerEvent(id=str(uuid4()), saved_vacancy_id=saved_id, user_id=owner,
                    from_state=current, to_state=target, event_revision=revision,
                    created_at=NOW + 365*86400))
                current = target
    return saved_id


def test_exact_metrics_history_after_window_repeats_reopen_and_missing_tracker(analytics_env):
    e = analytics_env
    add_saved(e, e.owner, age_days=2, sources=("hh", "reed"), state="preparing",
              milestones=("preparing", "submitted_user_reported", "preparing", "submitted_user_reported",
                          "in_process_user_reported", "closed", "saved", "preparing"))
    add_saved(e, e.owner, age_days=3, sources=("hh",))  # virtual saved
    add_saved(e, e.owner, age_days=4, sources=("reed",), state="closed", milestones=("closed",))
    report = e.svc.report(e.owner, period="7")
    assert {key: report[key] for key in ("saved_count", "preparing_ever_count", "submitted_ever_count",
        "in_process_ever_count", "active_pipeline_count", "closed_current_count")} == {
        "saved_count": 3, "preparing_ever_count": 1, "submitted_ever_count": 1,
        "in_process_ever_count": 1, "active_pipeline_count": 2, "closed_current_count": 1}
    assert report["current_state_distribution"] == {
        "saved": 1, "preparing": 1, "submitted_user_reported": 0, "in_process_user_reported": 0, "closed": 1}
    assert report["saved_to_submitted"].denominator == 3
    assert report["submitted_to_in_process"].denominator == 1


def test_periods_sources_overlap_invalid_filter_isolation_and_two_queries(analytics_env):
    e = analytics_env
    for age, sources in ((6, ("hh", "reed")), (20, ("hh",)), (60, ("reed",)), (120, ("other",))):
        add_saved(e, e.owner, age_days=age, sources=sources)
    add_saved(e, e.other, age_days=1, sources=("secret",), state="closed", milestones=("closed",))
    assert [e.svc.report(e.owner, period=p)["saved_count"] for p in ("7", "30", "90", "all")] == [1, 2, 3, 4]
    assert e.svc.report(e.owner, period="all", source="hh")["saved_count"] == 2
    assert e.svc.report(e.owner, period="all", source="reed")["saved_count"] == 2
    assert e.svc.report(e.owner, period="all", source="secret")["saved_count"] == 0
    assert "secret" not in e.svc.report(e.owner)["sources"]
    count = 0
    def before(*_args):
        nonlocal count
        count += 1
    event.listen(e.db.engine, "before_cursor_execute", before)
    try:
        e.svc.report(e.owner, period="all")
    finally:
        event.remove(e.db.engine, "before_cursor_execute", before)
    assert count == 2


@pytest.mark.parametrize("denominator,visible,small", [(0, False, False), (4, False, False), (5, True, True), (19, True, True), (20, True, False)])
def test_conversion_sample_boundaries(denominator, visible, small):
    result = conversion(min(2, denominator), denominator)
    assert (result.percentage is not None) is visible
    assert (result.caveat is not None and "Малая выборка" in result.caveat) is small
