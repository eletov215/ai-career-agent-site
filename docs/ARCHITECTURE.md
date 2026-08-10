# AI Career Agent — архитектура проекта

> Последнее обновление: 10 августа 2026 года  
> Текущий пакет: `AUTH-001` — first-party account  
> Статус: **НУЖНА ПРОВЕРКА**; candidate revision `20260810_0008`

## 1. Архитектурная цель

```text
Flask routes / blueprints
→ application services
→ repositories
→ SQLAlchemy models/session
```

SEARCH-001..004 остаются завершённым vacancy contour. AUTH-001 добавляет first-party identity contour без связывания внешних OAuth connections.

## 2. Identity/auth layers

```text
routes/auth.py
  → services/auth.py
    → repositories/auth.py
      → users + auth_sessions + auth_tokens

services/passwords.py       versioned scrypt
services/email_delivery.py  disabled/memory/SMTP adapter
```

`app.py` только wire-ит AuthService через `StorageServices`; routes не импортируют ORM.

## 3. Identity boundary

`users` — единственный root. Legacy users/OAuth rows могут иметь null password fields. AUTH-001 не присваивает HH/SJ connections. AUTH-002 выполнит explicit binding later.

## 4. Persistence schema

Candidate revision `20260810_0008`:

```text
users 1 ── * auth_sessions
users 1 ── * auth_tokens
users 1 ── * oauth_connections  (binding remains AUTH-002)
```

Auth rows cascade only when User is intentionally deleted. Password/session/action raw secrets are not stored.

## 5. HTTP/session flow

1. Registration creates pending User + hashed verification token.
2. Verification POST atomically consumes token and activates User.
3. Login performs bounded scrypt verification and creates hashed server session.
4. Browser Flask session stores opaque raw token; server checks DB on each request.
5. Logout/revoke sets `revoked_at`; reset changes password and revokes all sessions atomically.

## 6. Email/configuration

Production default is `disabled`. `smtp` uses STARTTLS and environment secrets. `memory` is test-only and forbidden in production. Readiness exposes only backend/configured boolean.

## 7. Security/observability

CSRF, secure cookie, trusted hosts, ProxyFix and security headers come from SEC-001. Auth routes add strict rate limits, no-store/no-referrer and enumeration-safe copy. Logs exclude email/password/raw token/SMTP body.

## 8. Compatibility and rollback

Search snapshot/dedup, sync state and OAuth tables are unchanged. Application revert may retain 0008. Downgrade removes auth data and is not allowed after real account creation without backup/explicit policy.
