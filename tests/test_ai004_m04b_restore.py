"""AI004-M04B encrypted backup/restore integrity on disposable synthetic SQLite.

Unlike a table-count-only backup manifest, these tests prove signed report
bytes, owner isolation and cascading source deletion *after* restore. No real
data, providers, cloud service or production DB is involved.
"""
from __future__ import annotations

import base64
import hashlib
import json

import pytest
from sqlalchemy import delete, func, select

from database import CURRENT_REVISION, create_database, current_revision, upgrade_database
from models import ResumeVersion, SavedVacancy, User
from models.user_match import UserMatchCache, UserMatchReport
from operations.backup import backup_database, restore_database, validate_backup
from repositories.user_match import UserMatchStorageError
from tests.test_ai004_m04b_storage import NOW, claim, repo, seed, settle, validated

KEY = base64.urlsafe_b64encode(b"R" * 32).decode("ascii")


def _read(storage, source, now=NOW + 45):
    return storage.load_saved(
        user_id=source["owner"], resume_version_id=source["version"],
        saved_vacancy_id=source["saved"], now=now,
    )


def test_encrypted_restore_preserves_owned_signed_results_and_cascades(tmp_path):
    initial = f"sqlite:///{tmp_path / 'm04b-source.db'}"
    target = f"sqlite:///{tmp_path / 'm04b-restored.db'}"
    upgrade_database(initial)
    source_db = create_database(initial)
    try:
        owner_a = seed(source_db, suffix="backup-a")
        owner_b = seed(source_db, suffix="backup-b")
        storage = repo(source_db)
        for owner in (owner_a, owner_b):
            pending = claim(storage, owner)
            settle(source_db, owner, pending["id"], validated(source_db, owner))

        before = {
            owner["owner"]: _read(storage, owner)["report"]
            for owner in (owner_a, owner_b)
        }
        assert all(
            r["result"]["summary"]["score_percent"] == 100 for r in before.values()
        )

        artifact = backup_database(
            initial, tmp_path / "encrypted-backups",
            output_name="m04b-owned-results.sqlite3",
            environment="test", encryption_key=KEY,
        )
        assert artifact.manifest["encrypted"] is True
        assert artifact.manifest["database_revision"] == CURRENT_REVISION
        assert artifact.manifest["table_counts"]["user_match_reports"] == 2
        assert artifact.manifest["table_counts"]["user_match_cache"] == 2
        assert validate_backup(artifact.backup_path) == artifact.manifest

        restored = restore_database(
            artifact.backup_path, target,
            environment="test", encryption_key=KEY,
        )
        assert restored.verified is True
        assert restored.database_revision == CURRENT_REVISION
        assert restored.table_counts["user_match_reports"] == 2
        assert restored.table_counts["user_match_cache"] == 2
    finally:
        source_db.dispose()

    restored_db = create_database(target)
    try:
        assert current_revision(restored_db.engine) == CURRENT_REVISION
        copied = repo(restored_db)
        for owner in (owner_a, owner_b):
            row = _read(copied, owner)
            assert row["state"] == "ready"
            original = before[owner["owner"]]
            assert row["report"]["result"] == original["result"]
            assert row["report"]["source_hash"] == original["source_hash"]
            assert row["report"]["resume_hash"] == original["resume_hash"]
            assert row["report"]["vacancy_hash"] == original["vacancy_hash"]
            assert row["report"]["result_hash"] == original["result_hash"]
            assert row["report"]["result"]["summary"]["score_percent"] == 100

        # A real owner must never be able to reuse the other owner's resume.
        with pytest.raises(UserMatchStorageError, match="^not_found$"):
            copied.load_saved(
                user_id=owner_a["owner"], resume_version_id=owner_b["version"],
                saved_vacancy_id=owner_a["saved"], now=NOW + 45,
            )
        with pytest.raises(UserMatchStorageError, match="^not_found$"):
            copied.load_saved(
                user_id=owner_b["owner"], resume_version_id=owner_b["version"],
                saved_vacancy_id=owner_a["saved"], now=NOW + 45,
            )

        # A malicious data edit that recomputes the plain SHA256 still cannot
        # forge the sealed report HMAC after encrypted restore.
        with restored_db.session() as session, session.begin():
            report = session.scalar(select(UserMatchReport).where(
                UserMatchReport.user_id == owner_a["owner"],
            ))
            report_json = json.loads(report.result_json)
            report_json["requirements"][0]["candidate_evidence"][0]["quote"] = (
                "fabricated resume evidence"
            )
            report.result_json = json.dumps(
                report_json, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            )
            report.result_hash = hashlib.sha256(report.result_json.encode()).hexdigest()
        with pytest.raises(UserMatchStorageError, match="^invalid_saved_report$"):
            _read(copied, owner_a)

        # Delete only A's saved vacancy on the restored DB. B survives
        # unchanged with the same signed report.
        with restored_db.session() as session, session.begin():
            session.execute(delete(SavedVacancy).where(
                SavedVacancy.id == owner_a["saved"],
                SavedVacancy.user_id == owner_a["owner"],
            ))
        with restored_db.session() as session:
            assert session.scalar(select(func.count()).select_from(
                UserMatchReport
            ).where(UserMatchReport.user_id == owner_a["owner"])) == 0
            assert session.scalar(select(func.count()).select_from(
                UserMatchCache
            ).where(UserMatchCache.user_id == owner_a["owner"])) == 0
        assert _read(copied, owner_b)["report"]["result"] == before[owner_b["owner"]]["result"]

        # Removing B's immutable resume version must also purge its derived
        # report/cache, with no residual owner-scoped data.
        with restored_db.session() as session, session.begin():
            session.execute(delete(ResumeVersion).where(
                ResumeVersion.id == owner_b["version"],
            ))
        with restored_db.session() as session:
            assert session.scalar(select(func.count()).select_from(
                UserMatchReport
            )) == 0
            assert session.scalar(select(func.count()).select_from(
                UserMatchCache
            )) == 0
            assert session.scalar(select(func.count()).select_from(
                User
            )) == 2
    finally:
        restored_db.dispose()
