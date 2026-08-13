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


def _insert_user(connection, *, user_id: str, email: str, now: int) -> None:
    connection.execute(
        text(
            """
            INSERT INTO users (
                id, email, normalized_email, display_name, status,
                email_verified_at, created_at, updated_at
            ) VALUES (
                :id, :email, :email, 'PROF-003 migration', 'active',
                :now, :now, :now
            )
            """
        ),
        {"id": user_id, "email": email, "now": now},
    )


def test_prof003_0012_creates_owner_drafts_versions_assets_and_export_metadata(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'prof003-migration.db').resolve().as_posix()}"
    upgrade_database(database_url, "20260812_0011")
    runtime = create_database(database_url)
    now = int(time.time())
    user_id = str(uuid.uuid4())
    draft_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    asset_id = str(uuid.uuid4())
    export_id = str(uuid.uuid4())
    try:
        with runtime.engine.begin() as connection:
            _insert_user(
                connection,
                user_id=user_id,
                email="prof003-migration@example.test",
                now=now,
            )
    finally:
        runtime.dispose()

    upgrade_database(database_url, "20260812_0012")
    runtime = create_database(database_url)
    try:
        inspector = inspect(runtime.engine)
        assert current_revision(runtime.engine) == "20260812_0012"
        assert CURRENT_REVISION == "20260812_0012"
        assert {
            "resume_drafts",
            "resume_versions",
            "resume_assets",
            "resume_exports",
        }.issubset(set(inspector.get_table_names()))

        version_uniques = {
            item.get("name")
            for item in inspector.get_unique_constraints("resume_versions")
        }
        asset_uniques = {
            item.get("name")
            for item in inspector.get_unique_constraints("resume_assets")
        }
        assert "uq_resume_versions_draft_version" in version_uniques
        assert "uq_resume_assets_draft_kind_sha256" in asset_uniques

        state = json.dumps(
            {
                "schemaVersion": 1,
                "index": 1,
                "answers": {"name": "Test User"},
                "messages": [],
                "photoAssetId": None,
                "universityLogoAssetId": None,
                "universityLogoFor": "",
                "universityResolvedName": "",
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        with runtime.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO resume_drafts (
                        id, user_id, schema_version, revision, title,
                        state_json, content_hash, completion_percent,
                        profile_version, created_at, updated_at
                    ) VALUES (
                        :id, :user_id, 1, 1, 'Test resume',
                        :state, :hash, 13, NULL, :now, :now
                    )
                    """
                ),
                {
                    "id": draft_id,
                    "user_id": user_id,
                    "state": state,
                    "hash": "a" * 64,
                    "now": now,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO resume_versions (
                        id, draft_id, schema_version, version, draft_revision,
                        snapshot_json, content_hash, reason,
                        restored_from_version, created_at
                    ) VALUES (
                        :id, :draft_id, 1, 1, 1, :state, :hash,
                        'checkpoint', NULL, :now
                    )
                    """
                ),
                {
                    "id": version_id,
                    "draft_id": draft_id,
                    "state": state,
                    "hash": "a" * 64,
                    "now": now,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO resume_assets (
                        id, draft_id, user_id, kind, content_type,
                        byte_size, sha256, data, created_at
                    ) VALUES (
                        :id, :draft_id, :user_id, 'photo', 'image/png',
                        8, :hash, :data, :now
                    )
                    """
                ),
                {
                    "id": asset_id,
                    "draft_id": draft_id,
                    "user_id": user_id,
                    "hash": "b" * 64,
                    "data": b"png-data",
                    "now": now,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO resume_exports (
                        id, draft_id, version_id, version, page_count,
                        byte_size, pdf_sha256, file_name, created_at
                    ) VALUES (
                        :id, :draft_id, :version_id, 1, 1,
                        1024, :hash, 'resume.pdf', :now
                    )
                    """
                ),
                {
                    "id": export_id,
                    "draft_id": draft_id,
                    "version_id": version_id,
                    "hash": "c" * 64,
                    "now": now,
                },
            )

        with runtime.engine.begin() as connection:
            connection.execute(
                text("DELETE FROM users WHERE id=:id"),
                {"id": user_id},
            )
            assert connection.scalar(text("SELECT COUNT(*) FROM resume_drafts")) == 0
            assert connection.scalar(text("SELECT COUNT(*) FROM resume_versions")) == 0
            assert connection.scalar(text("SELECT COUNT(*) FROM resume_assets")) == 0
            assert connection.scalar(text("SELECT COUNT(*) FROM resume_exports")) == 0
    finally:
        runtime.dispose()

    downgrade_database(database_url, "20260812_0011")
    runtime = create_database(database_url)
    try:
        inspector = inspect(runtime.engine)
        assert current_revision(runtime.engine) == "20260812_0011"
        for table_name in (
            "resume_drafts",
            "resume_versions",
            "resume_assets",
            "resume_exports",
        ):
            assert table_name not in inspector.get_table_names()
        assert "career_profile_versions" in inspector.get_table_names()
    finally:
        runtime.dispose()

    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == CURRENT_REVISION
    finally:
        runtime.dispose()
