#!/usr/bin/env python3
"""Seed and verify the bounded HOST-001 Stage C synthetic restore fixture.

This helper is intentionally narrow:
- it accepts only the reviewed Yandex Managed PostgreSQL source/restore database names;
- it requires an explicit synthetic-only acknowledgement;
- it writes only deterministic .invalid/test fixture rows;
- it never calls vacancy, AI, email, OAuth, or other external providers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


ACK = "HOST001_STAGE_C_SYNTHETIC_ONLY"
FIXTURE_NAMESPACE = uuid.UUID("5de13a4f-8901-4f63-9102-4cbbb94c9911")
FIXTURE_VERSION = 1
USER_ID = str(uuid.uuid5(FIXTURE_NAMESPACE, "user"))
VACANCY_ID = str(uuid.uuid5(FIXTURE_NAMESPACE, "saved-vacancy"))
VACANCY_SOURCE_ID = str(uuid.uuid5(FIXTURE_NAMESPACE, "saved-vacancy-source"))
CONSENT_ID = str(uuid.uuid5(FIXTURE_NAMESPACE, "consent"))
DRAFT_ID = str(uuid.uuid5(FIXTURE_NAMESPACE, "resume-draft"))
VERSION_ID = str(uuid.uuid5(FIXTURE_NAMESPACE, "resume-version"))
ASSET_ID = str(uuid.uuid5(FIXTURE_NAMESPACE, "resume-asset"))
EXPORT_ID = str(uuid.uuid5(FIXTURE_NAMESPACE, "resume-export"))
FIXTURE_EMAIL = "host001-stage-c@example.invalid"
ASSET_BYTES = b"ACA-HOST001-STAGE-C-SYNTHETIC-RESUME-ASSET-V1"
SELECTED_TABLES = (
    "users",
    "saved_vacancies",
    "saved_vacancy_sources",
    "ai_consents",
    "resume_drafts",
    "resume_versions",
    "resume_assets",
    "resume_exports",
)


class FixtureError(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _require_reviewed_target(database_url: str, *, restore: bool) -> None:
    try:
        parsed = urlsplit(database_url)
    except ValueError as exc:
        raise FixtureError("database_url_invalid") from exc
    host = (parsed.hostname or "").lower()
    database = parsed.path.lstrip("/")
    username = parsed.username or ""
    expected_database = "aca_restore" if restore else "ai_career_agent"
    expected_username = "aca_restore" if restore else "ai_career_agent"
    if not parsed.scheme.startswith("postgresql"):
        raise FixtureError("postgresql_required")
    if not host.endswith(".rw.mdb.yandexcloud.net"):
        raise FixtureError("reviewed_yandex_rw_host_required")
    if database != expected_database or username != expected_username:
        raise FixtureError("reviewed_stage_c_database_identity_required")


def _database_url(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise FixtureError(f"{name}_missing")
    return value


def _schema_signature(engine) -> dict[str, Any]:
    from sqlalchemy import inspect

    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    missing = [name for name in SELECTED_TABLES if name not in existing]
    if missing:
        raise FixtureError("fixture_tables_missing:" + ",".join(sorted(missing)))

    result: dict[str, Any] = {}
    for table in SELECTED_TABLES:
        result[table] = {
            "indexes": sorted(
                str(item.get("name") or "")
                for item in inspector.get_indexes(table)
                if item.get("name")
            ),
            "unique_constraints": sorted(
                str(item.get("name") or "")
                for item in inspector.get_unique_constraints(table)
                if item.get("name")
            ),
            "foreign_keys": sorted(
                [
                    str(item.get("name") or ""),
                    list(item.get("constrained_columns") or ()),
                    str(item.get("referred_table") or ""),
                    list(item.get("referred_columns") or ()),
                ]
                for item in inspector.get_foreign_keys(table)
            ),
        }
    return result


def _sequence_signature(engine) -> list[dict[str, Any]]:
    from sqlalchemy import text

    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT schemaname, sequencename, last_value, start_value,
                       increment_by, min_value, max_value, cycle, cache_size
                FROM pg_sequences
                WHERE schemaname = 'public'
                ORDER BY sequencename
                """
            )
        ).mappings()
        return [dict(row) for row in rows]


