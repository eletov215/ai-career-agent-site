# AI Career Agent — доменная модель

## 1. Основные агрегаты

```text
User 1 ── * AuthSession
User 1 ── * AuthToken
User 1 ── * OAuthConnection        (AUTH-002 binding)
Vacancy 1 ── * VacancySourceRecord
SyncRun / SyncWorker / SyncCheckpoint
SearchSnapshot 1 ── * SourceState / Candidate / Item
```

## 2. AuthUserRecord

Immutable service-facing projection: identity/contact/status/verification/password/login timestamps and hash. Flask routes never receive ORM entities.

## 3. AuthSessionRecord

Opaque hashed bearer session with absolute expiry, last-seen, revoke state/reason and hashed user-agent. It is server-revocable and independent of provider OAuth identities.

## 4. AuthTokenRecord

Purpose-bound verification/reset token hash with created/expiry/consumed state. New same-purpose token supersedes previous. Consumption and user mutation occur atomically.

## 5. Invariants

- normalized email is unique;
- pending User cannot login;
- verification activates only pending User;
- password reset revokes all first-party sessions;
- raw password/session/action tokens never persist;
- HH/SJ connection ownership is unchanged until AUTH-002.

## 6. Existing search/sync aggregates

SEARCH-001..004 vacancy/snapshot semantics and SYNC checkpoints remain unchanged by AUTH-001.
