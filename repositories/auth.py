"""Repository boundary for AUTH-001 users, sessions, and one-time tokens."""

from __future__ import annotations

import time
import uuid

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError

from domain import AuthSessionRecord, AuthTokenRecord, AuthUserRecord
from models import AuthSession, AuthToken, User

from .base import RepositoryBase


class AuthRepository(RepositoryBase):
    """Persist authentication state without exposing ORM objects to services."""

    @staticmethod
    def _user_record(row: User) -> AuthUserRecord:
        return AuthUserRecord(
            id=row.id,
            email=row.email or "",
            normalized_email=row.normalized_email or "",
            display_name=row.display_name,
            status=row.status,
            email_verified_at=row.email_verified_at,
            password_hash=row.password_hash,
            password_changed_at=row.password_changed_at,
            last_login_at=row.last_login_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _session_record(row: AuthSession) -> AuthSessionRecord:
        return AuthSessionRecord(
            id=row.id,
            user_id=row.user_id,
            token_hash=row.token_hash,
            created_at=row.created_at,
            last_seen_at=row.last_seen_at,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
            revoke_reason=row.revoke_reason,
            user_agent_hash=row.user_agent_hash,
        )

    @staticmethod
    def _token_record(row: AuthToken) -> AuthTokenRecord:
        return AuthTokenRecord(
            id=row.id,
            user_id=row.user_id,
            purpose=row.purpose,
            token_hash=row.token_hash,
            created_at=row.created_at,
            expires_at=row.expires_at,
            consumed_at=row.consumed_at,
            consumed_reason=row.consumed_reason,
        )

    def create_user(
        self,
        *,
        email: str,
        normalized_email: str,
        password_hash: str,
        display_name: str | None,
        status: str = "pending",
        now: int | None = None,
    ) -> AuthUserRecord | None:
        timestamp = int(now or time.time())
        row = User(
            id=str(uuid.uuid4()),
            email=email,
            normalized_email=normalized_email,
            display_name=display_name,
            status=status,
            email_verified_at=None,
            password_hash=password_hash,
            password_changed_at=timestamp,
            last_login_at=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        with self.session() as session:
            try:
                session.add(row)
                session.commit()
            except IntegrityError:
                session.rollback()
                return None
            return self._user_record(row)

    def get_user(self, user_id: str) -> AuthUserRecord | None:
        with self.session() as session:
            row = session.get(User, user_id)
            return self._user_record(row) if row else None

    def find_user_by_email(self, normalized_email: str) -> AuthUserRecord | None:
        if not normalized_email:
            return None
        with self.session() as session:
            row = session.scalar(
                select(User).where(User.normalized_email == normalized_email)
            )
            return self._user_record(row) if row else None

    def update_last_login(self, user_id: str, *, now: int | None = None) -> None:
        timestamp = int(now or time.time())
        with self.session() as session:
            session.execute(
                update(User)
                .where(User.id == user_id)
                .values(last_login_at=timestamp, updated_at=timestamp)
            )
            session.commit()

    def create_session(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: int,
        user_agent_hash: str | None,
        now: int | None = None,
    ) -> AuthSessionRecord:
        timestamp = int(now or time.time())
        row = AuthSession(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            created_at=timestamp,
            last_seen_at=timestamp,
            expires_at=expires_at,
            revoked_at=None,
            revoke_reason=None,
            user_agent_hash=user_agent_hash,
        )
        with self.session() as session:
            session.add(row)
            session.commit()
            return self._session_record(row)

    def get_active_session(
        self,
        token_hash: str,
        *,
        now: int | None = None,
    ) -> AuthSessionRecord | None:
        timestamp = int(now or time.time())
        with self.session() as session:
            row = session.scalar(
                select(AuthSession).where(
                    AuthSession.token_hash == token_hash,
                    AuthSession.revoked_at.is_(None),
                    AuthSession.expires_at > timestamp,
                )
            )
            return self._session_record(row) if row else None

    def touch_session(
        self,
        session_id: str,
        *,
        now: int | None = None,
        minimum_interval: int = 300,
    ) -> None:
        timestamp = int(now or time.time())
        with self.session() as session:
            session.execute(
                update(AuthSession)
                .where(
                    AuthSession.id == session_id,
                    AuthSession.revoked_at.is_(None),
                    AuthSession.last_seen_at <= timestamp - max(0, minimum_interval),
                )
                .values(last_seen_at=timestamp)
            )
            session.commit()

    def revoke_session_by_hash(
        self,
        token_hash: str,
        *,
        reason: str,
        now: int | None = None,
    ) -> int:
        timestamp = int(now or time.time())
        with self.session() as session:
            result = session.execute(
                update(AuthSession)
                .where(
                    AuthSession.token_hash == token_hash,
                    AuthSession.revoked_at.is_(None),
                )
                .values(revoked_at=timestamp, revoke_reason=reason[:64])
            )
            session.commit()
            return int(result.rowcount or 0)

    def revoke_session_by_id(
        self,
        *,
        user_id: str,
        session_id: str,
        reason: str,
        now: int | None = None,
    ) -> int:
        timestamp = int(now or time.time())
        with self.session() as session:
            result = session.execute(
                update(AuthSession)
                .where(
                    AuthSession.id == session_id,
                    AuthSession.user_id == user_id,
                    AuthSession.revoked_at.is_(None),
                )
                .values(revoked_at=timestamp, revoke_reason=reason[:64])
            )
            session.commit()
            return int(result.rowcount or 0)

    def revoke_all_sessions(
        self,
        user_id: str,
        *,
        reason: str,
        except_session_id: str | None = None,
        now: int | None = None,
    ) -> int:
        timestamp = int(now or time.time())
        conditions = [
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        ]
        if except_session_id:
            conditions.append(AuthSession.id != except_session_id)
        with self.session() as session:
            result = session.execute(
                update(AuthSession)
                .where(*conditions)
                .values(revoked_at=timestamp, revoke_reason=reason[:64])
            )
            session.commit()
            return int(result.rowcount or 0)

    def list_active_sessions(
        self,
        user_id: str,
        *,
        now: int | None = None,
    ) -> list[AuthSessionRecord]:
        timestamp = int(now or time.time())
        with self.session() as session:
            rows = session.scalars(
                select(AuthSession)
                .where(
                    AuthSession.user_id == user_id,
                    AuthSession.revoked_at.is_(None),
                    AuthSession.expires_at > timestamp,
                )
                .order_by(AuthSession.last_seen_at.desc(), AuthSession.created_at.desc())
            ).all()
            return [self._session_record(row) for row in rows]

    def issue_token(
        self,
        *,
        user_id: str,
        purpose: str,
        token_hash: str,
        expires_at: int,
        now: int | None = None,
    ) -> AuthTokenRecord:
        timestamp = int(now or time.time())
        with self.session() as session:
            session.execute(
                update(AuthToken)
                .where(
                    AuthToken.user_id == user_id,
                    AuthToken.purpose == purpose,
                    AuthToken.consumed_at.is_(None),
                )
                .values(consumed_at=timestamp, consumed_reason="superseded")
            )
            row = AuthToken(
                id=str(uuid.uuid4()),
                user_id=user_id,
                purpose=purpose,
                token_hash=token_hash,
                created_at=timestamp,
                expires_at=expires_at,
                consumed_at=None,
                consumed_reason=None,
            )
            session.add(row)
            session.commit()
            return self._token_record(row)

    def get_active_token(
        self,
        *,
        token_hash: str,
        purpose: str,
        now: int | None = None,
    ) -> AuthTokenRecord | None:
        timestamp = int(now or time.time())
        with self.session() as session:
            row = session.scalar(
                select(AuthToken).where(
                    AuthToken.token_hash == token_hash,
                    AuthToken.purpose == purpose,
                    AuthToken.consumed_at.is_(None),
                    AuthToken.expires_at > timestamp,
                )
            )
            return self._token_record(row) if row else None

    def verify_email_with_token(
        self,
        *,
        token_hash: str,
        purpose: str,
        now: int | None = None,
    ) -> AuthUserRecord | None:
        """Consume a verification token and activate its user atomically."""

        timestamp = int(now or time.time())
        with self.session() as session:
            with session.begin():
                token = session.scalar(
                    select(AuthToken)
                    .where(
                        AuthToken.token_hash == token_hash,
                        AuthToken.purpose == purpose,
                        AuthToken.consumed_at.is_(None),
                        AuthToken.expires_at > timestamp,
                    )
                    .with_for_update()
                )
                if token is None:
                    return None
                user = session.get(User, token.user_id)
                if user is None:
                    return None
                if user.status != "pending" or user.email_verified_at is not None:
                    token.consumed_at = timestamp
                    token.consumed_reason = "user_ineligible"
                    return None
                token.consumed_at = timestamp
                token.consumed_reason = "used"
                user.email_verified_at = timestamp
                user.status = "active"
                user.updated_at = timestamp
                session.execute(
                    update(AuthToken)
                    .where(
                        AuthToken.user_id == user.id,
                        AuthToken.purpose == purpose,
                        AuthToken.id != token.id,
                        AuthToken.consumed_at.is_(None),
                    )
                    .values(consumed_at=timestamp, consumed_reason="verified")
                )
            return self._user_record(user)

    def reset_password_with_token(
        self,
        *,
        token_hash: str,
        purpose: str,
        password_hash: str,
        now: int | None = None,
    ) -> AuthUserRecord | None:
        """Consume a reset token, update the password, and revoke sessions atomically."""

        timestamp = int(now or time.time())
        with self.session() as session:
            with session.begin():
                token = session.scalar(
                    select(AuthToken)
                    .where(
                        AuthToken.token_hash == token_hash,
                        AuthToken.purpose == purpose,
                        AuthToken.consumed_at.is_(None),
                        AuthToken.expires_at > timestamp,
                    )
                    .with_for_update()
                )
                if token is None:
                    return None
                user = session.get(User, token.user_id)
                if user is None:
                    return None
                token.consumed_at = timestamp
                token.consumed_reason = "used"
                user.password_hash = password_hash
                user.password_changed_at = timestamp
                user.updated_at = timestamp
                session.execute(
                    update(AuthSession)
                    .where(
                        AuthSession.user_id == user.id,
                        AuthSession.revoked_at.is_(None),
                    )
                    .values(revoked_at=timestamp, revoke_reason="password_reset")
                )
                session.execute(
                    update(AuthToken)
                    .where(
                        AuthToken.user_id == user.id,
                        AuthToken.id != token.id,
                        AuthToken.consumed_at.is_(None),
                    )
                    .values(consumed_at=timestamp, consumed_reason="password_changed")
                )
            return self._user_record(user)

    def invalidate_tokens(
        self,
        *,
        user_id: str,
        purpose: str | None = None,
        reason: str = "invalidated",
        now: int | None = None,
    ) -> int:
        timestamp = int(now or time.time())
        conditions = [
            AuthToken.user_id == user_id,
            AuthToken.consumed_at.is_(None),
        ]
        if purpose:
            conditions.append(AuthToken.purpose == purpose)
        with self.session() as session:
            result = session.execute(
                update(AuthToken)
                .where(*conditions)
                .values(consumed_at=timestamp, consumed_reason=reason[:128])
            )
            session.commit()
            return int(result.rowcount or 0)

    def cleanup_expired(self, *, before: int | None = None) -> int:
        cutoff = int(before or time.time())
        with self.session() as session:
            token_result = session.execute(
                delete(AuthToken).where(AuthToken.expires_at < cutoff - 86_400)
            )
            session.execute(
                delete(AuthSession).where(
                    or_(
                        AuthSession.expires_at < cutoff - 7 * 86_400,
                        AuthSession.revoked_at < cutoff - 7 * 86_400,
                    )
                )
            )
            session.commit()
            return int(token_result.rowcount or 0)