def _fixture_counts(engine) -> dict[str, int]:
    from sqlalchemy import text

    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table in SELECTED_TABLES:
            counts[table] = int(
                connection.scalar(text(f'SELECT COUNT(*) FROM "{table}"')) or 0
            )
    return counts


def _fixture_state() -> tuple[str, str]:
    state = json.dumps(
        {
            "schemaVersion": 1,
            "index": 1,
            "answers": {"name": "HOST-001 Stage C Synthetic"},
            "messages": [],
            "photoAssetId": ASSET_ID,
            "universityLogoAssetId": None,
            "universityLogoFor": "",
            "universityResolvedName": "",
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return state, _sha256_text(state)


def _assert_fixture_rows(engine) -> None:
    from sqlalchemy import text

    with engine.connect() as connection:
        owner = connection.execute(
            text("SELECT email,status FROM users WHERE id=:id"),
            {"id": USER_ID},
        ).one_or_none()
        vacancy = connection.execute(
            text(
                "SELECT title,company,note,revision "
                "FROM saved_vacancies WHERE id=:id"
            ),
            {"id": VACANCY_ID},
        ).one_or_none()
        source = connection.execute(
            text(
                "SELECT source,external_id "
                "FROM saved_vacancy_sources WHERE id=:id"
            ),
            {"id": VACANCY_SOURCE_ID},
        ).one_or_none()
        consent = connection.execute(
            text(
                "SELECT status,cycle,revision,provider,purpose "
                "FROM ai_consents WHERE id=:id"
            ),
            {"id": CONSENT_ID},
        ).one_or_none()
        asset = connection.execute(
            text(
                "SELECT byte_size,sha256,data "
                "FROM resume_assets WHERE id=:id"
            ),
            {"id": ASSET_ID},
        ).one_or_none()

    owner_tuple = tuple(owner) if owner is not None else None
    vacancy_tuple = tuple(vacancy) if vacancy is not None else None
    source_tuple = tuple(source) if source is not None else None
    consent_tuple = tuple(consent) if consent is not None else None

    if owner_tuple != (FIXTURE_EMAIL, "active"):
        raise FixtureError("restored_owner_fixture_mismatch")
    if vacancy_tuple != (
        "Synthetic Stage C vacancy",
        "Synthetic Co",
        "synthetic-only",
        1,
    ):
        raise FixtureError("restored_job_fixture_mismatch")
    if source_tuple != ("hh", "host001-stage-c-synthetic-vacancy"):
        raise FixtureError("restored_job_source_fixture_mismatch")
    if consent_tuple != (
        "withdrawn",
        1,
        2,
        "alice",
        "synthetic_restore_fixture",
    ):
        raise FixtureError("restored_legal_fixture_mismatch")

    expected_hash = _sha256_bytes(ASSET_BYTES)
    if (
        asset is None
        or int(asset[0]) != len(ASSET_BYTES)
        or asset[1] != expected_hash
        or bytes(asset[2]) != ASSET_BYTES
    ):
        raise FixtureError("restored_resume_asset_bytes_mismatch")


def seed(database_url: str, evidence_path: Path) -> dict[str, Any]:
    from database import CURRENT_REVISION, create_database, current_revision

    _require_reviewed_target(database_url, restore=False)
    runtime = create_database(database_url)
    try:
        revision = current_revision(runtime.engine)
        if revision != CURRENT_REVISION:
            raise FixtureError(
                f"schema_revision_mismatch:{revision or 'unversioned'}:{CURRENT_REVISION}"
            )

        now = int(time.time())
        state, state_hash = _fixture_state()
        snapshot = json.dumps(
            {
                "source": "host001-stage-c",
                "external_id": "synthetic-vacancy-1",
                "title": "Synthetic Stage C vacancy",
                "company": "Synthetic Co",
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        snapshot_hash = _sha256_text(snapshot)
        asset_hash = _sha256_bytes(ASSET_BYTES)
        policy_hash = _sha256_text("host001-stage-c-withdrawn-policy")
        identity_hash = _sha256_text("hh:host001-stage-c-synthetic-vacancy")
        pdf_hash = _sha256_text("host001-stage-c-synthetic-pdf-metadata")

        with runtime.engine.begin() as connection:
            existing = connection.scalar(
                text("SELECT COUNT(*) FROM users WHERE id=:id"),
                {"id": USER_ID},
            )
            if int(existing or 0) == 0:
                connection.execute(
                    text(
                        """
                        INSERT INTO users (
                            id, email, normalized_email, display_name, status,
                            email_verified_at, created_at, updated_at
                        ) VALUES (
                            :id, :email, :email, :display_name, 'active',
                            :now, :now, :now
                        )
                        """
                    ),
                    {
                        "id": USER_ID,
                        "email": FIXTURE_EMAIL,
                        "display_name": "HOST-001 Stage C synthetic",
                        "now": now,
                    },
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO saved_vacancies (
                            id, user_id, snapshot_json, snapshot_hash, snapshot_version,
                            title, company, location, search_text, note, revision,
                            created_at, updated_at
                        ) VALUES (
                            :id, :user_id, :snapshot, :snapshot_hash, 'job001-v1',
                            'Synthetic Stage C vacancy', 'Synthetic Co', 'Synthetic',
                            'host001 stage c synthetic', 'synthetic-only', 1,
                            :now, :now
                        )
                        """
                    ),
                    {
                        "id": VACANCY_ID,
                        "user_id": USER_ID,
                        "snapshot": snapshot,
                        "snapshot_hash": snapshot_hash,
                        "now": now,
                    },
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO saved_vacancy_sources (
                            id, saved_vacancy_id, user_id, source, external_id,
                            identity_hash, url, created_at
                        ) VALUES (
                            :id, :vacancy_id, :user_id, 'hh',
                            'host001-stage-c-synthetic-vacancy',
                            :identity_hash, 'https://example.invalid/vacancy/synthetic',
                            :now
                        )
                        """
                    ),
                    {
                        "id": VACANCY_SOURCE_ID,
                        "vacancy_id": VACANCY_ID,
                        "user_id": USER_ID,
                        "identity_hash": identity_hash,
                        "now": now,
                    },
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO ai_consents (
                            id, user_id, consent_type, scope, policy_version, policy_hash,
                            provider, purpose, status, cycle, revision, accepted_at,
                            withdrawn_at, created_at, updated_at
                        ) VALUES (
                            :id, :user_id, 'ai_generation', 'cover_letter',
                            'host001-stage-c-synthetic-v1', :policy_hash,
                            'alice', 'synthetic_restore_fixture', 'withdrawn',
                            1, 2, :accepted_at, :withdrawn_at, :accepted_at, :withdrawn_at
                        )
                        """
                    ),
                    {
                        "id": CONSENT_ID,
                        "user_id": USER_ID,
                        "policy_hash": policy_hash,
                        "accepted_at": now - 1,
                        "withdrawn_at": now,
                    },
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO resume_drafts (
                            id, user_id, schema_version, revision, title,
                            state_json, content_hash, completion_percent,
                            profile_version, created_at, updated_at
                        ) VALUES (
                            :id, :user_id, 1, 1, 'HOST-001 Stage C resume',
                            :state, :content_hash, 25, NULL, :now, :now
                        )
                        """
                    ),
                    {
                        "id": DRAFT_ID,
                        "user_id": USER_ID,
                        "state": state,
                        "content_hash": state_hash,
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
                            :id, :draft_id, 1, 1, 1, :state, :content_hash,
                            'checkpoint', NULL, :now
                        )
                        """
                    ),
                    {
                        "id": VERSION_ID,
                        "draft_id": DRAFT_ID,
                        "state": state,
                        "content_hash": state_hash,
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
                            :id, :draft_id, :user_id, 'photo',
                            'application/octet-stream', :byte_size, :sha256, :data, :now
                        )
                        """
                    ),
                    {
                        "id": ASSET_ID,
                        "draft_id": DRAFT_ID,
                        "user_id": USER_ID,
                        "byte_size": len(ASSET_BYTES),
                        "sha256": asset_hash,
                        "data": ASSET_BYTES,
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
                            :id, :draft_id, :version_id, 1, 1, 128,
                            :pdf_hash, 'stage-c-synthetic.pdf', :now
                        )
                        """
                    ),
                    {
                        "id": EXPORT_ID,
                        "draft_id": DRAFT_ID,
                        "version_id": VERSION_ID,
                        "pdf_hash": pdf_hash,
                        "now": now,
                    },
                )

        _assert_fixture_rows(runtime.engine)

        evidence = {
            "fixture_version": FIXTURE_VERSION,
            "database_revision": revision,
            "asset_sha256": asset_hash,
            "asset_size": len(ASSET_BYTES),
            "fixture_counts": _fixture_counts(runtime.engine),
            "schema_signature": _schema_signature(runtime.engine),
            "sequence_signature": _sequence_signature(runtime.engine),
        }
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.chmod(evidence_path, 0o600)
        return {
            "ok": True,
            "mode": "seed",
            "fixture_version": FIXTURE_VERSION,
            "database_revision": revision,
            "asset_sha256": asset_hash,
            "asset_size": len(ASSET_BYTES),
            "evidence_file": evidence_path.name,
        }
    finally:
        runtime.dispose()


def verify(database_url: str, evidence_path: Path) -> dict[str, Any]:
    from database import CURRENT_REVISION, create_database, current_revision

    _require_reviewed_target(database_url, restore=True)
    if not evidence_path.is_file():
        raise FixtureError("fixture_evidence_missing")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    runtime = create_database(database_url)
    try:
        revision = current_revision(runtime.engine)
        if revision != evidence.get("database_revision") or revision != CURRENT_REVISION:
            raise FixtureError("restored_revision_mismatch")
        if _fixture_counts(runtime.engine) != evidence.get("fixture_counts"):
            raise FixtureError("restored_fixture_counts_mismatch")
        if _schema_signature(runtime.engine) != evidence.get("schema_signature"):
            raise FixtureError("restored_schema_signature_mismatch")
        if _sequence_signature(runtime.engine) != evidence.get("sequence_signature"):
            raise FixtureError("restored_sequence_signature_mismatch")

        _assert_fixture_rows(runtime.engine)
        expected_hash = _sha256_bytes(ASSET_BYTES)

        return {
            "ok": True,
            "mode": "verify",
            "fixture_version": FIXTURE_VERSION,
            "database_revision": revision,
            "asset_sha256": expected_hash,
            "asset_size": len(ASSET_BYTES),
            "schema_signature_match": True,
            "sequence_signature_match": True,
        }
    finally:
        runtime.dispose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("seed", "verify"))
    parser.add_argument("--ack", required=True)
    parser.add_argument(
        "--evidence",
        default="/var/backups/ai-career-agent/host001-stage-c-fixture.json",
    )
    args = parser.parse_args()

    if args.ack != ACK:
        print(json.dumps({"ok": False, "error": "synthetic_ack_required"}))
        return 2

    try:
        if args.mode == "seed":
            result = seed(
                _database_url("DATABASE_URL"),
                Path(args.evidence).expanduser().resolve(),
            )
        else:
            result = verify(
                _database_url("RESTORE_DATABASE_URL"),
                Path(args.evidence).expanduser().resolve(),
            )
    except (FixtureError, ValueError, TypeError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
