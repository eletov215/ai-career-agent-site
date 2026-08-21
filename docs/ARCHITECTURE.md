# AI Career Agent — architecture reference

> Current package: SEARCH-005, status ГОТОВО К СТАРТУ. PROF-003/PRIV-001 закрыты; production `20260813_0013`.

## Runtime boundaries

```text
app.py / Flask routes / app:app
  -> AuthService / OAuthIdentityService / CareerProfileService
  -> ResumeImportService / ResumeDraftService / PrivacyService
  -> repository contracts
  -> SQLAlchemy models
  -> PostgreSQL via DATABASE_URL / Alembic
```

Routes do not instantiate ORM repositories. `StorageServices` provides auth, users, OAuth, profile, resume, privacy, search and sync persistence boundaries.

## Identity and confirmed profile

```text
User
  -> AuthSession (browser authentication)
  -> OAuthConnection (HH/SuperJob external identity)
  -> CareerProfile (current confirmed structured facts)
       -> CareerProfileVersion[] (immutable full snapshots + source/provenance)
```

PROF-001 remains the only canonical confirmed-facts store. Provider metadata, uploaded resume text, extraction proposals and future AI suggestions are not facts until an authenticated owner explicitly confirms the ordinary profile form.

## PROF-002 request lifecycle

```text
owner session + CSRF
-> bounded PDF bytes
-> pypdf text extraction
-> deterministic ResumeImportProposal
-> merge with current confirmed profile
-> HTML editable review in browser
-> metadata-only signed token
-> explicit confirm POST
-> PROF-001 validation + expected version + row lock
-> no-op or immutable confirmed version
```

Upload bytes, raw text and unconfirmed proposal are never repository/model objects. Browser review is intentionally ephemeral.

## Merge and confirmation

```text
empty scalar + suggestion          -> suggestion shown
confirmed scalar == suggestion     -> current retained
confirmed scalar != suggestion     -> current retained + conflict shown
lists/rows                         -> stable case-insensitive union
user edit/delete                   -> submitted value wins
```

Confirmation still passes PROF-001 canonical JSON/hash, completion indicator and stale-editor protection. An import with no material changes creates no duplicate version.

## Review token

The timed `itsdangerous` token carries schema/extractor/counts/section confidence/static warnings, HMAC owner fingerprint, base profile version and issued time only. It carries no filename, bytes, raw text, excerpts, contacts or proposed payload.

## Persistence

Revision `20260812_0011` adds `source_kind` and aggregate `provenance_json` to immutable version rows. Current profile schema remains version 1. Existing rows default to `manual`; confirmed imports use `resume_import`.

## Security/operational boundaries

- first-party session is mandatory;
- CSRF and route rate limits remain active;
- stale or foreign review cannot confirm;
- upload/page/text bounds fail closed;
- logs contain aggregate counts/outcomes only;
- OCR/AI/background/persisted drafts are separate packages;
- WSGI remains `app:app`; no `app_fixed.py`.

## PROF-003 server resume document boundary

`ResumeDraft`/`ResumeVersion` are owner-scoped document data, not canonical PROF-001 facts. A profile may seed a new draft one-way; document edits never auto-update the profile. Mutable autosave uses expected revision + row lock. Explicit checkpoint/export/restore produce immutable snapshots. Image assets are durable objects referenced by UUID; PDF binary remains client-side and only bounded export metadata is stored.


## PRIV-001 privacy control boundary

`PrivacyService` is the single application boundary for owner-readable export, confirmed account deletion and technical retention cleanup. `/privacy-center` requires an active first-party session; export/delete are POST + CSRF + rate-limited. Account deletion additionally requires the current password and the exact confirmation phrase.

```text
User owner data
  -> sanitized ZIP export (manifest.json + data.json + owned resume assets)
  -> no password/session/token/OAuth credentials

confirmed account deletion
  -> PostgreSQL owner row lock
  -> delete local HH/SuperJob legacy credential mirrors
  -> delete User
  -> FK cascade profile/auth/OAuth/resume subtree
  -> identifier-free aggregate audit row
```

Migration `20260813_0013` adds only `privacy_audit_events(event_type, counts_json, created_at)` and intentionally has no `user_id`, email, filename, asset ID or content column. The periodic cleanup worker removes stale pending accounts, expired/revoked auth artifacts and old identifier-free audit rows according to configurable technical defaults. Remote provider-side OAuth grant revocation is not claimed by PRIV-001; the guaranteed contract is local credential erasure.

## SEARCH-005 admin/source-health boundary
Verified first-party session plus explicit email allowlist protects read-only admin routes. `source_health_states` has no user relation and stores only bounded safe operational aggregates. Existing OPS provider events feed a non-gating persistence adapter; Trudvsem additionally uses persistent sync/worker state.
