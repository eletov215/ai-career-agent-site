from __future__ import annotations

import json
import time
import uuid
import zipfile
from dataclasses import replace
from io import BytesIO

from sqlalchemy import select

from config import load_settings
from database import create_database, upgrade_database
from models import (
    AuthSession,
    AuthToken,
    HeadHunterAccount,
    OAuthConnection,
    PrivacyAuditEvent,
    ResumeAsset,
    ResumeDraft,
    ResumeExport,
    ResumeVersion,
    SuperJobAccount,
    User,
)
from repositories.privacy import PrivacyRepository
from services.privacy import PrivacyService


def _settings(tmp_path):
    settings = load_settings({"APP_ENV": "test", "DATA_DIR": str(tmp_path)})
    return replace(
        settings,
        privacy_pending_account_retention_days=30,
        privacy_auth_artifact_retention_days=30,
        privacy_audit_retention_days=180,
    )


def test_export_is_readable_and_omits_authentication_secrets(tmp_path):
    settings = _settings(tmp_path)
    database_url = f"sqlite:///{(tmp_path / 'export.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    now = int(time.time())
    user_id = str(uuid.uuid4())
    with runtime.session() as session:
        session.add(
            User(
                id=user_id,
                email="privacy-export@example.test",
                normalized_email="privacy-export@example.test",
                display_name="Privacy Export",
                status="active",
                email_verified_at=now,
                password_hash="DO-NOT-EXPORT-PASSWORD-HASH",
                password_changed_at=now,
                last_login_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            AuthSession(
                id=str(uuid.uuid4()),
                user_id=user_id,
                token_hash="DO-NOT-EXPORT-SESSION-HASH",
                created_at=now,
                last_seen_at=now,
                expires_at=now + 3600,
                revoked_at=None,
                revoke_reason=None,
                user_agent_hash="DO-NOT-EXPORT-UA-HASH",
            )
        )
        session.add(
            AuthToken(
                id=str(uuid.uuid4()),
                user_id=user_id,
                purpose="reset_password",
                token_hash="DO-NOT-EXPORT-TOKEN-HASH",
                created_at=now,
                expires_at=now + 3600,
                consumed_at=None,
                consumed_reason=None,
            )
        )
        session.commit()

    service = PrivacyService(PrivacyRepository(runtime), settings)
    artifact = service.export_user_data(user_id, expected_password_hash="DO-NOT-EXPORT-PASSWORD-HASH", now=now)
    with zipfile.ZipFile(BytesIO(artifact.content)) as archive:
        assert {"manifest.json", "data.json"}.issubset(set(archive.namelist()))
        manifest = json.loads(archive.read("manifest.json"))
        data = json.loads(archive.read("data.json"))
    assert data["account"]["email"] == "privacy-export@example.test"
    assert data["authentication"]["sessions"]
    assert data["authentication"]["one_time_tokens"]
    assert manifest["export_schema_version"] == 1
    payload = artifact.content
    for forbidden in (
        b"DO-NOT-EXPORT-PASSWORD-HASH",
        b"DO-NOT-EXPORT-SESSION-HASH",
        b"DO-NOT-EXPORT-TOKEN-HASH",
        b"DO-NOT-EXPORT-UA-HASH",
    ):
        assert forbidden not in payload
    with runtime.session() as session:
        audit = session.scalar(
            select(PrivacyAuditEvent).where(
                PrivacyAuditEvent.event_type == "data_exported"
            )
        )
        assert audit is not None
        assert "privacy-export" not in audit.counts_json
    runtime.dispose()


def test_retention_cleanup_removes_stale_pending_and_auth_artifacts_only(tmp_path):
    settings = _settings(tmp_path)
    database_url = f"sqlite:///{(tmp_path / 'cleanup.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    now = 2_000_000_000
    old = now - 60 * 24 * 60 * 60
    recent = now - 2 * 24 * 60 * 60
    stale_pending_id = str(uuid.uuid4())
    active_id = str(uuid.uuid4())
    with runtime.session() as session:
        session.add_all(
            [
                User(
                    id=stale_pending_id,
                    email="stale-pending@example.test",
                    normalized_email="stale-pending@example.test",
                    display_name=None,
                    status="pending",
                    email_verified_at=None,
                    password_hash="hash",
                    password_changed_at=old,
                    last_login_at=None,
                    created_at=old,
                    updated_at=old,
                ),
                User(
                    id=active_id,
                    email="active@example.test",
                    normalized_email="active@example.test",
                    display_name=None,
                    status="active",
                    email_verified_at=recent,
                    password_hash="hash",
                    password_changed_at=recent,
                    last_login_at=recent,
                    created_at=recent,
                    updated_at=recent,
                ),
            ]
        )
        session.add_all(
            [
                AuthSession(
                    id=str(uuid.uuid4()),
                    user_id=active_id,
                    token_hash="old-session",
                    created_at=old,
                    last_seen_at=old,
                    expires_at=old,
                    revoked_at=old,
                    revoke_reason="logout",
                    user_agent_hash=None,
                ),
                AuthSession(
                    id=str(uuid.uuid4()),
                    user_id=active_id,
                    token_hash="recent-session",
                    created_at=recent,
                    last_seen_at=recent,
                    expires_at=now + 3600,
                    revoked_at=None,
                    revoke_reason=None,
                    user_agent_hash=None,
                ),
                AuthToken(
                    id=str(uuid.uuid4()),
                    user_id=active_id,
                    purpose="reset_password",
                    token_hash="old-token",
                    created_at=old,
                    expires_at=old,
                    consumed_at=old,
                    consumed_reason="used",
                ),
                AuthToken(
                    id=str(uuid.uuid4()),
                    user_id=active_id,
                    purpose="reset_password",
                    token_hash="recent-token",
                    created_at=recent,
                    expires_at=now + 3600,
                    consumed_at=None,
                    consumed_reason=None,
                ),
            ]
        )
        session.commit()

    counts = PrivacyService(PrivacyRepository(runtime), settings).run_retention_cleanup(now=now)
    assert counts["pending_accounts"] == 1
    assert counts["auth_sessions"] == 1
    assert counts["auth_tokens"] == 1
    with runtime.session() as session:
        assert session.get(User, stale_pending_id) is None
        assert session.get(User, active_id) is not None
        assert session.scalar(select(AuthSession).where(AuthSession.token_hash == "recent-session")) is not None
        assert session.scalar(select(AuthToken).where(AuthToken.token_hash == "recent-token")) is not None
        audit = session.scalar(
            select(PrivacyAuditEvent).where(
                PrivacyAuditEvent.event_type == "retention_cleanup"
            )
        )
        assert audit is not None
    runtime.dispose()


def test_export_includes_owned_resume_asset_and_delete_cascades_resume_and_provider_data(tmp_path):
    settings = _settings(tmp_path)
    database_url = f"sqlite:///{(tmp_path / 'cascade.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    now = 2_000_000_000
    user_id = str(uuid.uuid4())
    draft_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    asset_id = str(uuid.uuid4())
    export_id = str(uuid.uuid4())
    hh_external = "771199"
    sj_external = "882200"
    photo_bytes = b"privacy-owned-photo-bytes"
    state = json.dumps(
        {
            "schemaVersion": 1,
            "index": 0,
            "answers": {
                "name": "Owner",
                "role": "Engineer",
                "experience": "",
                "achievements": "",
                "skills": "Python",
                "education": "",
                "contacts": "owner@example.test",
                "goal": "",
            },
            "messages": [],
            "photoAssetId": asset_id,
            "universityLogoAssetId": None,
            "universityLogoFor": "",
            "universityResolvedName": "",
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    with runtime.session() as session:
        session.add(
            User(
                id=user_id,
                email="privacy-cascade@example.test",
                normalized_email="privacy-cascade@example.test",
                display_name="Privacy Cascade",
                status="active",
                email_verified_at=now,
                password_hash="secret-password-hash",
                password_changed_at=now,
                last_login_at=now,
                created_at=now,
                updated_at=now,
            )
        )
        session.add_all(
            [
                OAuthConnection(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    provider="headhunter",
                    external_user_id=hh_external,
                    display_name="HH Owner",
                    first_name=None,
                    last_name=None,
                    email=None,
                    access_token="secret-hh-oauth-access",
                    refresh_token="secret-hh-oauth-refresh",
                    expires_at=now + 3600,
                    profile_json='{"city":"Minsk"}',
                    created_at=now,
                    updated_at=now,
                ),
                OAuthConnection(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    provider="superjob",
                    external_user_id=sj_external,
                    display_name="SJ Owner",
                    first_name=None,
                    last_name=None,
                    email=None,
                    access_token="secret-sj-oauth-access",
                    refresh_token="secret-sj-oauth-refresh",
                    expires_at=now + 3600,
                    profile_json='{"city":"Minsk"}',
                    created_at=now,
                    updated_at=now,
                ),
                HeadHunterAccount(
                    user_id=hh_external,
                    first_name="Legacy",
                    last_name="HH",
                    email=None,
                    access_token="legacy-hh-access",
                    refresh_token="legacy-hh-refresh",
                    expires_at=now + 3600,
                    profile_json="{}",
                    updated_at=now,
                ),
                SuperJobAccount(
                    user_id=int(sj_external),
                    name="Legacy SJ",
                    email=None,
                    access_token="legacy-sj-access",
                    refresh_token="legacy-sj-refresh",
                    expires_at=now + 3600,
                    profile_json="{}",
                    updated_at=now,
                ),
                ResumeDraft(
                    id=draft_id,
                    user_id=user_id,
                    schema_version=1,
                    revision=1,
                    title="Private resume",
                    state_json=state,
                    content_hash="a" * 64,
                    completion_percent=25,
                    profile_version=None,
                    created_at=now,
                    updated_at=now,
                ),
                ResumeVersion(
                    id=version_id,
                    draft_id=draft_id,
                    schema_version=1,
                    version=1,
                    draft_revision=1,
                    snapshot_json=state,
                    content_hash="a" * 64,
                    reason="export",
                    restored_from_version=None,
                    created_at=now,
                ),
                ResumeAsset(
                    id=asset_id,
                    draft_id=draft_id,
                    user_id=user_id,
                    kind="photo",
                    content_type="image/png",
                    byte_size=len(photo_bytes),
                    sha256="b" * 64,
                    data=photo_bytes,
                    created_at=now,
                ),
                ResumeExport(
                    id=export_id,
                    draft_id=draft_id,
                    version_id=version_id,
                    version=1,
                    page_count=1,
                    byte_size=1234,
                    pdf_sha256="c" * 64,
                    file_name="resume.pdf",
                    created_at=now,
                ),
            ]
        )
        session.commit()

    service = PrivacyService(PrivacyRepository(runtime), settings)
    artifact = service.export_user_data(user_id, expected_password_hash="secret-password-hash", now=now)
    with zipfile.ZipFile(BytesIO(artifact.content)) as archive:
        names = set(archive.namelist())
        data = json.loads(archive.read("data.json"))
        asset_path = f"assets/{draft_id}/photo-{asset_id}.png"
        assert asset_path in names
        assert archive.read(asset_path) == photo_bytes
    assert data["resume_drafts"][0]["id"] == draft_id
    assert data["resume_versions"][0]["id"] == version_id
    assert data["resume_exports"][0]["id"] == export_id
    assert data["resume_assets"][0]["id"] == asset_id
    for forbidden in (
        b"secret-password-hash",
        b"secret-hh-oauth-access",
        b"secret-hh-oauth-refresh",
        b"secret-sj-oauth-access",
        b"secret-sj-oauth-refresh",
        b"legacy-hh-access",
        b"legacy-sj-access",
    ):
        assert forbidden not in artifact.content

    counts = service.delete_account(user_id, expected_password_hash="secret-password-hash", now=now + 1)
    assert counts["oauth_connections"] == 2
    assert counts["resume_drafts"] == 1
    assert counts["resume_versions"] == 1
    assert counts["resume_assets"] == 1
    assert counts["resume_exports"] == 1
    with runtime.session() as session:
        assert session.get(User, user_id) is None
        assert session.get(ResumeDraft, draft_id) is None
        assert session.get(ResumeVersion, version_id) is None
        assert session.get(ResumeAsset, asset_id) is None
        assert session.get(ResumeExport, export_id) is None
        assert session.get(HeadHunterAccount, hh_external) is None
        assert session.get(SuperJobAccount, int(sj_external)) is None
        audit = session.scalar(
            select(PrivacyAuditEvent)
            .where(PrivacyAuditEvent.event_type == "account_deleted")
            .order_by(PrivacyAuditEvent.created_at.desc())
        )
        assert audit is not None
        assert user_id not in audit.counts_json
        assert "privacy-cascade" not in audit.counts_json
    runtime.dispose()



def test_export_rejects_changed_password_hash(tmp_path):
    from services.privacy import PrivacyReauthenticationRequiredError

    settings = _settings(tmp_path)
    database_url = f"sqlite:///{(tmp_path / 'reauth.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    now = 2_000_000_000
    user_id = str(uuid.uuid4())
    with runtime.session() as session:
        session.add(User(
            id=user_id,
            email="reauth@example.test",
            normalized_email="reauth@example.test",
            display_name=None,
            status="active",
            email_verified_at=now,
            password_hash="new-hash",
            password_changed_at=now,
            last_login_at=now,
            created_at=now,
            updated_at=now,
        ))
        session.commit()
    service = PrivacyService(PrivacyRepository(runtime), settings)
    import pytest
    with pytest.raises(PrivacyReauthenticationRequiredError):
        service.export_user_data(user_id, expected_password_hash="old-hash", now=now)
    runtime.dispose()


def test_retention_cleanup_deletes_only_unreferenced_old_resume_assets(tmp_path):
    settings = _settings(tmp_path)
    database_url = f"sqlite:///{(tmp_path / 'orphan-assets.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    now = 2_000_000_000
    old = now - 30 * 24 * 60 * 60
    user_id = str(uuid.uuid4())
    draft_id = str(uuid.uuid4())
    keep_id = str(uuid.uuid4())
    drop_id = str(uuid.uuid4())
    state = json.dumps({"photoAssetId": keep_id, "universityLogoAssetId": None})
    with runtime.session() as session:
        session.add(User(
            id=user_id,
            email="asset-cleanup@example.test",
            normalized_email="asset-cleanup@example.test",
            display_name=None,
            status="active",
            email_verified_at=now,
            password_hash="hash",
            password_changed_at=now,
            last_login_at=now,
            created_at=now,
            updated_at=now,
        ))
        session.add(ResumeDraft(
            id=draft_id,
            user_id=user_id,
            schema_version=1,
            revision=1,
            title="asset cleanup",
            state_json=state,
            content_hash="a" * 64,
            completion_percent=1,
            profile_version=None,
            created_at=old,
            updated_at=old,
        ))
        for asset_id in (keep_id, drop_id):
            session.add(ResumeAsset(
                id=asset_id,
                draft_id=draft_id,
                user_id=user_id,
                kind="photo",
                content_type="image/png",
                byte_size=4,
                sha256=("b" if asset_id == keep_id else "c") * 64,
                data=b"data",
                created_at=old,
            ))
        session.commit()
    counts = PrivacyService(PrivacyRepository(runtime), settings).run_retention_cleanup(now=now)
    assert counts["orphan_resume_assets"] == 1
    with runtime.session() as session:
        assert session.get(ResumeAsset, keep_id) is not None
        assert session.get(ResumeAsset, drop_id) is None
    runtime.dispose()


def test_export_fails_closed_on_cross_owner_asset_integrity(tmp_path):
    from services.privacy import PrivacyOwnershipIntegrityError

    settings = _settings(tmp_path)
    database_url = f"sqlite:///{(tmp_path / 'owner-integrity.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    now = 2_000_000_000
    owner_id = str(uuid.uuid4())
    foreign_id = str(uuid.uuid4())
    draft_id = str(uuid.uuid4())
    with runtime.session() as session:
        for uid, email in ((owner_id, "owner@example.test"), (foreign_id, "foreign@example.test")):
            session.add(User(
                id=uid,
                email=email,
                normalized_email=email,
                display_name=None,
                status="active",
                email_verified_at=now,
                password_hash="owner-hash" if uid == owner_id else "foreign-hash",
                password_changed_at=now,
                last_login_at=now,
                created_at=now,
                updated_at=now,
            ))
        session.add(ResumeDraft(
            id=draft_id,
            user_id=owner_id,
            schema_version=1,
            revision=1,
            title="owner draft",
            state_json="{}",
            content_hash="a" * 64,
            completion_percent=0,
            profile_version=None,
            created_at=now,
            updated_at=now,
        ))
        session.add(ResumeAsset(
            id=str(uuid.uuid4()),
            draft_id=draft_id,
            user_id=foreign_id,
            kind="photo",
            content_type="image/png",
            byte_size=4,
            sha256="d" * 64,
            data=b"data",
            created_at=now,
        ))
        session.commit()
    service = PrivacyService(PrivacyRepository(runtime), settings)
    import pytest
    with pytest.raises(PrivacyOwnershipIntegrityError):
        service.export_user_data(owner_id, expected_password_hash="owner-hash", now=now)
    runtime.dispose()
