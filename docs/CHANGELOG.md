# Changelog

## 1.4.24 — PROF-002 complete — 12.08.2026

- Initial Pull Request CI passed, including `Verify PROF-002 resume import review controls`; Render applied PostgreSQL revision `20260812_0011` and readiness reported `status=ok`, persistent PostgreSQL and current/expected `0011`.
- Production verification found an upload-routing defect: `/profile/import` inherited the generic 256 KiB POST limit. Hotfix r2 added the route to upload endpoints, kept the 8 MiB PROF-002 limit, added visible upload/progress/oversize UX and regression coverage; no migration change.
- Production E2E confirmed text-PDF upload, editable review, zero persistence before explicit confirmation, preservation of existing confirmed scalar values, user correction/removal, one `resume_import` version with aggregate provenance, and stale-review rejection without lost updates.
- Cross-account URL smoke confirmed User B receives a clean upload form and cannot recover User A's PDF/review from the copied `/profile/import` URL; token owner-binding remains covered by dedicated CI.
- Non-PDF and image-only PDF failures were safe and did not change profile history. A corrupt-PDF manual fixture was unavailable; parser failure paths remain automated-test coverage.
- Render restart preserved confirmed profile/import history; mobile review and final dashboard/auth/OAuth/vacancy-search/log/readiness regression were reported working normally.
- English CV quality observation: deterministic extraction can produce low-confidence or incorrect structural suggestions on nonstandard layouts; mandatory review prevented automatic corruption. OCR/AI extraction remains future scope.
- PROF-002 is ВЫПОЛНЕНО. Next package: PROF-003.

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

## 2026-08-13 — PROF-003 iOS/Safari photo upload hotfix r3

- Production E2E on iPhone Safari reached photo upload after server drafts, versions, restore and stale-tab protection had passed. Selecting a valid gallery image showed the local preview but then surfaced Safari's generic `Load failed` before the asset was persisted.
- Root cause: the builder converted a generated `data:image/...;base64,...` URL to `Blob` through `fetch(dataUrl)`. Safari can reject this local `data:` fetch even though the same data URL renders in an `<img>`.
- Replaced the `fetch(dataUrl)` conversion with an in-memory base64 decode (`atob` -> `Uint8Array` -> `Blob`) before the ordinary same-origin multipart upload. Backend MIME/signature/2 MiB processed-asset controls are unchanged.
- Added a neutral Russian network error for the real server upload and restore of the previous photo/asset state when upload fails, so a failed local preview is not mistaken for a persisted photo.
- Added static frontend regression coverage. No database migration or Render environment-variable change; schema remains `20260812_0012`.
- PROF-003 remains **НУЖНА ПРОВЕРКА** pending green CI/redeploy and resumed asset/export/owner/restart regression E2E.

## 2026-08-13 — PROF-003 production E2E direct-edit hotfix r2

- Production E2E confirmed authenticated server drafts, autosave persistence across logout/login/device, multiple independent drafts, and checkpoint version 1.
- E2E exposed a usability defect in the legacy interview-only builder: after completing the interview, changing one field required replaying the whole questionnaire.
- Added a responsive `Редактировать поля` editor inside the existing resume builder. It pre-fills all eight document fields, allows changing or clearing only the needed values, updates live preview, reuses server autosave/optimistic revision protection, and does not rewrite the interview transcript.
- Education changes continue through the existing university-logo refresh path. No database migration or Render environment variable change.
- PROF-003 remains **НУЖНА ПРОВЕРКА** until hotfix CI/redeploy and resumed version/restore/conflict/asset/export/owner/restart regression E2E.

## 2026-08-13 — PROF-003 candidate v1.4.25

- Added owner-scoped server resume drafts and multiple-resume library.
- Added optimistic revision autosave with safe `409` stale conflict.
- Added immutable checkpoint/export/restore versions, history and read-only version views.
- Added durable photo/university-logo assets and export metadata tied to exact version.
- Added migration `20260812_0012`, backup inventory, owner/resource/rollback tests and dedicated CI gate.
- Removed authoritative localStorage writes; retained one-time legacy migration only.
- Synchronized repository docs that lagged canonical PROF-002 COMPLETE.
- Status: **НУЖНА ПРОВЕРКА** until CI/Render/E2E.
