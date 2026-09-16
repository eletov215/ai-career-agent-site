# AI Career Agent - AI-004 implementation

| Field | Value |
|---|---|
| Version | 1.0 r1 / 2026-09-16 |
| Status | НУЖНА ПРОВЕРКА / NEEDS_VERIFICATION |
| Baseline | GitHub main c683520058cc1f729c79ed49ac5c213811e4c9f3; CI #276 PASS |
| Accepted staging / target | 20260916_0017 / 20260916_0018 |
| Public or real-data AI | Disabled; no new consent or activation inferred |

## 1. Product boundary

This release implements the **synthetic/reference-only matching foundation**, not arbitrary live candidate-vacancy matching. It accepts only the pinned identifiers `vacancy-match-ru-01` and `vacancy-match-en-01`. Existing benchmark source facts, prompts and schemas remain byte-preserved. New reference files are copies of the accepted developer-authored outputs with a checked SHA-256 manifest; they are not presented as fresh Alice responses.

The browser can neither upload a resume nor submit free text, profile contents, a vacancy URL or a percentage. Ordinary search results/cards and real career profiles/resume drafts are not modified. Future live matching still needs general input/extraction integration, feature quality checks, consent and real-data routing, LEGAL-001 and explicit activation. There is no legal bypass switch.

## 2. Scoring and evidence

`domain/vacancy_match.py` computes a versioned exact-fraction score. Each validated requirement has a fixed importance, positive integer weight and evidence status. The denominator includes every requirement, including unresolved mandatory requirements. Score = round(100 * matched weight / total weight), using exact half-even rounding consistent with the accepted benchmark. Requirement ordering and provider verdict do not change it. Empty, duplicate, unknown, incomplete or malformed classifications fail closed.

The pinned RU case is 6/9 = **67%**; mandatory Docker and preferred Kubernetes remain unverified. The EN case is 5/7 = **71%**; mandatory Next.js remains unverified. Missing evidence is not interpreted as proof of missing ability. A high percentage cannot produce the internal strong verdict when any mandatory requirement remains unresolved. The UI always exposes the mandatory warning and every requirement rather than replacing them with prose.

Evidence coverage is calculated separately and labelled as coverage, not calibrated confidence or hiring probability. The general scorer distinguishes `mismatch` from `unverified`; these two fixtures contain no explicit mismatch. This candidate does not claim to infer real-world contradictions from arbitrary text.

## 3. Provider boundary

`services/ai/match_validation.py` first checks the accepted JSON schema, then complete unique requirement IDs, expected fixed-fixture statuses and exact evidence IDs. It rejects missing, invented or duplicate evidence and incomplete coverage. It is a fixed-fixture validator, not a general semantic truth oracle.

Provider-authored explanation text, verdict and caveats are discarded. Reports contain only exact input source extracts, computed labels and deterministic numbers. Therefore an unsupported claim in model prose cannot become a saved report statement. Validation is passed into AI-001 before successful settlement; the service explicitly canonicalizes the returned content again before persisting, because AI-001 callbacks validate but do not replace its return value.

The internal `VacancyMatchService.analyze()` accepts pinned fixtures only and reuses the existing Alice adapter, operator limits, kill switch, usage ledger and persistent idempotency. No browser route calls it. Ordinary tests use fake providers. If settlement succeeds but report persistence fails, repeating the same key does not launch another paid call to recover lost content. Browser reference creation does not touch the provider or usage ledger even with operator flags enabled.

## 4. Persistence and privacy

Migration `20260916_0018` adds `vacancy_match_series` and `vacancy_match_reports`. Reports are immutable owned snapshots with source facts, canonical result, separate candidate/vacancy/source/result hashes, source and scoring versions, reference/provider origin and creation time. A small per-owner/per-fixture series counter avoids reusing a version after deleting a report. Up to 100 reports per owner are retained; deleting an owned report frees capacity without clearing other user data.

Writes lock the verified owner row on PostgreSQL and use BEGIN IMMEDIATE on SQLite. Locks cover only short database work, never provider I/O. Unique constraints enforce owner/operation and owner/fixture/version. Request keys are HMAC-fingerprinted and bound to fixture, source, origin and scoring version. Replays return the same report while it exists. Individual deletion requires an explicit checkbox and the expected result hash; deleting one report does not alter the other versions or canonical sources.

`/privacy-center` export adds `vacancy_matches` and `vacancy_match_series`. Internal operation/accounting IDs are excluded from the readable match reports. Account deletion cascades both owned tables; backup inventory includes both. No real account is deleted during prescribed acceptance. Source changes mark an existing report as a historical/stale snapshot; it is never silently recomputed.

## 5. Access and user interface

| Method | Route | Purpose |
|---|---|---|
| GET | /ai-match/review | Verified allowlisted administrator gate |
| POST | /ai-match/review/enable | Unlock only the current signed session/user |
| POST | /ai-match/review/disable | Remove that unlock |
| GET | /ai-match | Pinned examples and owned history |
| POST | /ai-match/reference | Persist a reference report, never a provider call |
| GET | /ai-match/<report_id> | Read owned report |
| GET | /api/vacancy-matches/<report_id> | Read owned report as JSON |
| POST | /ai-match/<report_id>/delete | Confirmed owner-only deletion |

All routes require an active, verified account in existing SEARCH_ADMIN_EMAILS. The review gate itself requires admin status; other paths additionally require the signed current-user unlock. Logout clears it. No new Render variable is needed and AI-003 review permission does not unlock AI-004. Global CSRF, per-route limits, no-store/noindex and autoescaped native forms remain in force. Unknown/duplicate fields, JSON and uploads are rejected. Database errors produce neutral 503 responses rather than SQL/credentials. An inaccessible report is not disclosed by the owner API.

The RU/EN detail pages expose formula, per-requirement source evidence, mandatory warnings, provenance and deletion confirmation. The mobile layout wraps source/hash text and does not introduce JavaScript or change existing builder scripts.

## 6. Compatibility, checks and rollback

App remains `app:app`; runtime dependencies, config.py, render.yaml, accepted AI policy/prompts/schemas/evals and existing frontend are preserved. AI-003 final documentation synchronization is bundled because it was absent on the verified main. New and earlier package gates share an explicit additive checksum chain instead of disabling old protection checks.

See AI004_VERIFICATION_STATUS.md for measured local checks and uncompleted external gates. See AI004_RUNBOOK.md for safe deployment and rollback. Additive 0018 is not automatically compatible with old exact-revision readiness checks: do not revert the application to an 0017-only version while leaving an unplanned schema mismatch.
