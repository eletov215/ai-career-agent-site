# AI Career Agent - JOB-001 implementation

| Field | Value |
|---|---|
| Version | 1.1 REBUILT / 2026-09-17 |
| Status | NEEDS_VERIFICATION |
| Baseline | d5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4 |
| Accepted / candidate schema | 20260916_0018 / 20260917_0019 |
| Scope | Ordinary verified-account saved vacancies, not synthetic AI examples |
| Remote publication | Not performed in this reconstruction |

## 1. Source and reconstruction boundary

The previous JOB-001 r1 archive/source was unavailable. This implementation is a replacement based on the agreed scope and verified current GitHub main, not a byte-identical reissue. Historical r1 file counts and claimed test results are not evidence of this build. See JOB001_RECONSTRUCTION.md and SOURCE_AUDIT1.6.0.

Preserved AI-004 FINAL1.5.7 closure documents/status guards are included because main still contains the earlier candidate documentation. Its accepted application logic is unchanged except the explicit JOB-001 integration points. AI001..004 sources and acceptance remain in their individual reference/synthetic boundaries.

## 2. Authority of saved data

SearchAggregationService returns its committed SearchSnapshotItem stable key with each server-side item. The view layer signs only owner ID, snapshot UUID, stable key and hash of the exact stored search payload. These metadata contain no full vacancy or resume text. References expire after30minutes and are bound to the verified account. CSRF remains separately required.

Saving re-reads the unexpired committed item, validates its hash and takes an explicit allowlisted projection; the browser cannot provide a title, description, percentage or arbitrary source URL. Missing/expired/changed items return a neutral conflict and require a fresh search. Unrenderable source data does not break ordinary search.

Snapshots retain bounded title/employer/location, salary/currency, canonical work/employment/experience codes, description, requirements, published date and normalized known source records. Description is limited to32000 characters, requirements16000; truncation is recorded and shown. Provider raw JSON, personal credentials and search terms are not included. Text remains autoescaped. Salary/date/skill facts are not inferred.

## 3. Persistence and deduplication

Migration0019 adds saved_vacancies and saved_vacancy_sources. A saved row owns immutable snapshot JSON/hash/version, title/company/location/search text, editable private note, revision and timestamps. Source rows have an owner-scoped unique identity hash from provider and external ID (or safe URL if ID absent). A composite FK enforces the same owner on the saved object and all source aliases. There is no FK to cache/search tables, so cache retention does not delete saved content.

Repeated saves of a known identity return the existing object without replacing its snapshot or note. Proven extra aliases from a grouped search card may attach to that object and increment its revision. If a newly grouped card spans two already independently saved objects, the operation fails with a conflict instead of deleting/coalescing private notes. Conservative identity matching intentionally does not fuzzy-merge unrelated saved objects or retroactively reconcile split/regrouped source history.

Writes lock the active verified owner for short database-only transactions: BEGIN IMMEDIATE on SQLite and a user row lock on PostgreSQL, with a5-second PostgreSQL lock timeout. No network call is performed while holding a lock. Up to500 saved objects and16 source aliases per object are allowed. Duplicate saves still succeed when the object limit is reached.

## 4. Library, notes and source freshness

/saved-vacancies provides a20-item page, stable descending creation order with an ID tie-breaker, and literal case-insensitive substring filtering over title/company/location/private note. This is not full-text ranking. SQL wildcard characters are escaped. The detail view exposes the immutable saved text, sanitized source links, created time, last known cached state, a separate private note and confirmed deletion.

Notes are limited to4000 characters and save only on an explicit native-form submit. expected_revision detects stale editors and deletes. An unchanged note does not create a revision. A stale HTML edit shows both unsaved input and the current note, escaped, without auto-overwriting or silently replaying against a fresh revision.

Freshness is explicitly limited to local knowledge: last known cached active/closed/expired, old cache, missing cache or unknown. A24-hour technical threshold labels old snapshots/cache; it is not a source SLA. Absence from cache does not prove that the vacancy closed. No periodic provider recheck is introduced. URL links are allowlisted to the existing HH/SuperJob/Reed/Trudvsem hosts, have credentials/query/fragment stripped or are omitted when unsafe. Opening the library never fetches those URLs on the server.

## 5. Legacy browser marks

The old localStorage array stores keys only, without a reliable owner or complete snapshot. Migration is therefore explicit, never performed automatically on login. A hidden panel is exposed only when usable old marks exist. The user must confirm that they belong to the current account.

At most50 keys are processed per request. The server searches exact URL/fallback keys in a bounded local canonical cache query and exact old dedup keys in the200 most recent committed unexpired search items. Unknown or ambiguous candidates are retained as unresolved, not invented. There is no source HTTP fetch. Only keys explicitly acknowledged as saved by the server are removed from localStorage; concurrent new marks and unresolved marks remain. This is a bounded best-effort recovery, not a guarantee that every old mark can be restored.

## 6. Routes and browser controls

| Method | Route | Purpose |
|---|---|---|
| GET | /saved-vacancies | Private library/filter/page |
| POST | /saved-vacancies/save | Signed server-reference save |
| GET | /saved-vacancies/<uuid> | Owned snapshot and note |
| GET | /api/saved-vacancies/<uuid> | Owned JSON view |
| POST | /saved-vacancies/<uuid>/note | Revision-checked private note |
| POST | /saved-vacancies/<uuid>/delete | Confirmed revision-checked delete |
| POST | /saved-vacancies/import-legacy | Explicit bounded old-mark migration |

All routes require an active verified first-party account, not an admin review flag. Global CSRF and per-route limits remain enabled. Unexpected/duplicate form fields, uploads and arbitrary JSON bodies are rejected. API unauthenticated reads return401; anonymous page reads redirect to login; foreign/missing objects are404. Database failures produce neutral errors, not SQL or secret values. Private pages/API and the personalized search response use no-store.

Search save forms work without JavaScript. Optional progressive enhancement sends the same form with same-origin credentials and switches to the saved link only after server confirmation; failed requests are not labeled saved. New styles are scoped job001 classes; unrelated homepage/builder design is unchanged.

## 7. Privacy, AI and integration

Export includes saved_vacancies and saved_vacancy_sources for the reauthenticated owner only. Snapshot hashes are checked; internal owner/index/request secrets are not exported. Deleting a saved object removes only its owned source aliases. Deleting the owner cascades the saved subtree. Backup inventory includes both tables; production backup/restore is not claimed by this delivery.

This module does not call Alice or mutate a resume/profile. The match field is null with not_available; no synthetic67/71 result is assigned to a real vacancy. Future AI-005 letters and real-data matching need separate source/owner/quality/consent integration. Application tracking, auto-apply, notifications, new providers and live vacancy rechecks are excluded.

## 8. Compatibility and checks

WSGI remains app:app; config.py, render.yaml, dependencies, provider prompts/schemas/benchmarks and accepted AI policy are byte-preserved. The existing startup migration mechanism will apply0019 only after future deployment. Old exact-head checks are synchronized through an explicit JOB-001 checksum boundary; no blanket protection bypass is added. AI-004 historical migration tests still target0018 explicitly while current metadata remains0019.

New local results and exact limitations are in JOB001_VERIFICATION_STATUS.md. External GitHub CI, installed Flask/PG scenarios and real-site acceptance remain separate. Rollback instructions are in JOB001_RUNBOOK.md.
