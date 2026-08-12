from __future__ import annotations

import json
import os
import uuid

import pytest
from sqlalchemy import func, inspect, select, text

from database import (
    CURRENT_REVISION,
    create_database,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from models import (
    CareerProfile,
    CareerProfileVersion,
    HeadHunterAccount,
    OAuthConnection,
    SuperJobAccount,
    SyncCheckpoint,
    SyncRun,
    User,
    Vacancy,
    VacancySourceRecord,
)
from repositories import (
    AuthRepository,
    CareerProfileRepository,
    OAuthConnectionRepository,
    SearchSnapshotRepository,
    SyncCheckpointRepository,
    SyncRunRepository,
    UserRepository,
)
from services.oauth_identity import (
    OAuthIdentityOwnedByAnotherUser,
    OAuthIdentityService,
    OAuthProviderSlotOccupied,
)
from services.passwords import hash_password
from services.profile import CareerProfileService
from services.vacancy_store import VacancyStore


@pytest.mark.skipif(
    not os.environ.get("POSTGRES_TEST_URL"),
    reason="POSTGRES_TEST_URL is provided by the GitHub Actions PostgreSQL service",
)
def test_postgresql_migration_and_persistence_round_trip():
    """Exercise legacy migration, repositories, sequences, and reconnect."""

    database_url = os.environ["POSTGRES_TEST_URL"]
    suffix = uuid.uuid4().hex
    legacy_vacancy_id = 0
    legacy_superjob_id = 0
    legacy_hh_id = f"legacy-hh-{suffix}"
    legacy_external_id = f"legacy-vacancy-{suffix}"

    # CI first upgrades a clean PostgreSQL database.  Move it back to the
    # production pre-DATA-002 revision, seed real legacy rows, then migrate
    # forward.  This is the path the current Render database will execute.
    upgrade_database(database_url)
    downgrade_database(database_url, "20260804_0001")
    legacy_runtime = create_database(database_url)
    try:
        payload = {
            "source": "trudvsem",
            "external_id": legacy_external_id,
            "title": "Legacy PostgreSQL vacancy",
            "company": "AI Career Agent migration test",
            "experience": "Без опыта",
            "published_at": "2026-08-04T07:00:00Z",
        }
        with legacy_runtime.engine.begin() as connection:
            legacy_vacancy_id = int(
                connection.scalar(text("SELECT COALESCE(MAX(id), 0) FROM vacancies")) or 0
            ) + 100
            legacy_superjob_id = int(
                connection.scalar(text("SELECT COALESCE(MAX(user_id), 0) FROM accounts")) or 0
            ) + 100
            connection.execute(
                text(
                    """
                    INSERT INTO accounts (
                        user_id, name, email, access_token, refresh_token,
                        expires_at, profile_json, updated_at
                    ) VALUES (
                        :user_id, :name, :email, :access_token, :refresh_token,
                        :expires_at, :profile_json, :updated_at
                    )
                    """
                ),
                {
                    "user_id": legacy_superjob_id,
                    "name": "Legacy SuperJob",
                    "email": "legacy-sj@example.test",
                    "access_token": "encrypted-legacy-sj-access",
                    "refresh_token": "encrypted-legacy-sj-refresh",
                    "expires_at": 1_900_000_000,
                    "profile_json": "{}",
                    "updated_at": 1_785_853_489,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO hh_accounts (
                        user_id, first_name, last_name, email, access_token,
                        refresh_token, expires_at, profile_json, updated_at
                    ) VALUES (
                        :user_id, :first_name, :last_name, :email, :access_token,
                        :refresh_token, :expires_at, :profile_json, :updated_at
                    )
                    """
                ),
                {
                    "user_id": legacy_hh_id,
                    "first_name": "Legacy",
                    "last_name": "HeadHunter",
                    "email": "legacy-hh@example.test",
                    "access_token": "encrypted-legacy-hh-access",
                    "refresh_token": "encrypted-legacy-hh-refresh",
                    "expires_at": 1_900_000_000,
                    "profile_json": "{}",
                    "updated_at": 1_785_853_489,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO vacancies (
                        id, source, external_id, title, company, salary_from,
                        salary_to, currency, location, remote, schedule,
                        employment, experience, description, requirements,
                        published_at, url, search_text, raw_json, fetched_at,
                        updated_at
                    ) VALUES (
                        :id, :source, :external_id, :title, :company, NULL,
                        NULL, 'RUB', 'Oregon', false, NULL, NULL, :experience,
                        NULL, NULL, :published_at, :url, :search_text, :raw_json,
                        :fetched_at, :updated_at
                    )
                    """
                ),
                {
                    "id": legacy_vacancy_id,
                    "source": "trudvsem",
                    "external_id": legacy_external_id,
                    "title": payload["title"],
                    "company": payload["company"],
                    "experience": payload["experience"],
                    "published_at": payload["published_at"],
                    "url": f"https://example.test/{legacy_external_id}",
                    "search_text": "legacy postgresql vacancy",
                    "raw_json": json.dumps(payload),
                    "fetched_at": 1_785_853_489,
                    "updated_at": 1_785_853_489,
                },
            )
    finally:
        legacy_runtime.dispose()

    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        assert runtime.backend == "postgresql"
        assert runtime.persistent is True
        assert current_revision(runtime.engine) == CURRENT_REVISION
        constraint_names = {
            item.get("name")
            for item in inspect(runtime.engine).get_unique_constraints("oauth_connections")
        }
        assert "uq_oauth_connections_user_provider" in constraint_names

        oauth = OAuthConnectionRepository(runtime)
        oauth_identities = OAuthIdentityService(oauth)
        migrated_sj = oauth.get("superjob", str(legacy_superjob_id))
        migrated_hh = oauth.get("headhunter", legacy_hh_id)
        assert migrated_sj is not None
        assert migrated_sj.refresh_token == "encrypted-legacy-sj-refresh"
        assert migrated_hh is not None
        assert migrated_hh.last_name == "HeadHunter"

        with runtime.session() as session:
            migrated_source = session.scalar(
                select(VacancySourceRecord).where(
                    VacancySourceRecord.source == "trudvsem",
                    VacancySourceRecord.external_id == legacy_external_id,
                )
            )
            assert migrated_source is not None
            assert migrated_source.id == legacy_vacancy_id
            migrated_canonical = session.get(Vacancy, migrated_source.vacancy_id)
            assert migrated_canonical is not None
            assert migrated_canonical.title == "Legacy PostgreSQL vacancy"
            max_source_id = int(
                session.scalar(select(func.max(VacancySourceRecord.id))) or 0
            )

        users = UserRepository(runtime)
        auth = AuthRepository(runtime)
        auth_email = f"auth-{suffix}@example.test"
        auth_user = auth.create_user(
            email=auth_email,
            normalized_email=auth_email,
            password_hash=hash_password("PostgreSQL auth password 42!"),
            display_name="CI Auth User",
            now=10_000,
        )
        assert auth_user is not None
        auth.issue_token(
            user_id=auth_user.id,
            purpose="verify_email",
            token_hash="b" * 64,
            expires_at=20_000,
            now=10_001,
        )
        verified_auth_user = auth.verify_email_with_token(
            token_hash="b" * 64,
            purpose="verify_email",
            now=10_002,
        )
        assert verified_auth_user is not None
        assert verified_auth_user.status == "active"
        auth_session = auth.create_session(
            user_id=auth_user.id,
            token_hash="c" * 64,
            expires_at=20_000,
            user_agent_hash="d" * 64,
            now=10_003,
        )

        sync_runs = SyncRunRepository(runtime)
        sync_checkpoints = SyncCheckpointRepository(runtime)
        user_email = f"ci-{suffix}@example.test"
        user = users.create(email=user_email, display_name="CI User", status="active")

        numeric_external_id = str(20_000_000 + int(suffix[14:21], 16))
        connection_result = oauth_identities.connect(
            provider="superjob",
            external_user_id=numeric_external_id,
            display_name="CI SuperJob",
            email=user_email,
            access_token="encrypted-ci-token",
            refresh_token="encrypted-ci-refresh",
            expires_at=None,
            profile_json="{}",
            user_id=user.id,
        )
        connection = connection_result.connection
        assert connection_result.outcome == "created"
        assert connection.user_id == user.id

        second_user = users.create(
            email=f"ci-second-{suffix}@example.test",
            display_name="CI Second User",
            status="active",
        )
        with pytest.raises(OAuthIdentityOwnedByAnotherUser):
            oauth_identities.connect(
                provider="superjob",
                external_user_id=numeric_external_id,
                access_token="must-not-overwrite",
                profile_json="{}",
                user_id=second_user.id,
            )
        with pytest.raises(OAuthProviderSlotOccupied):
            oauth_identities.connect(
                provider="superjob",
                external_user_id=str(int(numeric_external_id) + 1),
                access_token="must-not-create",
                profile_json="{}",
                user_id=user.id,
            )

        profiles = CareerProfileService(CareerProfileRepository(runtime))
        profile_result = profiles.save(
            user_id=user.id,
            expected_version=0,
            payload={
                "headline": "PostgreSQL profile owner",
                "goals": {"target_roles": ["Platform lead"]},
                "skills": [{"name": "PostgreSQL", "level": "advanced"}],
            },
            now=10_010,
        )
        assert profile_result.profile.version == 1
        assert profiles.get(second_user.id).exists is False
        assert profiles.get_version(user_id=second_user.id, version=1) is None

        sync_run = sync_runs.start(
            source="ci-postgresql",
            trigger="integration-test",
            target=1,
        )
        sync_runs.finish(
            sync_run.id,
            status="succeeded",
            processed=1,
            saved=1,
            cursor="1",
        )
        checkpoint = sync_checkpoints.complete_success(
            "ci-postgresql",
            run_id=sync_run.id,
            watermark_at=1_785_853_489,
            cleanup_at=1_785_853_490,
        )
        assert checkpoint.watermark_at == 1_785_853_489

        external_id = f"vacancy-{suffix}"
        store = VacancyStore(runtime)
        assert store.upsert_many(
            [
                {
                    "source": "ci-postgresql",
                    "external_id": external_id,
                    "title": "PostgreSQL integration vacancy",
                    "company": "AI Career Agent CI",
                    "currency": "RUB",
                    "published_at": "2026-08-04T07:00:00Z",
                    "source_modified_at": "2026-08-07T12:00:00Z",
                    "source_status": "active",
                    "url": "https://example.test/postgresql-ci",
                }
            ],
            run_id=sync_run.id,
            seen_at=1_785_853_500,
        ) == 1

        inserted_source = store.repository.get_source("ci-postgresql", external_id)
        assert inserted_source is not None
        assert inserted_source.id > max_source_id
        assert inserted_source.source_modified_at == "2026-08-07T12:00:00Z"
        assert inserted_source.last_seen_run_id == sync_run.id
        assert inserted_source.source_status == "active"
        inserted_canonical = store.repository.get_canonical(inserted_source.vacancy_id)
        assert inserted_canonical is not None
        assert inserted_canonical.title == "PostgreSQL integration vacancy"

        with runtime.session() as session:
            legacy_mirror = session.get(SuperJobAccount, int(numeric_external_id))
            assert legacy_mirror is not None
            assert legacy_mirror.access_token == "encrypted-ci-token"

        search_snapshots = SearchSnapshotRepository(runtime)
        search_snapshot = search_snapshots.create(
            query_fingerprint="a" * 64,
            selected_sources=["hh", "superjob"],
            sort_code="date",
            page_size=20,
            ttl_seconds=900,
        )
        assert search_snapshots.get(search_snapshot.id) is not None

        # Dispose/recreate the engine to prove data is committed, detached from
        # ORM sessions, and accessible through the repository contracts.
        runtime.dispose()
        runtime = create_database(database_url)

        assert UserRepository(runtime).find_by_email(user_email) is not None
        persisted_auth = AuthRepository(runtime)
        persisted_auth_user = persisted_auth.find_user_by_email(auth_email)
        assert persisted_auth_user is not None
        assert persisted_auth_user.status == "active"
        assert persisted_auth.get_active_session("c" * 64, now=10_004) is not None
        assert any(
            item.id == auth_session.id
            for item in persisted_auth.list_active_sessions(auth_user.id, now=10_004)
        )
        persisted_oauth = OAuthConnectionRepository(runtime)
        persisted_identities = OAuthIdentityService(persisted_oauth)
        persisted_connection = persisted_identities.get(
            user_id=user.id,
            provider="superjob",
        )
        assert persisted_connection is not None
        assert persisted_connection.external_user_id == numeric_external_id
        assert persisted_connection.user_id == user.id
        persisted_profiles = CareerProfileService(CareerProfileRepository(runtime))
        persisted_profile = persisted_profiles.get(user.id)
        assert persisted_profile.exists is True
        assert persisted_profile.headline == "PostgreSQL profile owner"
        assert persisted_profile.skills[0]["name"] == "PostgreSQL"
        assert len(persisted_profiles.list_versions(user_id=user.id)) == 1
        latest_run = SyncRunRepository(runtime).latest("ci-postgresql")
        assert latest_run is not None
        assert latest_run.status == "succeeded"
        persisted_checkpoint = SyncCheckpointRepository(runtime).get("ci-postgresql")
        assert persisted_checkpoint is not None
        assert persisted_checkpoint.watermark_at == 1_785_853_489
        assert persisted_checkpoint.last_cleanup_at == 1_785_853_490
        persisted_source = VacancyStore(runtime).repository.get_source(
            "ci-postgresql", external_id
        )
        assert persisted_source is not None
        assert persisted_source.vacancy_id == inserted_source.vacancy_id
        persisted_snapshot = SearchSnapshotRepository(runtime).get(search_snapshot.id)
        assert persisted_snapshot is not None
        assert persisted_snapshot.query_fingerprint == "a" * 64

        with runtime.session() as session:
            assert session.scalar(
                select(OAuthConnection).where(
                    OAuthConnection.id == connection.id
                )
            ) is not None
            assert session.get(User, user.id) is not None
            assert session.get(SyncRun, sync_run.id) is not None
            assert session.get(SyncCheckpoint, "ci-postgresql") is not None
            assert session.get(HeadHunterAccount, legacy_hh_id) is not None
            assert session.scalar(
                select(CareerProfile).where(CareerProfile.user_id == user.id)
            ) is not None
            assert session.scalar(select(CareerProfileVersion)) is not None

        removed = persisted_identities.disconnect(
            user_id=user.id,
            provider="superjob",
        )
        assert removed is not None
        assert persisted_identities.get(user_id=user.id, provider="superjob") is None
        with runtime.session() as session:
            assert session.get(SuperJobAccount, int(numeric_external_id)) is None
    finally:
        runtime.dispose()
