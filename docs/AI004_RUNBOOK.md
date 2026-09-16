# AI Career Agent - AI-004 runbook

| Field | Value |
|---|---|
| Version | 1.0 r1 / 2026-09-16 |
| Status | НУЖНА ПРОВЕРКА / NEEDS_VERIFICATION |
| Input | GitHub main c683520058cc1f729c79ed49ac5c213811e4c9f3 |
| Schema | accepted 0017 -> candidate 0018 |

## 1. Before upload/deploy

Back up the real database before any automatic Render deployment. Use only one delivery: FULL contents at the repository root, or PATCH over the verified source commit. Do not add a nested second project folder. The candidate already includes missing AI-003 final documentation; do not overlay the old final patch afterward. No .env, token or database belongs in GitHub.

Keep AI_ENABLED=0, AI_KILL_SWITCH=1, AI_SYNTHETIC_ACCESS_ENABLED=0, AI_ANALYSIS_REVIEW_ENABLED=0 and AI_INTERVIEW_REVIEW_ENABLED=0. Do not enable paid Alice workflow jobs. There is no AI-004 environment flag to add.

## 2. CI and migrations

Run ordinary GitHub CI for the new commit. The step `Verify AI-004 explainable vacancy match controls` must pass, including the Flask HTTP module and PostgreSQL scenario in its installed CI environment. Earlier green CI #276 validates the baseline only. Migration, backup/restore, previous package gates, Docker and full regressions remain mandatory.

The existing Render start process applies migrations. After successful deployment, `/health/ready` must report PostgreSQL persistent storage, status=ok and both current_revision and expected_revision equal to `20260916_0018`, migrations.ok=true. Do not manually reset or stamp Alembic to conceal an error. `/api/ai/status` must still be generation_available=false, mode=manual, reason=runtime_not_activated.

## 3. Open private review

Log into the existing active, email-verified SEARCH_ADMIN_EMAILS account. In that same browser open `/ai-match/review` and use the enable button. This authorizes only the current signed browser session and user. `/ai-match` then shows two developer-authored examples. No new registration, provider key or real resume is needed. Non-admin and logged-out visitors must continue to receive 404.

## 4. RU evidence and history

Create a report from the RU example. Expect 67%, the formula 6 / 9 * 100, and five requirements. Python, FastAPI/Django and PostgreSQL match supplied evidence. Mandatory Docker and preferred Kubernetes are explicitly unverified. The prominent mandatory warning must mention Docker. No wording may assert that unknown means the candidate cannot use it.

Open source and provenance details. Requirements and candidate excerpts must match the fixed input. Origin must say reference/test, not a new Alice call. Refresh/relogin and unlock the review again: saved report, version, source facts and score must remain. Creating a new report from the same example gives a new version; repeating the same submitted operation must not create duplicate versions. Two different newly loaded forms may legitimately create independent versions.

## 5. EN and source control

Create the EN report. Expect 71%, formula 5 / 7 * 100, and four requirements. React, TypeScript and testing evidence match; mandatory Next.js is unverified. Check that the English report and mandatory warning remain readable at desktop/mobile widths. Source snapshots, scoring version and hash fields are visible. There is no arbitrary-text input or upload control. Existing profile, resumes and search results must remain unchanged.

## 6. Deletion, export and isolation

Export data through `/privacy-center`; inspect locally, do not send the account export to the assistant. data.json must contain `vacancy_matches` and `vacancy_match_series`. Delete only an unwanted matching report using its confirmation checkbox. The report disappears and its former URL is unavailable; other reports, profile/resume/interview data and sources remain. New report versions do not reuse deleted numbers. Do not delete the real account.

A second already-working verified account may test cross-owner access. To prove owner isolation rather than merely the admin gate, both test accounts need independent review authorization. Never add unknown people to SEARCH_ADMIN_EMAILS. Without such a test setup, record manual two-account isolation NOT RUN and use named automated ownership tests as separate evidence; do not invent a successful manual test. Destructive account-cascade behavior is covered on disposable automated databases, not required on the owner's account.

## 7. Regressions and closure

Verify /dashboard, /profile, /resumes, ordinary builder autosave, preview/PDF, /vacancies search, login/logout and admin sources. Existing AI-003 session gate and saved interviews must still work when deliberately opened, and then be closed. Check Render logs for new 500/Traceback/IntegrityError/migration errors and content/secrets leakage; do not publish raw logs or credentials.

On `/ai-match/review` disable review. `/ai-match` and owned report/API URLs must again return 404. The review control page can remain accessible to the verified administrator, just as for AI-003; it does not mean generation is enabled. Confirm readiness0018 and manual AI status again. Record exact candidate Git SHA and CI run before package closure.

## 8. Rollback

First remove the session unlock/logout; no public AI switch should be turned on. For an application/database rollback, stop writes and preserve a verified backup including match reports/series. A controlled Alembic downgrade from 0018 to 0017 drops only these two new tables and destroys their match history; then deploy the compatible previous application. Coordinate this operation to avoid the old app's strict expected-revision mismatch. Do not downgrade a production database casually or treat a backup as optional. Rollback is a recovery operation, not a routine acceptance step.

## 9. Acceptance boundary

This can close only the synthetic/reference foundation. Live real-data matching, arbitrary requirement extraction, actual quality evidence and LEGAL-001/consent remain separate. No new paid provider call is required for reference acceptance. Successful unit tests alone do not close candidate HTTP, CI or staging gates.
