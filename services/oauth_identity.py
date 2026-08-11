"""AUTH-002 ownership service for external OAuth identities.

The provider adapters and token exchange remain in the web integration layer,
while this service owns the application-level rules that bind one verified
provider identity to exactly one first-party user.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain import OAuthConnectionRecord
from repositories.oauth_connections import (
    OAuthConnectionOwnershipError,
    OAuthProviderAlreadyConnectedError,
    OAuthConnectionRepository,
)


SUPPORTED_OAUTH_PROVIDERS = frozenset({"headhunter", "superjob"})


class OAuthIdentityError(RuntimeError):
    """Base class for safe AUTH-002 ownership failures."""

    code = "oauth_identity_error"
    public_message = "Не удалось изменить подключение. Повторите попытку позже."


class OAuthIdentityOwnedByAnotherUser(OAuthIdentityError):
    code = "identity_owned_by_another_user"
    public_message = (
        "Этот аккаунт площадки уже привязан к другому аккаунту AI Career Agent."
    )


class OAuthProviderSlotOccupied(OAuthIdentityError):
    code = "provider_slot_occupied"
    public_message = (
        "К вашему аккаунту уже подключён другой аккаунт этой площадки. "
        "Сначала отключите текущее подключение."
    )


class UnsupportedOAuthProvider(OAuthIdentityError):
    code = "unsupported_provider"
    public_message = "Эта площадка пока не поддерживается."


@dataclass(frozen=True, slots=True)
class OAuthIdentityResult:
    connection: OAuthConnectionRecord
    outcome: str


class OAuthIdentityService:
    """Apply ownership, uniqueness, and disconnect rules around repositories."""

    def __init__(self, repository: OAuthConnectionRepository) -> None:
        self.repository = repository

    @staticmethod
    def normalize_provider(provider: str) -> str:
        value = str(provider or "").strip().casefold()
        if value not in SUPPORTED_OAUTH_PROVIDERS:
            raise UnsupportedOAuthProvider()
        return value

    def connect(
        self,
        *,
        user_id: str,
        provider: str,
        external_user_id: str,
        access_token: str,
        profile_json: str,
        display_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        refresh_token: str | None = None,
        expires_at: int | None = None,
        updated_at: int | None = None,
    ) -> OAuthIdentityResult:
        provider_value = self.normalize_provider(provider)
        try:
            connection, outcome = self.repository.claim_for_user(
                user_id=user_id,
                provider=provider_value,
                external_user_id=external_user_id,
                access_token=access_token,
                profile_json=profile_json,
                display_name=display_name,
                first_name=first_name,
                last_name=last_name,
                email=email,
                refresh_token=refresh_token,
                expires_at=expires_at,
                updated_at=updated_at,
            )
        except OAuthConnectionOwnershipError as exc:
            raise OAuthIdentityOwnedByAnotherUser() from exc
        except OAuthProviderAlreadyConnectedError as exc:
            raise OAuthProviderSlotOccupied() from exc
        return OAuthIdentityResult(connection=connection, outcome=outcome)

    def get(self, *, user_id: str, provider: str) -> OAuthConnectionRecord | None:
        return self.repository.get_for_user(
            user_id=user_id,
            provider=self.normalize_provider(provider),
        )

    def list(self, *, user_id: str) -> list[OAuthConnectionRecord]:
        return self.repository.list_for_user(user_id)

    def disconnect(
        self,
        *,
        user_id: str,
        provider: str,
    ) -> OAuthConnectionRecord | None:
        return self.repository.delete_for_user(
            user_id=user_id,
            provider=self.normalize_provider(provider),
        )
