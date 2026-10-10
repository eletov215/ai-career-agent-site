"""LEGAL-001 disposable PostgreSQL verification.

The tests create and drop isolated databases on the PostgreSQL server named by
POSTGRES_TEST_URL. They never use production credentials or provider transport.
"""
from __future__ import annotations

import base64
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from scripts.ai004_m04b_successor import expected_schema_head
from database import (
    CURRENT_REVISION,
    create_database,
    current_revision,
    downgrade_database,
    upgrade_database,
)
from operations.backup import backup_database, restore_database, validate_backup
from repositories.consent import ConsentRepository
from services.consent import ConsentService, ConsentStaleStateError


PG_URL = os.environ.get("POSTGRES_TEST_URL", "").strip()
pytestmark = pytest.mark.skipif(
    not PG_URL,
    reason="Disposable PostgreSQL required; skipped != passed for LEGAL-001 T-05/T-06.",
)
TEST_KEY = base64.urlsafe_b64encode(b"L" * 32).decode("ascii")


def _database_url(name: str) -> str:
    return make_url(PG_URL).set(database=name).render_as_string(hide_password=False)


def _admin_engine():
    url = make_url(PG_URL).set(database="postgres")
    return create_engine(url, future=True, isolation_level="AUTOCOMMIT", hide_parameters=True)


def _create_db(prefix: str) -> tuple[str, str]:
    name = f"{prefix}_{uuid4().hex[:12]}"
    engine = _admin_engine()
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql(f'CREATE DATABASE "{name}"')
    finally:
        engine.dispose()
    return name, _database_url(name)


def _drop_db(name: str) -> None:
    engine = _admin_engine()
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname=:name AND pid<>pg_backend_pid()"
                ),
                {"name": name},
            )
            conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}"')
    finally:
        engine.dispose()


def _insert_owner_and_vacancy(runtime, user_id: str, vacancy_id: str, stamp: int) -> None:
    with runtime.engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users "
                "(id,status,email_verified_at,created_at,updated_at) "
                "VALUES (:id,'active',:stamp,:stamp,:stamp)"
            ),
            {"id": user_id, "stamp": stamp},
        )
        conn.execute(
            text(
                "INSERT INTO saved_vacancies "
                "(id,user_id,snapshot_json,snapshot_hash,snapshot_version,title,company,"
                "location,search_text,note,revision,created_at,updated_at) "
                "VALUES (:id,:user_id,'{}',:hash,'job001-v1',:title,'Synthetic Co',"
                "'Test','synthetic role','',1,:stamp,:stamp)"
            ),
            {
                "id": vacancy_id,
                "user_id": user_id,
                "hash": "a" * 64,
                "title": f"Synthetic {user_id[-4:]}",
                "stamp": stamp,
            },
        )


def _history(service: ConsentService, user_id: str, start: int) -> list[dict]:
    first = service.accept(
        user_id, expected_record_id=None, expected_revision=0, now=start
    )
    first_w = service.withdraw(
        user_id,
        expected_record_id=first["id"],
        expected_revision=first["revision"],
        now=start + 1,
    )
    second = service.accept(
        user_id,
        expected_record_id=first_w["id"],
        expected_revision=first_w["revision"],
        now=start + 2,
    )
    second_w = service.withdraw(
        user_id,
        expected_record_id=second["id"],
        expected_revision=second["revision"],
        now=start + 3,
    )
    return [first_w, second_w]


def _consent_rows(runtime) -> list[tuple]:
    with runtime.engine.connect() as conn:
        return list(
            conn.execute(
                text(
                    "SELECT id,user_id,consent_type,scope,policy_version,policy_hash,"
                    "provider,purpose,status,cycle,revision,accepted_at,withdrawn_at,"
                    "created_at,updated_at FROM ai_consents ORDER BY user_id,cycle,id"
                )
            ).tuples()
        )


