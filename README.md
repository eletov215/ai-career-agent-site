# AI Career Agent

## Current candidate / AI-004 r1

PLAN_CURRENT 1.5.6 / PROJECT_PASSPORT 2.73. AI-003 is accepted; AI-004 is NEEDS_VERIFICATION. Source is verified GitHub main c683520058cc1f729c79ed49ac5c213811e4c9f3 / CI #276. Last accepted staging schema0017; candidate0018 requires new CI/deployment. Private reference matching opens via `/ai-match/review` for a verified allowlisted admin and never calls Alice from the browser. See `docs/AI004_RUNBOOK.md`. No new Render environment variable, free text or public AI activation. This package includes pending AI-003 final doc sync. Older dated summaries below are historical.

<!-- ACA-CANONICAL-STATUS:START -->
## Canonical state / 2026-09-16

| Field | Value |
|---|---|
| Current package | AI-003 - ВЫПОЛНЕНО in synthetic/reference-only scope; AI-004 r1 - НУЖНА ПРОВЕРКА / NEEDS_VERIFICATION |
| Source lineage | GitHub main `c683520058cc1f729c79ed49ac5c213811e4c9f3`; tree `6458daea23371dadfbbd49d830abcdde44df1293`; 527 verified files |
| Canonical versions | PLAN 1.5.6; PASSPORT 2.73; SOURCE_AUDIT 1.5.6 |
| Completed AI foundation | AI-BENCH-001 / AI-PROVIDER-001 / AI-001 / AI-002 / AI-003 - ВЫПОЛНЕНО in accepted boundaries |
| LEGAL-001 | ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА; public real-data AI, payments and commercial release remain blocked |
| Accepted staging schema | Render/Neon 20260916_0017; owner-confirmed current=expected and migrations.ok=true |
| New candidate schema | 20260916_0018; two additive matching tables; deployment NOT yet verified |
| AI-004 boundary | Closed RU/EN reference reports; exact code-derived score, per-requirement source evidence, versions and privacy; no browser provider call |
| Runtime | generation_available=false, mode=manual, reason=runtime_not_activated |
| Baseline CI | GitHub CI #276 / run 35132463421 / success; directly read through connector for the exact source commit |
| Candidate verification | Local measurements in AI004_VERIFICATION_STATUS; new GitHub CI, Render/Neon and owner browser tests PENDING |
| Next action | Deliver candidate -> ordinary CI -> 0018 readiness -> private /ai-match/review acceptance; keep public AI closed |
<!-- ACA-CANONICAL-STATUS:END -->

## 1. Product and runtime

Flask + Gunicorn (`app:app`), PostgreSQL through SQLAlchemy/Alembic, independent sync/privacy workers. Confirmed career profiles and editable resume drafts remain separate. HH, SuperJob, Reed and Trudvsem vacancy search is unchanged by AI-003. Do not create `app_fixed.py`.

## 2. AI-003 accepted foundation

Read `docs/AI003_RUNBOOK.md` before deployment. This is a private synthetic/reference-only adaptive interview, not a live Alice conversation. It accepts pinned answer IDs, keeps history, and applies only explicitly selected reference statements to a newly created test draft after confirmation. No real profile is read or sent to a provider. The accepted benchmark and provider strategy remain unchanged.

```bash
python scripts/check_ai_provider_package.py
python scripts/check_ai_bench_package.py
python scripts/check_ai001_package.py
python scripts/check_ai002_package.py
python scripts/check_ai003_package.py
python scripts/check_ai004_package.py
python -m pytest -q
python scripts/check_document_structure.py
python scripts/check_repository_hygiene.py
```

Ordinary CI installs pinned dependencies and runs PostgreSQL 17. Paid benchmark workflow inputs remain false. No new credentials are needed for this reference review. Full local results and skips are recorded in `docs/AI003_VERIFICATION_STATUS.md`.

## 3. Source of truth

The latest supplied GitHub archive is the code baseline. Owner final PDFs dated 2026-09-15 establish AI-002 acceptance and legal deferral, overriding stale Markdown in main (33). This new candidate incorporates that closure documentation and advances active Markdown to PLAN1.5.6 / PASSPORT2.73 / AUDIT1.5.6. Historical entries remain dated. See `docs/CANONICAL_DOCUMENTS.md` and `docs/SOURCE_AUDIT.md`.

## 4. Deployment and gates

Accepted staging: Render web + Neon PostgreSQL at `20260916_0017`. The additive AI-003 migration contains only the two interview tables; back up before any future downgrade. `AI_ENABLED=0`, `AI_KILL_SWITCH=1`, `AI_SYNTHETIC_ACCESS_ENABLED=0`, `AI_ANALYSIS_REVIEW_ENABLED=0` stay unchanged. `AI_INTERVIEW_REVIEW_ENABLED=0` remains the operator-wide default; r1.2 staging review normally uses the admin-only `/ai-interview/review` per-session unlock and closes it again after testing.

LEGAL-001 remains deferred and blocks public real-data AI, paid subscriptions and commercial launch. Verification email delivery remains unresolved. INFRA-001 and production restore/domain migration stay pre-release work. AI-004 r1 is a new candidate on the directly verified GitHub source and requires its own CI/staging acceptance.

## 5. Upload and security

The AI-004 FULL ZIP is the complete new candidate; its PATCH overlays verified GitHub main c683520058cc1f729c79ed49ac5c213811e4c9f3. It includes the pending AI-003 final documentation. Do not overlay the old AI-003 final patch afterward. Do not delete the repository or `.git` first. Preserve `.github/workflows/ci.yml` when uploading. Never commit `.env`, tokens, databases, backups, virtualenvs, caches or bytecode. No package command sends mail, calls Alice or changes a remote account.
