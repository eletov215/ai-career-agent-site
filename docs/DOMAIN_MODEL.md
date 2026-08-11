# AI Career Agent — доменная модель

## 1. Основные агрегаты

```text
User 1 ── * AuthSession
User 1 ── * AuthToken
User 1 ── 0..1 OAuthConnection/provider (AUTH-002 owner-bound)
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
- HH/SJ connections are owner-bound by AUTH-002 candidate; legacy nullable rows remain unbound until fresh OAuth proof.

## 6. Existing search/sync aggregates

SEARCH-001..004 vacancy/snapshot semantics and SYNC checkpoints remain unchanged by AUTH-001/AUTH-002.


## 6. AUTH-002 ownership invariants

| Field/constraint | Contract |
|---|---|
| `oauth_connections.user_id` | owner User; nullable only for legacy unbound compatibility |
| unique `(provider, external_user_id)` | one external identity across all Users |
| unique `(user_id, provider)` | one connection per provider for each User |
| `access_token` / `refresh_token` | Fernet-encrypted ciphertext |
| `profile_json` | provider snapshot, not verified career-profile truth |

Create/claim/refresh occurs transactionally after provider callback. Email matching is never an ownership proof. Disconnect deletes the owner row and provider mirror; first-party User remains.
