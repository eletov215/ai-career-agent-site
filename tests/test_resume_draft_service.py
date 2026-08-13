from __future__ import annotations

import base64
import time
import uuid

import pytest

from database import create_database, upgrade_database
from models import User
from repositories.resume_drafts import ResumeDraftNotFoundError, ResumeDraftRepository
from services.resume_drafts import (
    ResumeDraftConflictError,
    ResumeDraftService,
    ResumeDraftValidationError,
)


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _user(email: str) -> User:
    now = int(time.time())
    return User(
        id=str(uuid.uuid4()),
        email=email,
        normalized_email=email.casefold(),
        display_name="Resume Draft Owner",
        status="active",
        email_verified_at=now,
        password_hash=None,
        password_changed_at=None,
        last_login_at=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture()
def draft_context(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'resume-drafts.db').resolve().as_posix()}"
    upgrade_database(database_url)
    runtime = create_database(database_url)
    first = _user("resume-owner-a@example.test")
    second = _user("resume-owner-b@example.test")
    with runtime.session() as session:
        session.add_all([first, second])
        session.commit()
    service = ResumeDraftService(ResumeDraftRepository(runtime))
    try:
        yield runtime, service, first, second
    finally:
        runtime.dispose()


def _state(*, name: str = "User", role: str = "", photo_asset_id=None):
    answers = {"name": name}
    if role:
        answers["role"] = role
    return {
        "schemaVersion": 1,
        "index": 2 if role else 1,
        "answers": answers,
        "messages": [],
        "photoAssetId": photo_asset_id,
        "universityLogoAssetId": None,
        "universityLogoFor": "",
        "universityResolvedName": "",
    }


def test_server_draft_autosave_noop_conflict_checkpoint_and_restore(draft_context):
    _runtime, service, owner, _other = draft_context
    draft = service.create(user_id=owner.id, display_name=owner.display_name)
    assert draft.revision == 1
    assert draft.state["answers"]["name"] == owner.display_name

    saved = service.save(
        user_id=owner.id,
        draft_id=draft.id,
        expected_revision=1,
        state=_state(name="Resume Draft Owner", role="Backend Engineer"),
    )
    assert saved.changed is True
    assert saved.draft.revision == 2
    assert saved.draft.completion_percent == 25

    noop = service.save(
        user_id=owner.id,
        draft_id=draft.id,
        expected_revision=2,
        state=_state(name="Resume Draft Owner", role="Backend Engineer"),
    )
    assert noop.changed is False
    assert noop.draft.revision == 2

    with pytest.raises(ResumeDraftConflictError):
        service.save(
            user_id=owner.id,
            draft_id=draft.id,
            expected_revision=1,
            state=_state(name="Resume Draft Owner", role="Stale overwrite"),
        )

    checkpoint_1 = service.checkpoint(
        user_id=owner.id,
        draft_id=draft.id,
        expected_revision=2,
    )
    assert checkpoint_1.created is True
    assert checkpoint_1.version.version == 1
    same_checkpoint = service.checkpoint(
        user_id=owner.id,
        draft_id=draft.id,
        expected_revision=2,
    )
    assert same_checkpoint.created is False
    assert same_checkpoint.version.version == 1

    saved_again = service.save(
        user_id=owner.id,
        draft_id=draft.id,
        expected_revision=2,
        state=_state(name="Resume Draft Owner", role="Product Engineer"),
    )
    checkpoint_2 = service.checkpoint(
        user_id=owner.id,
        draft_id=draft.id,
        expected_revision=saved_again.draft.revision,
    )
    assert checkpoint_2.version.version == 2

    restored_draft, restored_version = service.restore(
        user_id=owner.id,
        draft_id=draft.id,
        version=1,
        expected_revision=saved_again.draft.revision,
    )
    assert restored_draft.state["answers"]["role"] == "Backend Engineer"
    assert restored_draft.revision == saved_again.draft.revision + 1
    assert restored_version.version == 3
    assert restored_version.reason == "restore"
    assert restored_version.restored_from_version == 1


