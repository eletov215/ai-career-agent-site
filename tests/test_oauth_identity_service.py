from __future__ import annotations

import pytest
from sqlalchemy import select

from database import create_database, upgrade_database
from models import HeadHunterAccount, OAuthConnection, SuperJobAccount
from repositories import OAuthConnectionRepository, UserRepository
from services.oauth_identity import (
    OAuthIdentityOwnedByAnotherUser,
    OAuthIdentityService,
    OAuthProviderSlotOccupied,
    UnsupportedOAuthProvider,
)


def _runtime(tmp_path):
    url = f"sqlite:///{(tmp_path / 'oauth-identity.db').resolve().as_posix()}"
    upgrade_database(url)
    return create_database(url)


def _connect(
    service: OAuthIdentityService,
    *,
    user_id: str,
    provider: str = "headhunter",
    external_id: str = "external-1",
    access: str = "encrypted-access",
):
    return service.connect(
        user_id=user_id,
        provider=provider,
        external_user_id=external_id,
        display_name="Provider User",
        first_name="Provider",
        last_name="User",
        email="provider@example.test",
        access_token=access,
        refresh_token="encrypted-refresh",
        expires_at=9999,
        profile_json="{}",
    )


def test_unbound_identity_is_claimed_only_after_explicit_oauth_connect(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        users = UserRepository(runtime)
        repository = OAuthConnectionRepository(runtime)
        service = OAuthIdentityService(repository)
        user = users.create(email="claim@example.test", status="active")
        unbound = repository.upsert(
            provider="headhunter",
            external_user_id="hh-claim",
            access_token="old-encrypted-access",
            refresh_token="old-encrypted-refresh",
            profile_json="{}",
        )
        assert unbound.user_id is None

        result = _connect(
            service,
            user_id=user.id,
            provider="headhunter",
            external_id="hh-claim",
            access="new-encrypted-access",
        )
        assert result.outcome == "claimed"
        assert result.connection.id == unbound.id
        assert result.connection.user_id == user.id
        assert result.connection.access_token == "new-encrypted-access"
        assert service.get(user_id=user.id, provider="headhunter") == result.connection
    finally:
        runtime.dispose()


def test_same_owned_identity_refreshes_without_creating_duplicate(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        users = UserRepository(runtime)
        repository = OAuthConnectionRepository(runtime)
        service = OAuthIdentityService(repository)
        user = users.create(email="refresh@example.test", status="active")

        created = _connect(service, user_id=user.id, access="encrypted-one")
        refreshed = _connect(service, user_id=user.id, access="encrypted-two")

        assert created.outcome == "created"
        assert refreshed.outcome == "refreshed"
        assert refreshed.connection.id == created.connection.id
        assert refreshed.connection.access_token == "encrypted-two"
        with runtime.session() as session:
            assert len(session.scalars(select(OAuthConnection)).all()) == 1
    finally:
        runtime.dispose()


def test_foreign_identity_and_provider_slot_conflicts_do_not_overwrite(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        users = UserRepository(runtime)
        repository = OAuthConnectionRepository(runtime)
        service = OAuthIdentityService(repository)
        first = users.create(email="owner-one@example.test", status="active")
        second = users.create(email="owner-two@example.test", status="active")
        original = _connect(
            service,
            user_id=first.id,
            external_id="hh-owned",
            access="cipher-one",
        )

        with pytest.raises(OAuthIdentityOwnedByAnotherUser):
            _connect(
                service,
                user_id=second.id,
                external_id="hh-owned",
                access="cipher-two",
            )
        unchanged = repository.get("headhunter", "hh-owned")
        assert unchanged is not None
        assert unchanged.user_id == first.id
        assert unchanged.access_token == "cipher-one"

        with pytest.raises(OAuthProviderSlotOccupied):
            _connect(
                service,
                user_id=first.id,
                external_id="hh-other",
                access="cipher-three",
            )
        current = service.get(user_id=first.id, provider="headhunter")
        assert current is not None
        assert current.id == original.connection.id
        assert repository.get("headhunter", "hh-other") is None
    finally:
        runtime.dispose()


def test_owner_scoped_list_and_disconnect_clear_unified_and_legacy_data(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        users = UserRepository(runtime)
        repository = OAuthConnectionRepository(runtime)
        service = OAuthIdentityService(repository)
        owner = users.create(email="disconnect-owner@example.test", status="active")
        other = users.create(email="disconnect-other@example.test", status="active")

        hh = _connect(
            service,
            user_id=owner.id,
            provider="headhunter",
            external_id="hh-disconnect",
            access="cipher-hh",
        )
        sj = _connect(
            service,
            user_id=owner.id,
            provider="superjob",
            external_id="707",
            access="cipher-sj",
        )
        _connect(
            service,
            user_id=other.id,
            provider="headhunter",
            external_id="hh-other-owner",
            access="cipher-other",
        )

        assert {item.provider for item in service.list(user_id=owner.id)} == {
            "headhunter",
            "superjob",
        }
        # An unrelated user cannot delete or even select the owner's provider row.
        assert service.disconnect(user_id=other.id, provider="superjob") is None
        assert service.get(user_id=owner.id, provider="superjob") is not None

        removed_sj = service.disconnect(user_id=owner.id, provider="superjob")
        removed_hh = service.disconnect(user_id=owner.id, provider="headhunter")
        assert removed_sj is not None and removed_sj.id == sj.connection.id
        assert removed_hh is not None and removed_hh.id == hh.connection.id
        assert service.list(user_id=owner.id) == []

        with runtime.session() as session:
            assert session.scalar(
                select(OAuthConnection).where(OAuthConnection.id == sj.connection.id)
            ) is None
            assert session.scalar(
                select(OAuthConnection).where(OAuthConnection.id == hh.connection.id)
            ) is None
            assert session.get(SuperJobAccount, 707) is None
            assert session.get(HeadHunterAccount, "hh-disconnect") is None
    finally:
        runtime.dispose()


def test_unsupported_provider_is_rejected_before_repository_access(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        service = OAuthIdentityService(OAuthConnectionRepository(runtime))
        with pytest.raises(UnsupportedOAuthProvider):
            service.get(user_id="user", provider="unknown")
    finally:
        runtime.dispose()
