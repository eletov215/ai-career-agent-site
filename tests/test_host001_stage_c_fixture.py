from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from database import CURRENT_REVISION, create_database, upgrade_database
from models import User
from scripts.host001_stage_c_fixture import (
    StageCFixtureError,
    seed_fixture,
    verify_fixture,
)


def _runtime(tmp_path):
    url = f"sqlite:///{tmp_path / 'stage-c-fixture.sqlite3'}"
    upgrade_database(url)
    return create_database(url)


def test_stage_c_fixture_is_deterministic_and_idempotent(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        seed_fixture(runtime)
        first = verify_fixture(runtime)
        seed_fixture(runtime)
        second = verify_fixture(runtime)

        assert first["ok"] is True
        assert first["database_revision"] == CURRENT_REVISION
        assert first["fixture_digest"] == second["fixture_digest"]
        assert first["asset_sha256"] == second["asset_sha256"]
        assert first["schema_digest"] == second["schema_digest"]
        assert first["sequence_count"] == 0

        with runtime.session() as session:
            assert int(session.scalar(select(func.count()).select_from(User)) or 0) == 1
    finally:
        runtime.dispose()


def test_stage_c_fixture_refuses_a_nonempty_unrelated_database(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        with runtime.session() as session:
            session.add(
                User(
                    id="11111111-1111-4111-8111-111111111111",
                    email="existing@example.invalid",
                    normalized_email="existing@example.invalid",
                    display_name="Existing Synthetic",
                    status="active",
                    email_verified_at=1_760_000_000,
                    password_hash=None,
                    password_changed_at=None,
                    last_login_at=None,
                    created_at=1_760_000_000,
                    updated_at=1_760_000_000,
                )
            )
            session.commit()

        with pytest.raises(StageCFixtureError, match="already has users"):
            seed_fixture(runtime)
    finally:
        runtime.dispose()