def test_t05_postgresql_migration_history_cascade_and_destructive_downgrade():
    name, url = _create_db("legal001_t05")
    owner_a, owner_b = str(uuid4()), str(uuid4())
    vacancy_a, vacancy_b = str(uuid4()), str(uuid4())
    try:
        upgrade_database(url, "20260917_0020")
        runtime = create_database(url)
        try:
            assert current_revision(runtime.engine) == "20260917_0020"
            assert "ai_consents" not in inspect(runtime.engine).get_table_names()
            _insert_owner_and_vacancy(runtime, owner_a, vacancy_a, 100)
            _insert_owner_and_vacancy(runtime, owner_b, vacancy_b, 101)
            with runtime.engine.connect() as conn:
                assert conn.scalar(text("SELECT COUNT(*) FROM users")) == 2
                assert conn.scalar(text("SELECT COUNT(*) FROM saved_vacancies")) == 2
        finally:
            runtime.dispose()

        upgrade_database(url, "20260922_0021")
        runtime = create_database(url)
        try:
            assert current_revision(runtime.engine) == "20260922_0021"
            # The 0021 migration is tested independently of the approved
            # 0023-to-0024 successor of the later runtime schema.
            assert CURRENT_REVISION == expected_schema_head(
                Path(__file__).resolve().parents[1], "20261002_0023",
            )
            inspector = inspect(runtime.engine)
            assert "ai_consents" in inspector.get_table_names()
            columns = {column["name"] for column in inspector.get_columns("ai_consents")}
            assert columns == {
                "id", "user_id", "consent_type", "scope", "policy_version",
                "policy_hash", "provider", "purpose", "status", "cycle", "revision",
                "accepted_at", "withdrawn_at", "created_at", "updated_at",
            }
            fks = inspector.get_foreign_keys("ai_consents")
            assert any(
                fk["referred_table"] == "users"
                and fk["referred_columns"] == ["id"]
                and str((fk.get("options") or {}).get("ondelete", "")).upper() == "CASCADE"
                for fk in fks
            )
            with runtime.engine.connect() as conn:
                assert conn.scalar(text("SELECT COUNT(*) FROM users")) == 2
                assert conn.scalar(text("SELECT COUNT(*) FROM saved_vacancies")) == 2
                assert conn.scalar(text("SELECT COUNT(*) FROM ai_consents")) == 0

            service = ConsentService(ConsentRepository(runtime))
            hist_a = _history(service, owner_a, 200)
            hist_b = _history(service, owner_b, 300)
            assert [row["cycle"] for row in hist_a] == [1, 2]
            assert [row["revision"] for row in hist_a] == [2, 2]
            assert all(row["status"] == "withdrawn" for row in hist_a + hist_b)
            assert all(row["withdrawn_at"] >= row["accepted_at"] for row in hist_a + hist_b)
            assert hist_a[0]["id"] != hist_a[1]["id"]

            current = service.state(owner_b)["current"]
            assert current and current["status"] == "withdrawn"
            expected = (current["id"], current["revision"])

            def accept_same_state(_):
                try:
                    return ("ok", service.accept(
                        owner_b,
                        expected_record_id=expected[0],
                        expected_revision=expected[1],
                        now=400,
                    ))
                except ConsentStaleStateError:
                    return ("stale", None)

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(accept_same_state, range(2)))
            assert sorted(result[0] for result in results) == ["ok", "stale"]
            active = service.state(owner_b)["current"]
            assert active and active["status"] == "accepted" and active["cycle"] == 3
            withdrawn = service.withdraw(
                owner_b,
                expected_record_id=active["id"],
                expected_revision=active["revision"],
                now=401,
            )
            assert withdrawn["status"] == "withdrawn" and withdrawn["revision"] == 2
            with runtime.engine.connect() as conn:
                assert conn.scalar(
                    text("SELECT COUNT(*) FROM ai_consents WHERE status='accepted'")
                ) == 0

            with runtime.engine.begin() as conn:
                conn.execute(text("DELETE FROM users WHERE id=:id"), {"id": owner_a})
            with runtime.engine.connect() as conn:
                assert conn.scalar(
                    text("SELECT COUNT(*) FROM ai_consents WHERE user_id=:id"), {"id": owner_a}
                ) == 0
                assert conn.scalar(
                    text("SELECT COUNT(*) FROM ai_consents WHERE user_id=:id"), {"id": owner_b}
                ) == 3
                assert conn.scalar(
                    text("SELECT COUNT(*) FROM saved_vacancies WHERE user_id=:id"), {"id": owner_b}
                ) == 1
        finally:
            runtime.dispose()

        downgrade_database(url, "20260917_0020")
        runtime = create_database(url)
        try:
            assert current_revision(runtime.engine) == "20260917_0020"
            assert "ai_consents" not in inspect(runtime.engine).get_table_names()
            with runtime.engine.connect() as conn:
                assert conn.scalar(text("SELECT COUNT(*) FROM users WHERE id=:id"), {"id": owner_b}) == 1
                assert conn.scalar(
                    text("SELECT COUNT(*) FROM saved_vacancies WHERE user_id=:id"), {"id": owner_b}
                ) == 1
        finally:
            runtime.dispose()

        upgrade_database(url, "20260922_0021")
        runtime = create_database(url)
        try:
            assert current_revision(runtime.engine) == "20260922_0021"
            with runtime.engine.connect() as conn:
                assert conn.scalar(text("SELECT COUNT(*) FROM ai_consents")) == 0
        finally:
            runtime.dispose()
    finally:
        _drop_db(name)


def test_t05_postgresql_encrypted_backup_restore_preserves_consent_history(tmp_path):
    if not os.environ.get("PG_DUMP_BIN") or not os.environ.get("PG_RESTORE_BIN"):
        pytest.skip("Dedicated LEGAL-001 PostgreSQL workflow provides pg_dump/pg_restore wrappers.")

    source_name, source_url = _create_db("legal001_backup_source")
    restore_name, restore_url = _create_db("legal001_backup_restore")
    owner_a, owner_b = str(uuid4()), str(uuid4())
    try:
        upgrade_database(source_url, "20260922_0021")
        source = create_database(source_url)
        try:
            _insert_owner_and_vacancy(source, owner_a, str(uuid4()), 500)
            _insert_owner_and_vacancy(source, owner_b, str(uuid4()), 501)
            service = ConsentService(ConsentRepository(source))
            _history(service, owner_a, 600)
            _history(service, owner_b, 700)
            before = _consent_rows(source)
            assert len(before) == 4
        finally:
            source.dispose()

        result = backup_database(
            source_url,
            tmp_path,
            output_name="legal001-t05.dump",
            encryption_key=TEST_KEY,
            environment="test",
            service_name="ai-career-agent",
            app_version="legal001-t05",
        )
        manifest = validate_backup(result.backup_path, result.manifest_path)
        assert manifest["encrypted"] is True
        assert manifest["database_revision"] == "20260922_0021"

        restored = restore_database(
            result.backup_path,
            restore_url,
            manifest_path=result.manifest_path,
            encryption_key=TEST_KEY,
            environment="test",
        )
        assert restored.verified is True
        assert restored.database_revision == "20260922_0021"

        target = create_database(restore_url)
        try:
            after = _consent_rows(target)
            assert after == before
        finally:
            target.dispose()
    finally:
        _drop_db(restore_name)
        _drop_db(source_name)
