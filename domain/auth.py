"""AUTH-001 records and service-facing results detached from SQLAlchemy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthUserRecord:
    id: str
    email: str
    normalized_email: str
    display_name: str | None
    status: str
    email_verified_at: int | None
    password_hash: str | None
    password_changed_at: int | None
    last_login_at: int | None
    created_at: int
    updated_at: int


@dataclass(frozen=True, slots=True)
class AuthSessionRecord:
    id: str
    user_id: str
    token_hash: str
    created_at: int
    last_seen_at: int
    expires_at: int
    revoked_at: int | None
    revoke_reason: str | None
    user_agent_hash: str | None


@dataclass(frozen=True, slots=True)
class AuthTokenRecord:
    id: str
    user_id: str
    purpose: str
    token_hash: str
    created_at: int
    expires_at: int
    consumed_at: int | None
    consumed_reason: str | None


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    user: AuthUserRecord
    session: AuthSessionRecord


@dataclass(frozen=True, slots=True)
class AuthActionResult:
    ok: bool
    code: str
    message: str
    user: AuthUserRecord | None = None
    session_token: str | None = None
