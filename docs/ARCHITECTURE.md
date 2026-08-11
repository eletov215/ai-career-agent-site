# AI Career Agent — архитектура проекта

> Последнее обновление: 11 августа 2026 года  
> Текущий пакет: `AUTH-002` — first-party-owned HeadHunter/SuperJob identities  
> Статус: **НУЖНА ПРОВЕРКА**; candidate revision `20260811_0009`

## 1. Архитектурная цель

```text
Flask routes / blueprints
→ application services
→ repositories
→ SQLAlchemy models/session
```

SEARCH-001..004 и AUTH-001 остаются завершёнными contours. AUTH-002 добавляет owner-bound external identity contour поверх first-party `User`.

## 2. Identity/auth layers

```text
routes/auth.py
  → services/auth.py
    → repositories/auth.py
      → users + auth_sessions + auth_tokens

services/passwords.py       versioned scrypt
services/email_delivery.py  disabled/memory/SMTP/Gmail API provider-neutral adapters
```

`app.py` только wire-ит AuthService через `StorageServices`; routes не импортируют ORM.

## 3. Identity boundary

`users` — единственный root. AUTH-002 explicit-binding выполняется только после свежего provider OAuth proof; legacy unbound rows сохраняют nullable `user_id` и не связываются по email.

## 4. Persistence schema

Candidate revision `20260811_0009`:

```text
users 1 ── * auth_sessions
users 1 ── * auth_tokens
users 1 ── 0..2 oauth_connections  (one slot per supported provider)
```

Auth rows cascade only when User is intentionally deleted. Password/session/action raw secrets are not stored.

## 5. HTTP/session flow

1. Registration creates pending User + hashed verification token.
2. Verification POST atomically consumes token and activates User.
3. Login performs bounded scrypt verification and creates hashed server session.
4. Browser Flask session stores opaque raw token; server checks DB on each request.
5. Logout/revoke sets `revoked_at`; reset changes password and revokes all sessions atomically.

## 6. Email/configuration

Production default is `disabled`. `smtp` supports either STARTTLS or implicit SSL/TLS with environment secrets; exactly one secure transport mode is required in production. `memory` is test-only and forbidden in production. Readiness exposes only backend/configured boolean.

## 7. Security/observability

CSRF, secure cookie, trusted hosts, ProxyFix and security headers come from SEC-001. Auth routes add strict rate limits, no-store/strict-origin and enumeration-safe copy. Origin-only referrers preserve Flask-WTF HTTPS same-origin CSRF validation without forwarding token paths/queries. Logs exclude email/password/raw token/SMTP body.

## 8. Compatibility and rollback

Search snapshot/dedup and sync state are unchanged. AUTH-002 adds only revision `0009` ownership constraint. Application revert may retain `0009`; downgrade removes only the new constraint and keeps OAuth/auth/search data.


## 9. AUTH-002 ownership contour

- Browser authentication is first-party `AuthSession` only; legacy provider IDs are ignored and removed from session.
- OAuth start requires current User/AuthSession. State stores random value, TTL, `user_id` and `auth_session_id`.
- `OAuthIdentityService` mediates create/claim/refresh/disconnect and maps repository conflicts to safe public errors.
- Database constraints enforce unique external identity and one provider slot per User.
- Provider access/refresh tokens remain Fernet-encrypted; owner-scoped repository methods prevent cross-user reads/deletes.
- Dashboard is first-party-only. Search continues to use provider/public application credentials independently of user OAuth.

Remote provider revoke and account transfer/merge are explicit exclusions of the candidate.