def test_assets_are_durable_owner_and_draft_scoped(draft_context):
    _runtime, service, owner, other = draft_context
    first = service.create(user_id=owner.id, title="First")
    second = service.create(user_id=owner.id, title="Second")

    asset = service.store_asset(
        user_id=owner.id,
        draft_id=first.id,
        kind="photo",
        content_type="image/png",
        data=PNG_1X1,
    )
    assert asset.draft_id == first.id
    assert service.get_asset(user_id=owner.id, asset_id=asset.id) is not None
    assert service.get_asset(user_id=other.id, asset_id=asset.id) is None

    state = _state(photo_asset_id=asset.id)
    saved = service.save(
        user_id=owner.id,
        draft_id=first.id,
        expected_revision=first.revision,
        state=state,
    )
    assert saved.draft.state["photoAssetId"] == asset.id

    with pytest.raises(ResumeDraftValidationError, match="не принадлежит этому черновику"):
        service.save(
            user_id=owner.id,
            draft_id=second.id,
            expected_revision=second.revision,
            state=state,
        )

    with pytest.raises(ResumeDraftValidationError):
        service.store_asset(
            user_id=owner.id,
            draft_id=first.id,
            kind="photo",
            content_type="image/svg+xml",
            data=b"<svg/>",
        )


def test_export_metadata_is_bound_to_immutable_version(draft_context):
    _runtime, service, owner, _other = draft_context
    draft = service.create(user_id=owner.id)
    saved = service.save(
        user_id=owner.id,
        draft_id=draft.id,
        expected_revision=draft.revision,
        state=_state(role="Data Engineer"),
    )
    result = service.record_export(
        user_id=owner.id,
        draft_id=draft.id,
        expected_revision=saved.draft.revision,
        page_count=2,
        byte_size=42_000,
        pdf_sha256="a" * 64,
        file_name="resume.pdf",
    )
    assert result.version_created is True
    assert result.version.reason == "export"
    assert result.export.version == result.version.version == 1
    assert result.export.page_count == 2
    assert result.export.pdf_sha256 == "a" * 64

    repeated = service.record_export(
        user_id=owner.id,
        draft_id=draft.id,
        expected_revision=saved.draft.revision,
        page_count=2,
        byte_size=42_001,
        pdf_sha256="b" * 64,
        file_name="resume-2.pdf",
    )
    assert repeated.version_created is False
    assert repeated.version.version == 1
    assert repeated.export.version == 1


def test_owner_isolation_hides_drafts_and_versions(draft_context):
    _runtime, service, owner, other = draft_context
    draft = service.create(user_id=owner.id)
    service.checkpoint(
        user_id=owner.id,
        draft_id=draft.id,
        expected_revision=draft.revision,
    )

    assert service.get(user_id=other.id, draft_id=draft.id) is None
    assert service.get_version(
        user_id=other.id,
        draft_id=draft.id,
        version=1,
    ) is None
    with pytest.raises(ResumeDraftNotFoundError):
        service.save(
            user_id=other.id,
            draft_id=draft.id,
            expected_revision=1,
            state=_state(role="Foreign overwrite"),
        )


def test_university_logo_accepts_valid_gif_but_photo_remains_jpg_png_webp(draft_context):
    _runtime, service, owner, _other = draft_context
    draft = service.create(user_id=owner.id)
    gif = b"GIF89a" + b"\x00" * 64
    logo = service.store_asset(
        user_id=owner.id,
        draft_id=draft.id,
        kind="university_logo",
        content_type="image/gif",
        data=gif,
    )
    assert logo.content_type == "image/gif"
    with pytest.raises(ResumeDraftValidationError, match="фотографии"):
        service.store_asset(
            user_id=owner.id,
            draft_id=draft.id,
            kind="photo",
            content_type="image/gif",
            data=gif,
        )
