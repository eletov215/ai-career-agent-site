from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import delete, select

from database import INITIAL_REVISION, create_database, current_revision, upgrade_database
from models import HeadHunterAccount, SuperJobAccount, Vacancy
from services.vacancy_store import VacancyStore


@pytest.mark.skipif(
    not os.environ.get("POSTGRES_TEST_URL"),
    reason="POSTGRES_TEST_URL is provided by the GitHub Actions PostgreSQL service",
)
def test_postgresql_migration_and_persistence_round_trip():
    """Exercise the real psycopg/PostgreSQL path used by production."""

    database_url = os.environ["POSTGRES_TEST_URL"]
    upgrade_database(database_url)
    runtime = create_database(database_url)
    suffix = uuid.uuid4().hex
    sj_user_id = int(suffix[:12], 16)
    hh_user_id = f"hh-{suffix}"
    external_id = f"vacancy-{suffix}"

    try:
        assert runtime.backend == "postgresql"
        assert runtime.persistent is True
        assert current_revision(runtime.engine) == INITIAL_REVISION

        with runtime.session() as session:
            session.add(
                SuperJobAccount(
                    user_id=sj_user_id,
                    name="CI SuperJob",
                    email="sj-ci@example.test",
                    access_token="encrypted-ci-token",
                    refresh_token=None,
                    expires_at=None,
                    profile_json="{}",
                    updated_at=1,
                )
            )
            session.add(
                HeadHunterAccount(
                    user_id=hh_user_id,
                    first_name="CI",
                    last_name="HeadHunter",
                    email="hh-ci@example.test",
                    access_token="encrypted-ci-token",
                    refresh_token=None,
                    expires_at=None,
                    profile_json="{}",
                    updated_at=1,
                )
            )
            session.commit()

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
                    "url": "https://example.test/postgresql-ci",
                }
            ]
        ) == 1

        runtime.dispose()
        runtime = create_database(database_url)

        with runtime.session() as session:
            assert session.get(SuperJobAccount, sj_user_id) is not None
            assert session.get(HeadHunterAccount, hh_user_id) is not None
            vacancy = session.scalar(
                select(Vacancy).where(
                    Vacancy.source == "ci-postgresql",
                    Vacancy.external_id == external_id,
                )
            )
            assert vacancy is not None
            assert vacancy.title == "PostgreSQL integration vacancy"

            session.execute(
                delete(Vacancy).where(
                    Vacancy.source == "ci-postgresql",
                    Vacancy.external_id == external_id,
                )
            )
            session.execute(
                delete(SuperJobAccount).where(SuperJobAccount.user_id == sj_user_id)
            )
            session.execute(
                delete(HeadHunterAccount).where(HeadHunterAccount.user_id == hh_user_id)
            )
            session.commit()
    finally:
        runtime.dispose()
