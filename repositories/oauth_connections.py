"""Repository for unified OAuth connections."""

from __future__ import annotations

import time
import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain import OAuthConnectionRecord
from models import (
    HeadHunterAccount,
    OAuthConnection,
    SuperJobAccount,
)

from .base import RepositoryBase

class OAuthConnectionOwnershipError(RuntimeError):
    """The external provider identity belongs to another first-party user."""


class OAuthProviderAlreadyConnectedError(RuntimeError):
    """The first-party user already owns another identity for this provider."""


class OAuthConnectionRepository(RepositoryBase):
    """Persist provider connections independently of Flask routes.

    During DATA-002 writes are mirrored to the provider-specific legacy tables.
    This keeps OAuth credentials current for a controlled rollback after the
    database schema is restored to the DATA-001 revision.  AUTH-002 can remove
    the compatibility write after first-party users own every connection.
    """

    @staticmethod
    def _record(row: OAuthConnection) -> OAuthConnectionRecord:
        return OAuthConnectionRecord(
            id=row.id,
            provider=row.provider,
            external_user_id=row.external_user_id,
            user_id=row.user_id,
            display_name=row.display_name,
            first_name=row.first_name,
            last_name=row.last_name,
            email=row.email,
            access_token=row.access_token,
            refresh_token=row.refresh_token,
            expires_at=row.expires_at,
            profile_json=row.profile_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _normalize_identity(provider: str, external_user_id: str) -> tuple[str, str]:
        provider_value = str(provider or "").strip().casefold()
        external_value = str(external_user_id or "").strip()
        if not provider_value or not external_value:
            raise ValueError("provider и external_user_id обязательны")
        return provider_value, external_value

    @staticmethod
    def _delete_legacy_row(session: Session, row: OAuthConnection) -> None:
        """Delete rollback mirrors when an owner explicitly disconnects."""

        if row.provider == "superjob":
            try:
                legacy_user_id = int(row.external_user_id)
            except (TypeError, ValueError):
                return
            session.execute(
                delete(SuperJobAccount).where(
                    SuperJobAccount.user_id == legacy_user_id
                )
            )
            return

        if row.provider == "headhunter":
            session.execute(
                delete(HeadHunterAccount).where(
                    HeadHunterAccount.user_id == row.external_user_id
                )
            )

    @staticmethod
    def _sync_legacy_row(session: Session, row: OAuthConnection) -> None:
        """Mirror known providers to DATA-001 tables for rollback safety."""

        if row.provider == "superjob":
            try:
                legacy_user_id = int(row.external_user_id)
            except (TypeError, ValueError):
                # Test/future identities may not be numeric.  The unified table
                # remains authoritative and no invalid legacy row is created.
                return
            legacy = session.get(SuperJobAccount, legacy_user_id)
            if legacy is None:
                legacy = SuperJobAccount(
                    user_id=legacy_user_id,
                    name=row.display_name or "Пользователь SuperJob",
                    email=row.email,
                    access_token=row.access_token,
                    refresh_token=row.refresh_token,
                    expires_at=row.expires_at,
                    profile_json=row.profile_json,
                    updated_at=row.updated_at,
                )
                session.add(legacy)
            else:
                legacy.name = row.display_name or "Пользователь SuperJob"
                legacy.email = row.email
                legacy.access_token = row.access_token
                legacy.refresh_token = row.refresh_token
                legacy.expires_at = row.expires_at
                legacy.profile_json = row.profile_json
                legacy.updated_at = row.updated_at
            return

        if row.provider == "headhunter":
            legacy = session.get(HeadHunterAccount, row.external_user_id)
            if legacy is None:
                legacy = HeadHunterAccount(
                    user_id=row.external_user_id,
                    first_name=row.first_name,
                    last_name=row.last_name,
                    email=row.email,
                    access_token=row.access_token,
                    refresh_token=row.refresh_token,
                    expires_at=row.expires_at,
                    profile_json=row.profile_json,
                    updated_at=row.updated_at,
                )
                session.add(legacy)
            else:
                legacy.first_name = row.first_name
                legacy.last_name = row.last_name
                legacy.email = row.email
                legacy.access_token = row.access_token
                legacy.refresh_token = row.refresh_token
                legacy.expires_at = row.expires_at
                legacy.profile_json = row.profile_json
                legacy.updated_at = row.updated_at

    def get(self, provider: str, external_user_id: str) -> OAuthConnectionRecord | None:
        try:
            provider_value, external_value = self._normalize_identity(
                provider, external_user_id
            )
        except ValueError:
            return None
        with self.session() as session:
            row = session.scalar(
                select(OAuthConnection).where(
                    OAuthConnection.provider == provider_value,
                    OAuthConnection.external_user_id == external_value,
                )
            )
            return self._record(row) if row else None

    def upsert(
        self,
        *,
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
        user_id: str | None = None,
        updated_at: int | None = None,
    ) -> OAuthConnectionRecord:
        provider_value, external_value = self._normalize_identity(
            provider, external_user_id
        )
        if not access_token:
            raise ValueError("access_token обязателен")
        now = int(updated_at or time.time())
        with self.session() as session:
            row = session.scalar(
                select(OAuthConnection).where(
                    OAuthConnection.provider == provider_value,
                    OAuthConnection.external_user_id == external_value,
                )
            )
            if row is None:
                row = OAuthConnection(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    provider=provider_value,
                    external_user_id=external_value,
                    display_name=display_name,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    profile_json=profile_json,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                if user_id is not None:
                    row.user_id = user_id
                row.display_name = display_name
                row.first_name = first_name
                row.last_name = last_name
                row.email = email
                row.access_token = access_token
                if refresh_token:
                    row.refresh_token = refresh_token
                row.expires_at = expires_at
                row.profile_json = profile_json
                row.updated_at = now

            self._sync_legacy_row(session, row)
            session.commit()
            return self._record(row)

    def get_for_user(
        self,
        *,
        user_id: str,
        provider: str,
    ) -> OAuthConnectionRecord | None:
        user_value = str(user_id or "").strip()
        provider_value = str(provider or "").strip().casefold()
        if not user_value or not provider_value:
            return None
        with self.session() as session:
            row = session.scalar(
                select(OAuthConnection).where(
                    OAuthConnection.user_id == user_value,
                    OAuthConnection.provider == provider_value,
                )
            )
            return self._record(row) if row else None

    def list_for_user(self, user_id: str) -> list[OAuthConnectionRecord]:
        user_value = str(user_id or "").strip()
        if not user_value:
            return []
        with self.session() as session:
            rows = session.scalars(
                select(OAuthConnection)
                .where(OAuthConnection.user_id == user_value)
                .order_by(OAuthConnection.provider.asc(), OAuthConnection.created_at.asc())
            ).all()
            return [self._record(row) for row in rows]

    def claim_for_user(
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
    ) -> tuple[OAuthConnectionRecord, str]:
        """Atomically claim or refresh one provider identity for one user.

        Existing unbound rows are claimable only after the provider callback
        proves control of the same external identity. Rows owned by another
        user and a second identity for the same provider are never overwritten.
        """

        user_value = str(user_id or "").strip()
        if not user_value:
            raise ValueError("user_id обязателен")
        provider_value, external_value = self._normalize_identity(
            provider, external_user_id
        )
        if not access_token:
            raise ValueError("access_token обязателен")
        now = int(updated_at or time.time())

        with self.session() as session:
            try:
                with session.begin():
                    external_row = session.scalar(
                        select(OAuthConnection)
                        .where(
                            OAuthConnection.provider == provider_value,
                            OAuthConnection.external_user_id == external_value,
                        )
                        .with_for_update()
                    )
                    user_provider_row = session.scalar(
                        select(OAuthConnection)
                        .where(
                            OAuthConnection.user_id == user_value,
                            OAuthConnection.provider == provider_value,
                        )
                        .with_for_update()
                    )

                    if (
                        external_row is not None
                        and external_row.user_id is not None
                        and external_row.user_id != user_value
                    ):
                        raise OAuthConnectionOwnershipError(
                            "OAuth identity already belongs to another user"
                        )

                    if (
                        user_provider_row is not None
                        and user_provider_row.external_user_id != external_value
                    ):
                        raise OAuthProviderAlreadyConnectedError(
                            "User already owns another identity for this provider"
                        )

                    row = external_row or user_provider_row
                    if row is None:
                        row = OAuthConnection(
                            id=str(uuid.uuid4()),
                            user_id=user_value,
                            provider=provider_value,
                            external_user_id=external_value,
                            display_name=display_name,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            access_token=access_token,
                            refresh_token=refresh_token,
                            expires_at=expires_at,
                            profile_json=profile_json,
                            created_at=now,
                            updated_at=now,
                        )
                        session.add(row)
                        outcome = "created"
                    else:
                        outcome = "claimed" if row.user_id is None else "refreshed"
                        row.user_id = user_value
                        row.display_name = display_name
                        row.first_name = first_name
                        row.last_name = last_name
                        row.email = email
                        row.access_token = access_token
                        if refresh_token:
                            row.refresh_token = refresh_token
                        row.expires_at = expires_at
                        row.profile_json = profile_json
                        row.updated_at = now

                    self._sync_legacy_row(session, row)
                    session.flush()
                    result = self._record(row)
                return result, outcome
            except IntegrityError as exc:
                session.rollback()
                raise OAuthProviderAlreadyConnectedError(
                    "OAuth identity uniqueness conflict"
                ) from exc

    def bind_to_user(
        self,
        *,
        provider: str,
        external_user_id: str,
        user_id: str,
    ) -> OAuthConnectionRecord:
        """Compatibility binding with AUTH-002 ownership checks."""

        provider_value, external_value = self._normalize_identity(
            provider, external_user_id
        )
        user_value = str(user_id or "").strip()
        if not user_value:
            raise ValueError("user_id обязателен")
        with self.session() as session:
            try:
                with session.begin():
                    row = session.scalar(
                        select(OAuthConnection)
                        .where(
                            OAuthConnection.provider == provider_value,
                            OAuthConnection.external_user_id == external_value,
                        )
                        .with_for_update()
                    )
                    if row is None:
                        raise LookupError("OAuth connection not found")
                    if row.user_id not in {None, user_value}:
                        raise OAuthConnectionOwnershipError(
                            "OAuth identity already belongs to another user"
                        )
                    occupied = session.scalar(
                        select(OAuthConnection)
                        .where(
                            OAuthConnection.user_id == user_value,
                            OAuthConnection.provider == provider_value,
                            OAuthConnection.id != row.id,
                        )
                        .with_for_update()
                    )
                    if occupied is not None:
                        raise OAuthProviderAlreadyConnectedError(
                            "User already owns another identity for this provider"
                        )
                    row.user_id = user_value
                    row.updated_at = int(time.time())
                    session.flush()
                    result = self._record(row)
                return result
            except IntegrityError as exc:
                session.rollback()
                raise OAuthProviderAlreadyConnectedError(
                    "OAuth identity uniqueness conflict"
                ) from exc

    def delete_for_user(
        self,
        *,
        user_id: str,
        provider: str,
    ) -> OAuthConnectionRecord | None:
        user_value = str(user_id or "").strip()
        provider_value = str(provider or "").strip().casefold()
        if not user_value or not provider_value:
            return None
        with self.session() as session:
            with session.begin():
                row = session.scalar(
                    select(OAuthConnection)
                    .where(
                        OAuthConnection.user_id == user_value,
                        OAuthConnection.provider == provider_value,
                    )
                    .with_for_update()
                )
                if row is None:
                    return None
                result = self._record(row)
                self._delete_legacy_row(session, row)
                session.delete(row)
            return result
