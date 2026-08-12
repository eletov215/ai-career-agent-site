from __future__ import annotations

import json
import time
import uuid

from sqlalchemy import inspect, text

from database import (
    CURRENT_REVISION,
    create_database,
    current_revision,
    downgrade_database,
    upgrade_database,
)


def test_prof002_0011_adds_confirmed_import_provenance_without_rewriting_history(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'prof002-migration.db').resolve().as_posix()}"
    upgrade_database(database_url, "20260811_0010")
    runtime = create_database(database_url)
    now = int(time.time())
    user_id = str(uuid.uuid4())
    profile_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    try:
        with runtime.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO users (
                        id, email, normalized_email, display_name, status,
                        email_verified_at, created_at, updated_at
                    ) VALUES (
                        :id, :email, :normalized_email, :display_name, :status,
                        :verified, :created, :updated
                    )
                    """
                ),
                {
                    "id": user_id,
                    "email": "prof002-migration@example.test",
                    "normalized_email": "prof002-migration@example.test",
                    "display_name": "PROF-002 migration",
                    "status": "active",
                    "verified": now,
                    "created": now,
                    "updated": now,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO career_profiles (
                        id, user_id, schema_version, version, headline, summary,
                        contacts_json, goals_json, geography_json, salary_json,
                        skills_json, employment_json, achievements_json,
                        education_json, languages_json, content_hash,
                        completion_percent, confirmed_at, created_at, updated_at
                    ) VALUES (
                        :id, :user_id, 1, 1, 'Manual profile', NULL,
                        '{}', '{}', '{}', '{}', '[]', '[]', '[]', '[]', '[]',
                        :content_hash, 10, :now, :now, :now
                    )
                    """
                ),
                {
                    "id": profile_id,
                    "user_id": user_id,
                    "content_hash": "a" * 64,
                    "now": now,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO career_profile_versions (
                        id, profile_id, schema_version, version, snapshot_json,
                        content_hash, changed_sections_json, created_at
                    ) VALUES (
                        :id, :profile_id, 1, 1, :snapshot, :content_hash,
                        '["core"]', :now
                    )
                    """
                ),
                {
                    "id": version_id,
                    "profile_id": profile_id,
                    "snapshot": json.dumps({"schema_version": 1, "headline": "Manual profile"}),
                    "content_hash": "a" * 64,
                    "now": now,
                },
            )
    finally:
        runtime.dispose()

    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        inspector = inspect(runtime.engine)
        assert current_revision(runtime.engine) == CURRENT_REVISION == "20260812_0011"
        columns = {item["name"] for item in inspector.get_columns("career_profile_versions")}
        assert {"source_kind", "provenance_json"}.issubset(columns)
        checks = {
            item.get("name")
            for item in inspector.get_check_constraints("career_profile_versions")
        }
        assert "ck_career_profile_versions_source_kind" in checks
        with runtime.engine.connect() as connection:
            existing = connection.execute(
                text(
                    "SELECT source_kind, provenance_json FROM career_profile_versions WHERE id=:id"
                ),
                {"id": version_id},
            ).one()
            assert existing.source_kind == "manual"
            assert json.loads(existing.provenance_json) == {}

            connection.execute(
                text(
                    """
                    INSERT INTO career_profile_versions (
                        id, profile_id, schema_version, version, snapshot_json,
                        content_hash, changed_sections_json, source_kind,
                        provenance_json, created_at
                    ) VALUES (
                        :id, :profile_id, 1, 2, '{}', :content_hash, '["skills"]',
                        'resume_import', :provenance, :now
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "profile_id": profile_id,
                    "content_hash": "b" * 64,
                    "provenance": json.dumps(
                        {
                            "extractor_version": "deterministic-text-v1",
                            "page_count": 2,
                        }
                    ),
                    "now": now + 1,
                },
            )
            connection.commit()
    finally:
        runtime.dispose()

    downgrade_database(database_url, "20260811_0010")
    runtime = create_database(database_url)
    try:
        inspector = inspect(runtime.engine)
        assert current_revision(runtime.engine) == "20260811_0010"
        columns = {item["name"] for item in inspector.get_columns("career_profile_versions")}
        assert "source_kind" not in columns
        assert "provenance_json" not in columns
        assert "career_profiles" in inspector.get_table_names()
    finally:
        runtime.dispose()

    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == CURRENT_REVISION
    finally:
        runtime.dispose()
