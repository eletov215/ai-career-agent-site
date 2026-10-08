#!/usr/bin/env python3
"""Seed and verify the deterministic HOST-001 Stage C synthetic restore fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url

from database import CURRENT_REVISION, DatabaseRuntime, create_database, current_revision
from models import (
    AIConsent,
    ResumeAsset,
    ResumeDraft,
    SavedVacancy,
    SavedVacancySource,
    SavedVacancyTracker,
    SavedVacancyTrackerEvent,
    User,
)

_ACK = "SEED_STAGE_C_SYNTHETIC_ONLY"
_USER_ID = "00000000-0000-4000-8000-0000000000c1"
_DRAFT_ID = "00000000-0000-4000-8000-0000000000c2"
_ASSET_ID = "00000000-0000-4000-8000-0000000000c3"
_SAVED_ID = "00000000-0000-4000-8000-0000000000c4"
_SOURCE_ID = "00000000-0000-4000-8000-0000000000c5"
_EVENT_ID = "00000000-0000-4000-8000-0000000000c6"
_CONSENT_ID = "00000000-0000-4000-8000-0000000000c7"
_TIMESTAMP = 1_760_000_000
_ASSET_BYTES = b"\x89PNG\r\n\x1a\nACA-STAGE-C-ASSET-v1\x00\xff"
_EMAIL = "stage-c-owner@example.invalid"


class StageCFixtureError(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _stage_c_url_from_env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise StageCFixtureError(f"{name} is required.")
    try:
        parsed = make_url(value)
    except Exception as exc:
        raise StageCFixtureError(f"{name} is not a valid database URL.") from exc
    if parsed.get_backend_name() != "postgresql" or parsed.get_driver_name() != "psycopg":
        raise StageCFixtureError(f"{name} must use postgresql+psycopg://.")
    host = (parsed.host or "").lower()
    if not host.endswith(".mdb.yandexcloud.net"):
        raise StageCFixtureError(f"{name} must point to a Yandex Managed PostgreSQL host.")
    if parsed.database not in {"ai_career_agent", "aca_restore"}:
        raise StageCFixtureError(f"{name} points to an unexpected database.")
    return value


def _schema_report(runtime: DatabaseRuntime) -> dict[str, object]:
    inspector = inspect(runtime.engine)
    selected_tables = (
        "users",
        "resume_drafts",
        "resume_assets",
        "saved_vacancies",
        "saved_vacancy_sources",
        "saved_vacancy_trackers",
        "saved_vacancy_tracker_events",
        "ai_consents",
    )
    objects: list[str] = []
    by_table: dict[str, dict[str, list[str]]] = {}
    for table in selected_tables:
        indexes = sorted(
            str(item.get("name"))
            for item in inspector.get_indexes(table)
            if item.get("name")
        )
        uniques = sorted(
            str(item.get("name"))
            for item in inspector.get_unique_constraints(table)
            if item.get("name")
        )
        checks = sorted(
            str(item.get("name"))
            for item in inspector.get_check_constraints(table)
            if item.get("name")
        )
        foreign_keys = sorted(
            str(item.get("name"))
            for item in inspector.get_foreign_keys(table)
            if item.get("name")
        )
        by_table[table] = {
            "indexes": indexes,
            "unique_constraints": uniques,
            "check_constraints": checks,
            "foreign_keys": foreign_keys,
        }
        for kind, names in by_table[table].items():
            objects.extend(f"{table}:{kind}:{name}" for name in names)

    if runtime.backend == "postgresql":
        required = {
            "users": {
                "indexes": {"idx_users_status"},
                "unique_constraints": {"uq_users_normalized_email"},
            },
            "resume_assets": {
                "indexes": {"idx_resume_assets_user_draft", "idx_resume_assets_created"},
                "unique_constraints": {"uq_resume_assets_draft_kind_sha256"},
                "check_constraints": {"ck_resume_assets_kind", "ck_resume_assets_byte_size"},
            },
            "saved_vacancies": {
                "indexes": {"idx_saved_vacancy_owner_created"},
                "unique_constraints": {"uq_saved_vacancy_id_owner"},
                "check_constraints": {"ck_saved_vacancy_revision"},
            },
            "saved_vacancy_trackers": {
                "indexes": {"idx_tracker_owner_updated"},
                "unique_constraints": {"uq_tracker_saved_owner"},
                "check_constraints": {"ck_tracker_state", "ck_tracker_revision"},
            },
            "saved_vacancy_tracker_events": {
                "indexes": {"idx_tracker_event_owner_saved_revision"},
                "unique_constraints": {"uq_tracker_event_owner_saved_revision"},
                "check_constraints": {
                    "ck_tracker_event_from_state",
                    "ck_tracker_event_to_state",
                    "ck_tracker_event_changed",
                    "ck_tracker_event_revision",
                },
            },
            "ai_consents": {
                "indexes": {
                    "idx_ai_consents_owner_created",
                    "idx_ai_consents_owner_policy",
                    "uq_ai_consents_active_policy",
                },
                "unique_constraints": {"uq_ai_consents_policy_cycle"},
                "check_constraints": {
                    "ck_ai_consents_versions",
                    "ck_ai_consents_status",
                    "ck_ai_consents_withdrawal",
                },
            },
        }
        missing: list[str] = []
        for table, expected_kinds in required.items():
            actual = by_table[table]
            for kind, expected_names in expected_kinds.items():
                absent = sorted(expected_names.difference(actual[kind]))
                missing.extend(f"{table}:{kind}:{name}" for name in absent)
        if missing:
            raise StageCFixtureError(
                "Representative schema objects are missing: " + ", ".join(missing)
            )

    sequences: list[dict[str, object]] = []
    if runtime.backend == "postgresql":
        with runtime.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT sequencename, start_value, increment_by, last_value, cycle "
                    "FROM pg_sequences WHERE schemaname = 'public' ORDER BY sequencename"
                )
            ).mappings()
            sequences = [
                {
                    "name": str(row["sequencename"]),
                    "start_value": row["start_value"],
                    "increment_by": row["increment_by"],
                    "last_value": row["last_value"],
                    "cycle": bool(row["cycle"]),
                }
                for row in rows
            ]

    schema_payload = {
        "objects": sorted(objects),
        "sequences": sequences,
    }
    return {
        "selected_tables": list(selected_tables),
        "schema_digest": _sha256_text(_canonical_json(schema_payload)),
        "sequence_count": len(sequences),
        "sequences": sequences,
    }


def seed_fixture(runtime: DatabaseRuntime) -> None:
    if current_revision(runtime.engine) != CURRENT_REVISION:
        raise StageCFixtureError("Stage C fixture requires the accepted database revision.")

    snapshot = _canonical_json(
        {
            "source": "stage-c-synthetic",
            "external_id": "stage-c-job-1",
            "title": "Synthetic Stage C vacancy",
            "company": "Example Invalid LLC",
            "location": "Synthetic",
            "url": "https://example.invalid/jobs/stage-c-1",
        }
    )
    resume_state = _canonical_json(
        {
            "schema_version": 1,
            "owner": "Stage C Synthetic",
            "photo_asset_id": _ASSET_ID,
            "skills": ["synthetic-verification"],
        }
    )
    policy_hash = _sha256_text("stage-c-synthetic-policy-v1")

    with runtime.session() as session:
        existing = session.get(User, _USER_ID)
        total_users = int(session.scalar(select(func.count()).select_from(User)) or 0)
        if existing is not None:
            return
        if total_users != 0:
            raise StageCFixtureError(
                "Refusing to seed Stage C fixture into a database that already has users."
            )

        session.add(
            User(
                id=_USER_ID,
                email=_EMAIL,
                normalized_email=_EMAIL,
                display_name="Stage C Synthetic Owner",
                status="active",
                email_verified_at=_TIMESTAMP,
                password_hash=None,
                password_changed_at=None,
                last_login_at=None,
                created_at=_TIMESTAMP,
                updated_at=_TIMESTAMP,
            )
        )
        # These fixture mappers intentionally do not define all ORM
        # relationships. Flush each FK parent layer explicitly so SQLite and
        # PostgreSQL observe the same deterministic insertion order.
        session.flush()

        session.add(
            ResumeDraft(
                id=_DRAFT_ID,
                user_id=_USER_ID,
                schema_version=1,
                revision=1,
                title="Stage C Synthetic Resume",
                state_json=resume_state,
                content_hash=_sha256_text(resume_state),
                completion_percent=100,
                profile_version=None,
                created_at=_TIMESTAMP,
                updated_at=_TIMESTAMP,
            )
        )
        session.add(
            ResumeAsset(
                id=_ASSET_ID,
                draft_id=_DRAFT_ID,
                user_id=_USER_ID,
                kind="photo",
                content_type="image/png",
                byte_size=len(_ASSET_BYTES),
                sha256=_sha256_bytes(_ASSET_BYTES),
                data=_ASSET_BYTES,
                created_at=_TIMESTAMP,
            )
        )
        session.add(
            SavedVacancy(
                id=_SAVED_ID,
                user_id=_USER_ID,
                snapshot_json=snapshot,
                snapshot_hash=_sha256_text(snapshot),
                snapshot_version="stage-c-v1",
                title="Synthetic Stage C vacancy",
                company="Example Invalid LLC",
                location="Synthetic",
                search_text="synthetic stage c vacancy example invalid",
                note="synthetic-only",
                revision=1,
                created_at=_TIMESTAMP,
                updated_at=_TIMESTAMP,
            )
        )
        session.add(
            AIConsent(
                id=_CONSENT_ID,
                user_id=_USER_ID,
                consent_type="ai_processing",
                scope="stage_c_synthetic",
                policy_version="stage-c-synthetic-v1",
                policy_hash=policy_hash,
                provider="none",
                purpose="restore_verification",
                status="withdrawn",
                cycle=1,
                revision=2,
                accepted_at=_TIMESTAMP,
                withdrawn_at=_TIMESTAMP + 1,
                created_at=_TIMESTAMP,
                updated_at=_TIMESTAMP + 1,
            )
        )
        session.flush()

        session.add(
            SavedVacancySource(
                id=_SOURCE_ID,
                saved_vacancy_id=_SAVED_ID,
                user_id=_USER_ID,
                source="synthetic",
                external_id="stage-c-job-1",
                identity_hash=_sha256_text("synthetic:stage-c-job-1"),
                url="https://example.invalid/jobs/stage-c-1",
                created_at=_TIMESTAMP,
            )
        )
        session.add(
            SavedVacancyTracker(
                saved_vacancy_id=_SAVED_ID,
                user_id=_USER_ID,
                state="preparing",
                revision=2,
                created_at=_TIMESTAMP,
                updated_at=_TIMESTAMP + 1,
            )
        )
        session.flush()

        session.add(
            SavedVacancyTrackerEvent(
                id=_EVENT_ID,
                saved_vacancy_id=_SAVED_ID,
                user_id=_USER_ID,
                from_state="saved",
                to_state="preparing",
                event_revision=1,
                created_at=_TIMESTAMP + 1,
            )
        )
        session.commit()


def verify_fixture(runtime: DatabaseRuntime) -> dict[str, object]:
    revision = current_revision(runtime.engine)
    if revision != CURRENT_REVISION:
        raise StageCFixtureError(
            f"Unexpected database revision: {revision!r}; expected {CURRENT_REVISION!r}."
        )

    with runtime.session() as session:
        user = session.get(User, _USER_ID)
        draft = session.get(ResumeDraft, _DRAFT_ID)
        asset = session.get(ResumeAsset, _ASSET_ID)
        saved = session.get(SavedVacancy, _SAVED_ID)
        source = session.get(SavedVacancySource, _SOURCE_ID)
        tracker = session.get(SavedVacancyTracker, _SAVED_ID)
        event = session.get(SavedVacancyTrackerEvent, _EVENT_ID)
        consent = session.get(AIConsent, _CONSENT_ID)

        if user is None or user.normalized_email != _EMAIL:
            raise StageCFixtureError("Synthetic owner record is missing or changed.")
        if draft is None or _ASSET_ID not in draft.state_json:
            raise StageCFixtureError("Synthetic resume draft is missing or changed.")
        if asset is None or bytes(asset.data) != _ASSET_BYTES:
            raise StageCFixtureError("Synthetic resume asset bytes are missing or changed.")
        if asset.sha256 != _sha256_bytes(_ASSET_BYTES):
            raise StageCFixtureError("Synthetic resume asset checksum does not match.")
        if saved is None or saved.title != "Synthetic Stage C vacancy":
            raise StageCFixtureError("Synthetic saved vacancy is missing or changed.")
        if source is None or source.external_id != "stage-c-job-1":
            raise StageCFixtureError("Synthetic saved-vacancy source is missing or changed.")
        if tracker is None or tracker.state != "preparing" or tracker.revision != 2:
            raise StageCFixtureError("Synthetic JOB tracker is missing or changed.")
        if (
            event is None
            or event.from_state != "saved"
            or event.to_state != "preparing"
            or event.event_revision != 1
        ):
            raise StageCFixtureError("Synthetic JOB transition event is missing or changed.")
        if (
            consent is None
            or consent.status != "withdrawn"
            or consent.provider != "none"
            or consent.scope != "stage_c_synthetic"
        ):
            raise StageCFixtureError("Synthetic legal-consent record is missing or unsafe.")

    schema = _schema_report(runtime)
    fixture_payload = {
        "user_id": _USER_ID,
        "draft_id": _DRAFT_ID,
        "asset_id": _ASSET_ID,
        "asset_sha256": _sha256_bytes(_ASSET_BYTES),
        "saved_vacancy_id": _SAVED_ID,
        "tracker_state": "preparing",
        "consent_status": "withdrawn",
    }
    return {
        "ok": True,
        "database_revision": revision,
        "fixture_digest": _sha256_text(_canonical_json(fixture_payload)),
        "asset_sha256": _sha256_bytes(_ASSET_BYTES),
        **schema,
    }


def _write_report(path: str | None, report: dict[str, object]) -> None:
    if not path:
        return
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        destination.chmod(0o600)
    except OSError:
        pass


def _compare_expected(path: str | None, report: dict[str, object]) -> None:
    if not path:
        return
    expected = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("database_revision", "fixture_digest", "asset_sha256", "schema_digest"):
        if expected.get(key) != report.get(key):
            raise StageCFixtureError(f"Restore verification mismatch: {key}.")
    if expected.get("sequences") != report.get("sequences"):
        raise StageCFixtureError("Restore verification mismatch: sequences.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    seed = sub.add_parser("seed")
    seed.add_argument("--acknowledgement", required=True)
    seed.add_argument("--database-env", default="DATABASE_URL")
    seed.add_argument("--report")

    verify = sub.add_parser("verify")
    verify.add_argument("--database-env", default="DATABASE_URL")
    verify.add_argument("--expected-report")
    verify.add_argument("--report")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        database_url = _stage_c_url_from_env(args.database_env)
        runtime = create_database(database_url)
        try:
            if args.command == "seed":
                if args.acknowledgement != _ACK:
                    raise StageCFixtureError(
                        f"Refusing seed: acknowledgement must be {_ACK}."
                    )
                if make_url(database_url).database != "ai_career_agent":
                    raise StageCFixtureError(
                        "Synthetic seed may run only against the Stage C primary database."
                    )
                seed_fixture(runtime)
            report = verify_fixture(runtime)
            _compare_expected(getattr(args, "expected_report", None), report)
            _write_report(getattr(args, "report", None), report)
        finally:
            runtime.dispose()
    except (StageCFixtureError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
