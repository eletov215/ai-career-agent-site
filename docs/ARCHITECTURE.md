# AI Career Agent — architecture reference

> Current candidate: PROF-001, status НУЖНА ПРОВЕРКА, Alembic head `20260811_0010`.

## Runtime boundaries

```text
app.py / Flask routes / app:app
  -> AuthService / OAuthIdentityService / CareerProfileService
  -> repository contracts
  -> SQLAlchemy models
  -> PostgreSQL via DATABASE_URL / Alembic
```

Routes do not instantiate ORM repositories. `StorageServices` provides auth, users, OAuth, profile, search and sync persistence boundaries.

## Identity and profile

```text
User
  -> AuthSession (browser authentication)
  -> OAuthConnection (HH/SuperJob external identity)
  -> CareerProfile (current confirmed structured facts)
       -> CareerProfileVersion[] (immutable full snapshots)
```

OAuth provider profile JSON is credential metadata and does not automatically become CareerProfile facts. Resume extraction/AI suggestions remain unconfirmed until a future explicit review flow.

## PROF-001 transaction

```text
owner POST + CSRF
-> validate/canonicalize
-> owner row lock + expected_version check
-> compare SHA-256 content hash
-> unchanged: return current version
-> changed: update current + insert immutable version
-> commit transaction
```

## Data evolution

- Alembic only; current production `0009`, candidate `0010`.
- Profile `schema_version=1` is independent of Alembic revision.
- Future child-table normalization must be additive and preserve immutable snapshots.
- Application rollback may keep `0010`; downgrade is profile-data destructive.

## Security

Profile routes require first-party session, are owner-scoped, POST+CSRF protected, rate-limited and `no-store`. Structured logs exclude profile facts and owner IDs. Backup inventory includes profile tables.

## Exclusions

PROF-002 import/review, PROF-003 autosave/drafts, PRIV-001 lifecycle, AI population, public profile and version restore are not part of this architecture candidate.
