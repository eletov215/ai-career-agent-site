from __future__ import annotations

import time
import uuid

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from database import (
    CURRENT_REVISION,
    create_database,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from models import OAuthConnection, User


def _user(email: str) -> User:
    now = int(time.time())
    return User(
        id=str(uuid.uuid4()),
        email=email,
        normalized_email=email.casefold(),
        display_name=None,
        status="active",
        email_verified_at=now,
        password_hash=None,
        password_changed_at=None,
        last_login_at=None,
        created_at=now,
        updated_at=now,
    )


def _connection(*, user_id: str | None, provider: str, external_id: str) -> OAuthConnection:
    now = int(time.time())
    return OAuthConnection(
        id=str(uuid.uuid4()),
        user_id=user_id,
        provider=provider,
        external_user_id=external_id,
        display_name=None,
        first_name=None,
        last_name=None,
        email=None,
        access_token="encrypted-access",
        refresh_token="encrypted-refresh",
        expires_at=None,
        profile_json="{}",
        created_at=now,
        updated_at=now,
    )


def _owned_provider_constraint_names(engine) -> set[str]:
    inspector = inspect(engine)
    names = {
        item.get("name")
        for item in inspector.get_unique_constraints("oauth_connections")
        if item.get("name")
    }
    names.update(
        item.get("name")
        for item in inspector.get_indexes("oauth_connections")
        if item.get("name") and item.get("unique")
    )
    return names


def test_auth002_0009_migration_enforces_one_provider_slot_per_user(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'auth002-migration.db').resolve().as_posix()}"
    upgrade_database(database_url, "20260811_0009")
    runtime = create_database(database_url)
    try:
        assert "uq_oauth_connections_user_provider" in _owned_provider_constraint_names(
            runtime.engine
        )
        assert current_revision(runtime.engine) == "20260811_0009"

        with runtime.session() as session:
            first = _user("auth002-first@example.test")
            second = _user("auth002-second@example.test")
            session.add_all([first, second])
            session.flush()
            first_id = first.id
            second_id = second.id
            session.add_all(
                [
                    _connection(
                        user_id=first_id,
                        provider="headhunter",
                        external_id="hh-one",
                    ),
                    _connection(
                        user_id=second_id,
                        provider="headhunter",
                        external_id="hh-two",
                    ),
                    # NULL ownership stays intentionally claimable. Both SQLite
                    # and PostgreSQL allow multiple NULL values here.
                    _connection(
                        user_id=None,
                        provider="superjob",
                        external_id="sj-unbound-one",
                    ),
                    _connection(
                        user_id=None,
                        provider="superjob",
                        external_id="sj-unbound-two",
                    ),
                ]
            )
            session.commit()

        with runtime.session() as session:
            session.add(
                _connection(
                    user_id=first_id,
                    provider="headhunter",
                    external_id="hh-conflict",
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()
    finally:
        runtime.dispose()

    downgrade_database(database_url, "20260810_0008")
    runtime = create_database(database_url)
    try:
        assert "uq_oauth_connections_user_provider" not in _owned_provider_constraint_names(
            runtime.engine
        )
        assert current_revision(runtime.engine) == "20260810_0008"
    finally:
        runtime.dispose()

    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == CURRENT_REVISION
    finally:
        runtime.dispose()


def test_auth002_migration_fails_closed_on_ambiguous_existing_ownership(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'auth002-duplicates.db').resolve().as_posix()}"
    upgrade_database(database_url, "20260810_0008")
    runtime = create_database(database_url)
    try:
        with runtime.session() as session:
            owner = _user("ambiguous-owner@example.test")
            session.add(owner)
            session.flush()
            session.add_all(
                [
                    _connection(
                        user_id=owner.id,
                        provider="headhunter",
                        external_id="hh-ambiguous-one",
                    ),
                    _connection(
                        user_id=owner.id,
                        provider="headhunter",
                        external_id="hh-ambiguous-two",
                    ),
                ]
            )
            session.commit()
    finally:
        runtime.dispose()

    with pytest.raises(
        RuntimeError,
        match="duplicate owned provider connections|resolving duplicate owned provider",
    ):
        upgrade_database(database_url, "20260811_0009")

    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == "20260810_0008"
    finally:
        runtime.dispose()
