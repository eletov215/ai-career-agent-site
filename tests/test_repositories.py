from __future__ import annotations

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from database import create_database, upgrade_database
from models import (
    AuthSession,
    AuthToken,
    HeadHunterAccount,
    OAuthConnection,
    SuperJobAccount,
    SyncRun,
    User,
    Vacancy,
    VacancySourceRecord,
)
from repositories import AuthRepository, OAuthConnectionRepository, SyncRunRepository, UserRepository
from services.vacancy_store import VacancyStore


def _runtime(tmp_path):
    url = f"sqlite:///{(tmp_path / 'repositories.db').resolve().as_posix()}"
    upgrade_database(url)
    return create_database(url)


def test_user_and_oauth_repositories_detach_domain_records(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        users = UserRepository(runtime)
        oauth = OAuthConnectionRepository(runtime)

        user = users.create(email="  User@Example.TEST ", display_name="Test User")
        assert user.normalized_email == "user@example.test"
        assert users.find_by_email("USER@example.test").id == user.id

        with pytest.raises(IntegrityError):
            users.create(email="user@example.test")

        connection = oauth.upsert(
            provider="superjob",
            external_user_id="101",
            display_name="Super Job",
            email="sj@example.test",
            access_token="encrypted-access",
            refresh_token="encrypted-refresh",
            expires_at=100,
            profile_json="{}",
        )
        assert connection.user_id is None

        updated = oauth.upsert(
            provider="superjob",
            external_user_id="101",
            display_name="Super Job Updated",
            email="sj@example.test",
            access_token="encrypted-access-2",
            refresh_token=None,
            expires_at=200,
            profile_json="{}",
        )
        assert updated.id == connection.id
        assert updated.refresh_token == "encrypted-refresh"

        bound = oauth.bind_to_user(
            provider="superjob",
            external_user_id="101",
            user_id=user.id,
        )
        assert bound.user_id == user.id
        assert bound.as_legacy_mapping()["name"] == "Super Job Updated"

        hh_connection = oauth.upsert(
            provider="headhunter",
            external_user_id="hh-101",
            first_name="Head",
            last_name="Hunter",
            email="hh@example.test",
            access_token="encrypted-hh-access",
            refresh_token="encrypted-hh-refresh",
            profile_json="{}",
        )
        assert hh_connection.as_legacy_mapping()["last_name"] == "Hunter"

        with runtime.session() as session:
            assert session.scalar(select(func.count(User.id))) == 1
            assert session.scalar(select(func.count(OAuthConnection.id))) == 2
            legacy = session.get(SuperJobAccount, 101)
            assert legacy is not None
            assert legacy.name == "Super Job Updated"
            assert legacy.access_token == "encrypted-access-2"
            assert legacy.refresh_token == "encrypted-refresh"
            legacy_hh = session.get(HeadHunterAccount, "hh-101")
            assert legacy_hh is not None
            assert legacy_hh.first_name == "Head"
            assert legacy_hh.access_token == "encrypted-hh-access"
    finally:
        runtime.dispose()


def test_sync_run_repository_persists_lifecycle(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        repository = SyncRunRepository(runtime)
        started = repository.start(
            source="trudvsem",
            trigger="test",
            target=300,
            details={"mode": "full"},
        )
        assert started.status == "running"

        finished = repository.finish(
            started.id,
            status="failed",
            processed=100,
            saved=24,
            cursor="100",
            error_type="TimeoutError",
            error_message="source timeout",
        )
        assert finished.status == "failed"
        assert finished.finished_at is not None
        latest = repository.latest("trudvsem")
        assert latest is not None
        assert latest.id == started.id
        assert latest.public_summary()["saved"] == 24

        with runtime.session() as session:
            assert session.scalar(select(func.count(SyncRun.id))) == 1
    finally:
        runtime.dispose()


def test_vacancy_store_creates_canonical_and_source_records(tmp_path):
    runtime = _runtime(tmp_path)
    store = VacancyStore(runtime)
    try:
        item = {
            "source": "trudvsem",
            "external_id": "domain-1",
            "title": "Python engineer",
            "company": "Example",
            "currency": "RUB",
            "published_at": "2026-08-04T07:00:00Z",
            "url": "https://example.test/domain-1",
        }
        assert store.upsert_many([item]) == 1
        assert store.upsert_many([{**item, "title": "Senior Python engineer"}]) == 1

        with runtime.session() as session:
            source_record = session.scalar(
                select(VacancySourceRecord).where(
                    VacancySourceRecord.source == "trudvsem",
                    VacancySourceRecord.external_id == "domain-1",
                )
            )
            assert source_record is not None
            canonical = session.get(Vacancy, source_record.vacancy_id)
            assert canonical is not None
            assert canonical.title == "Senior Python engineer"
            assert session.scalar(select(func.count(Vacancy.id))) == 1
            assert session.scalar(select(func.count(VacancySourceRecord.id))) == 1

            canonical_id = canonical.id
            source_record_id = source_record.id

        detached_source = store.repository.get_source("trudvsem", "domain-1")
        detached_vacancy = store.repository.get_canonical(canonical_id)
        assert detached_source is not None
        assert detached_source.title == "Senior Python engineer"
        assert detached_vacancy is not None
        assert detached_vacancy.id == canonical_id
        assert [item.id for item in store.repository.list_sources(canonical_id)] == [
            source_record_id
        ]

        with runtime.session() as session:
            session.execute(delete(Vacancy).where(Vacancy.id == canonical_id))
            session.commit()

        with runtime.session() as verification_session:
            assert verification_session.get(VacancySourceRecord, source_record_id) is None
    finally:
        runtime.dispose()


def test_user_delete_cascades_unified_oauth_and_keeps_rollback_mirror(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        users = UserRepository(runtime)
        oauth = OAuthConnectionRepository(runtime)
        user = users.create(email="cascade@example.test", status="active")
        connection = oauth.upsert(
            provider="superjob",
            external_user_id="202",
            display_name="Cascade Test",
            access_token="encrypted-access",
            refresh_token="encrypted-refresh",
            profile_json="{}",
            user_id=user.id,
        )

        with runtime.session() as session:
            session.execute(delete(User).where(User.id == user.id))
            session.commit()

        assert oauth.get("superjob", "202") is None
        with runtime.session() as session:
            assert session.get(OAuthConnection, connection.id) is None
            assert session.get(SuperJobAccount, 202) is not None
    finally:
        runtime.dispose()


def test_user_delete_cascades_first_party_sessions_and_tokens(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        auth = AuthRepository(runtime)
        user = auth.create_user(
            email="auth-cascade@example.test",
            normalized_email="auth-cascade@example.test",
            password_hash="aca_scrypt$1$32768$8$1$placeholder$placeholder",
            display_name=None,
            now=10,
        )
        assert user is not None
        auth.create_session(
            user_id=user.id,
            token_hash="a" * 64,
            expires_at=10_000,
            user_agent_hash=None,
            now=11,
        )
        auth.issue_token(
            user_id=user.id,
            purpose="verify_email",
            token_hash="b" * 64,
            expires_at=10_000,
            now=11,
        )

        with runtime.session() as session:
            session.execute(delete(User).where(User.id == user.id))
            session.commit()

        with runtime.session() as session:
            assert session.scalar(select(func.count(AuthSession.id))) == 0
            assert session.scalar(select(func.count(AuthToken.id))) == 0
    finally:
        runtime.dispose()
