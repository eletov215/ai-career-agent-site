"""CI-only PostgreSQL 18 encrypted backup/restore of populated M04B records.

Requires local disposable GitHub Actions PostgreSQL and native PostgreSQL 18
pg_dump/pg_restore wrappers. Refuses any remote/shared database URL before
performing SQL. Never connects to Neon or any paid provider/cloud resource.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os

import pytest
from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.engine import make_url

from database import CURRENT_REVISION, create_database, upgrade_database
from models import SavedVacancy, User
from models.user_match import UserMatchCache, UserMatchReport
from operations.backup import backup_database, restore_database, validate_backup
from repositories.privacy import PrivacyRepository
from repositories.user_match import UserMatchStorageError
from services.privacy import PrivacyService
from tests.test_ai004_m04b_storage import (
    NOW, claim, repo, seed, settle, validated,
)
from tests.test_privacy_service import _settings

BACKUP_KEY = base64.urlsafe_b64encode(b"Q" * 32).decode("ascii")
RESTORED_DB = "ai004_m04b_restore_test"


def _url():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        pytest.fail("m04b_pg18_disposable_ci_only")
    raw = os.environ.get("POSTGRES_TEST_URL", "")
    parsed = make_url(raw)
    if not (
        parsed.get_backend_name() == "postgresql"
        and parsed.host in ("localhost", "127.0.0.1")
        and parsed.port == 5432
        and parsed.username == "candidate"
        and parsed.database == "ai004_m04b_test"
    ):
        pytest.fail("m04b_pg18_disposable_url_required")
    for var in ("PG_DUMP_BIN", "PG_RESTORE_BIN"):
        if not os.environ.get(var):
            pytest.fail("m04b_pg18_client_missing")
    return parsed


def _read(db, source):
    return repo(db).load_saved(
        user_id=source["owner"], resume_version_id=source["version"],
        saved_vacancy_id=source["saved"], now=NOW + 50,
    )


@pytest.mark.skipif(
    os.environ.get("M04B_PG18_RESTORE_ENABLED") != "1",
    reason="Populated-row PostgreSQL 18 restore runs in the mandatory isolated M04B CI job",
)
def test_disposable_pg18_encrypted_restore_preserves_rows_hmac_and_owner(tmp_path):
    source_url = _url()
    source_str = source_url.render_as_string(hide_password=False)
    restored_url = source_url.set(database=RESTORED_DB)
    restored_str = restored_url.render_as_string(hide_password=False)
    admin_url = source_url.set(database="postgres")
    admin = None
    source = None
    restored = None
    owners = []
    created = False
    try:
        upgrade_database(source_str)
        source = create_database(source_str)
        owner_a = seed(source, suffix="pg18-backup-a")
        owner_b = seed(source, suffix="pg18-backup-b")
        owners = [owner_a, owner_b]
        originals = {}
        for owner in owners:
            cache = claim(repo(source), owner)
            assert settle(source, owner, cache["id"], validated(source, owner))[1]
            originals[owner["owner"]] = _read(source, owner)["report"]

        backup = backup_database(
            source_str, tmp_path / "pg18-encrypted",
            output_name="ai004-m04b-ci-pg18.dump",
            encryption_key=BACKUP_KEY, environment="test",
            pg_dump_bin=os.environ["PG_DUMP_BIN"],
            pg_restore_bin=os.environ["PG_RESTORE_BIN"],
        )
        assert backup.manifest["encrypted"] is True
        assert backup.manifest["database_revision"] == CURRENT_REVISION
        for table in ("user_match_reports", "user_match_cache"):
            assert backup.manifest["table_counts"][table] == 2
        assert validate_backup(backup.backup_path) == backup.manifest

        # Create a second *disposable* DB on the same CI service. Never reuse
        # the source or connect to a named remote service.
        admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            conn.execute(text("CREATE DATABASE " + RESTORED_DB))
        created = True
        copied = restore_database(
            backup.backup_path, restored_str,
            encryption_key=BACKUP_KEY, environment="test", clean=False,
            pg_restore_bin=os.environ["PG_RESTORE_BIN"],
        )
        assert copied.verified is True
        assert copied.database_revision == CURRENT_REVISION
        for table in ("user_match_reports", "user_match_cache"):
            assert copied.table_counts[table] == 2

        restored = create_database(restored_str)
        for owner in owners:
            current = _read(restored, owner)
            assert current["state"] == "ready"
            assert current["report"]["source_hash"] == originals[owner["owner"]]["source_hash"]
            assert current["report"]["result_hash"] == originals[owner["owner"]]["result_hash"]
            assert current["report"]["result"] == originals[owner["owner"]]["result"]

        with pytest.raises(UserMatchStorageError, match="^not_found$"):
            repo(restored).load_saved(
                user_id=owner_a["owner"],
                resume_version_id=owner_b["version"],
                saved_vacancy_id=owner_a["saved"], now=NOW + 50,
            )

        # User-specific privacy ZIP must not leak the other tenant's reports.
        privacy = PrivacyService(PrivacyRepository(restored), _settings(tmp_path))
        artifact = privacy.export_user_data(
            owner_a["owner"],
            expected_password_hash="safe-fake-password-hash",
            now=NOW + 51,
        )
        from io import BytesIO
        from zipfile import ZipFile
        with ZipFile(BytesIO(artifact.content)) as archive:
            exported = json.loads(archive.read("data.json"))
            manifest = json.loads(archive.read("manifest.json"))
        assert len(exported["user_match_reports"]) == 1
        assert len(exported["user_match_cache"]) == 1
        assert exported["user_match_reports"][0]["id"] == originals[owner_a["owner"]]["id"]
        assert manifest["counts"]["user_match_reports"] == 1

        # Detect malicious corruption despite recomputation of the public
        # SHA256: only the secret-backed HMAC from M04A authenticates content.
        with restored.session() as s, s.begin():
            row = s.scalar(select(UserMatchReport).where(
                UserMatchReport.user_id == owner_a["owner"],
            ))
            altered = json.loads(row.result_json)
            altered["requirements"][0]["candidate_evidence"][0]["quote"] = "fake"
            row.result_json = json.dumps(
                altered, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            )
            row.result_hash = hashlib.sha256(row.result_json.encode()).hexdigest()
        with pytest.raises(UserMatchStorageError, match="^invalid_saved_report$"):
            _read(restored, owner_a)

        # Deletion after restore is cascade-safe and strictly isolated.
        with restored.session() as s, s.begin():
            s.execute(delete(SavedVacancy).where(
                SavedVacancy.id == owner_a["saved"],
                SavedVacancy.user_id == owner_a["owner"],
            ))
        assert _read(restored, owner_b)["report"] == originals[owner_b["owner"]]
        with restored.session() as s:
            for model in (UserMatchCache, UserMatchReport):
                assert s.scalar(select(func.count()).select_from(model).where(
                    model.user_id == owner_a["owner"],
                )) == 0
                assert s.scalar(select(func.count()).select_from(model).where(
                    model.user_id == owner_b["owner"],
                )) == 1
    finally:
        if restored:
            restored.dispose()
        if source:
            try:
                with source.session() as s, s.begin():
                    for owner in owners:
                        s.execute(delete(User).where(User.id == owner["owner"]))
            finally:
                source.dispose()
        if created and admin is not None:
            with admin.connect() as conn:
                conn.execute(text("DROP DATABASE " + RESTORED_DB + " WITH (FORCE)"))
        if admin:
            admin.dispose()
