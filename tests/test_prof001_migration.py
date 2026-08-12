from __future__ import annotations

import json
import time
import uuid

from sqlalchemy import inspect, select

from database import (
    CURRENT_REVISION,
    create_database,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from models import CareerProfile, CareerProfileVersion, User


def _active_user(email: str) -> User:
    now = int(time.time())
    return User(
        id=str(uuid.uuid4()),
        email=email,
        normalized_email=email.casefold(),
        display_name="Profile Migration",
        status="active",
        email_verified_at=now,
        password_hash=None,
        password_changed_at=None,
        last_login_at=None,
        created_at=now,
        updated_at=now,
    )


def test_prof001_0010_migration_creates_owner_profile_and_version_tables(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'prof001-migration.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        inspector = inspect(runtime.engine)
        assert current_revision(runtime.engine) == "20260811_0010"
        assert {"career_profiles", "career_profile_versions"}.issubset(
            set(inspector.get_table_names())
        )
        profile_constraints = {
            item.get("name")
            for item in inspector.get_unique_constraints("career_profiles")
        }
        version_constraints = {
            item.get("name")
            for item in inspector.get_unique_constraints("career_profile_versions")
        }
        assert "uq_career_profiles_user_id" in profile_constraints
        assert "uq_career_profile_versions_profile_version" in version_constraints

        now = int(time.time())
        with runtime.session() as session:
            user = _active_user("profile-migration@example.test")
            profile = CareerProfile(
                id=str(uuid.uuid4()),
                user_id=user.id,
                schema_version=1,
                version=1,
                headline="Data analyst",
                summary=None,
                contacts_json="{}",
                goals_json="{}",
                geography_json="{}",
                salary_json="{}",
                skills_json="[]",
                employment_json="[]",
                achievements_json="[]",
                education_json="[]",
                languages_json="[]",
                content_hash="a" * 64,
                completion_percent=10,
                confirmed_at=now,
                created_at=now,
                updated_at=now,
            )
            version = CareerProfileVersion(
                id=str(uuid.uuid4()),
                profile_id=profile.id,
                schema_version=1,
                version=1,
                snapshot_json=json.dumps({"headline": "Data analyst"}),
                content_hash="a" * 64,
                changed_sections_json='["core"]',
                created_at=now,
            )
            session.add_all([user, profile, version])
            session.commit()
            user_id = user.id

        with runtime.session() as session:
            assert session.scalar(
                select(CareerProfile).where(CareerProfile.user_id == user_id)
            ) is not None
            user = session.get(User, user_id)
            session.delete(user)
            session.commit()

        with runtime.session() as session:
            assert session.scalar(select(CareerProfile)) is None
            assert session.scalar(select(CareerProfileVersion)) is None
    finally:
        runtime.dispose()

    downgrade_database(database_url, "20260811_0009")
    runtime = create_database(database_url)
    try:
        inspector = inspect(runtime.engine)
        assert current_revision(runtime.engine) == "20260811_0009"
        assert "career_profiles" not in inspector.get_table_names()
        assert "career_profile_versions" not in inspector.get_table_names()
        assert "users" in inspector.get_table_names()
    finally:
        runtime.dispose()

    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == CURRENT_REVISION
    finally:
        runtime.dispose()
