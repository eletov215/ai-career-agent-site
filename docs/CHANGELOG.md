# Changelog

## 1.4.23 — PROF-002 candidate — 12.08.2026

- Verified uploaded `ai-career-agent-site-main (16).zip` as exact GitHub `main` commit `f5e513f0f992b20305fbef36851ef97576013c86`.
- Added authenticated text-PDF import and full editable PROF-001 review; profile/history remain unchanged before explicit confirmation.
- Added deterministic `ResumeImportService` proposals for positioning, contacts, geography, skills, employment, education, languages and achievements with confidence, warnings, conflicts and bounded evidence.
- Preserved existing confirmed scalar facts on conflict and merged lists/rows without implicit deletion.
- Added a 30-minute signed review token bound to HMAC owner fingerprint and base profile version; token excludes filename, raw text and profile facts.
- Added migration `20260812_0011` with `source_kind` and aggregate `provenance_json` on immutable profile versions; canonical profile schema remains version 1.
- Added upload/review/history UI, owner/privacy-safe logging, migration/service/route/parser/PostgreSQL tests and dedicated PROF-002 CI gate.
- Local verification: `246 passed, 10 skipped`; focused `15 passed`; compile/Jinja/SQLite round-trip/Alembic check passed.
- Status remains НУЖНА ПРОВЕРКА pending Pull Request CI, Render `0011` and production E2E.

## 1.4.21 — PROF-001 partial-profile hotfix — 12.08.2026

- Initial PROF-001 Pull Request CI passed and Render successfully migrated production PostgreSQL to `20260811_0010`.
- Production E2E found a false-required validation defect: blank repeatable form rows still submitted default select values and were treated as entered records.
- Updated repeatable-row detection to ignore only default-only `employment_current=0`, `skill_level=unspecified`, and `language_level=unspecified` rows.
- Preserved strict validation when a user actually starts entering a repeatable record.
- Added service and browser-shaped route regression tests for partial profile save.
- No database migration or environment variable changes. PROF-001 remains НУЖНА ПРОВЕРКА pending hotfix CI/redeploy and resumed production E2E.

## 1.4.20 — PROF-001 candidate — 11.08.2026

- Added owner-scoped `career_profiles` and immutable `career_profile_versions`.
- Added Alembic `20260811_0010` with unique owner/current and profile/version constraints.
- Added canonical structured sections for positioning, contacts, goals, geography, salary, skills, employment, achievements, education and languages.
- Added bounded validation, canonical JSON/content hash, completion indicator and optimistic stale-editor conflict.
- Added `/profile`, `/profile/edit`, `/profile/history` and read-only version views.
- Integrated profile completion into dashboard, navigation and responsive UI.
- Added backup inventory, migration/service/route/PostgreSQL tests and dedicated PROF-001 CI gate.
- Added PROF001 implementation, verification, runbook and profile reference docs.
- Status remains НУЖНА ПРОВЕРКА pending Pull Request CI, Render `0010` and production owner/version/restart E2E.

## 1.4.19 — AUTH-002 complete — 11.08.2026

- GitHub CI, Render `20260811_0009`, HeadHunter/SuperJob ownership E2E and regression smoke confirmed.
- AUTH-002 marked ВЫПОЛНЕНО; PROF-001 became next.

Earlier history is preserved in `docs/PLAN_CURRENT.md` and previous canonical packages.
