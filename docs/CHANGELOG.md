# Changelog

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
