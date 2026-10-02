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


def test_priv001_0013_adds_identifier_free_privacy_audit(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'priv001-migration.db').resolve().as_posix()}"
    upgrade_database(database_url, "20260812_0012")
    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == "20260812_0012"
        assert "privacy_audit_events" not in inspect(runtime.engine).get_table_names()
    finally:
        runtime.dispose()

    upgrade_database(database_url, "20260813_0013")
    runtime = create_database(database_url)
    try:
        inspector = inspect(runtime.engine)
        assert current_revision(runtime.engine) == "20260813_0013"
        assert CURRENT_REVISION == "20261002_0023"
        assert "privacy_audit_events" in inspector.get_table_names()
        resume_asset_indexes = {item["name"] for item in inspector.get_indexes("resume_assets")}
        assert "idx_resume_assets_created" in resume_asset_indexes
        columns = {column["name"] for column in inspector.get_columns("privacy_audit_events")}
        assert columns == {"id", "event_type", "counts_json", "created_at"}
        assert "user_id" not in columns
        assert "email" not in columns
        assert "content" not in columns

        with runtime.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO privacy_audit_events (id, event_type, counts_json, created_at)
                    VALUES (:id, 'account_deleted', :counts, :now)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "counts": json.dumps({"resume_drafts": 2}),
                    "now": int(time.time()),
                },
            )
            assert connection.scalar(text("SELECT COUNT(*) FROM privacy_audit_events")) == 1
    finally:
        runtime.dispose()

    downgrade_database(database_url, "20260812_0012")
    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == "20260812_0012"
        inspector = inspect(runtime.engine)
        assert "privacy_audit_events" not in inspector.get_table_names()
        assert "resume_drafts" in inspector.get_table_names()
        assert "idx_resume_assets_created" not in {item["name"] for item in inspector.get_indexes("resume_assets")}
    finally:
        runtime.dispose()

    upgrade_database(database_url)
    runtime = create_database(database_url)
    try:
        assert current_revision(runtime.engine) == CURRENT_REVISION
    finally:
        runtime.dispose()
