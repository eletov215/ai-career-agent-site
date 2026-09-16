# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние / 2026-09-16

| Поле | Значение |
|---|---|
| Current package | AI-003 - НУЖНА ПРОВЕРКА; synthetic/reference-only adaptive interview candidate r1 |
| Source code | Owner main (33).zip; archive comment 20947f2e015097010cbe33772f7662bef4503f37; SHA-256 3f46536638fb541310c15a5520dc5a445d4916d8af90baf14292c99866971533 |
| Canonical versions | PLAN 1.5.4; PASSPORT 2.71; SOURCE_AUDIT 1.5.4 |
| Completed AI foundation | AI-BENCH-001 / AI-PROVIDER-001 / AI-001 / AI-002 - ВЫПОЛНЕНО in accepted boundaries |
| LEGAL-001 | ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА; public real-data AI and paid launch remain blocked |
| Schema | Last accepted staging 20260915_0016; AI-003 target 20260916_0017, two additive tables; NOT YET verified on staging |
| Candidate boundary | Private RU/EN reference interviews; pinned choice IDs; persisted history; explicit confirmation into isolated synthetic draft; no provider call |
| Verification | Local evidence in AI003_VERIFICATION_STATUS; GitHub CI, PostgreSQL 17, Render and owner browser acceptance PENDING |
| Next action | Ordinary CI, backup, staging migration and private AI-003 review; then disable review flag; no AI-004 start before acceptance |
<!-- ACA-CANONICAL-STATUS:END -->

## 1. Product and runtime

Flask + Gunicorn (`app:app`), PostgreSQL through SQLAlchemy/Alembic, independent sync/privacy workers. Confirmed career profiles and editable resume drafts remain separate. HH, SuperJob, Reed and Trudvsem vacancy search is unchanged by AI-003. Do not create `app_fixed.py`.

## 2. AI-003 candidate

Read `docs/AI003_RUNBOOK.md` before deployment. This is a private synthetic/reference-only adaptive interview, not a live Alice conversation. It accepts pinned answer IDs, keeps history, and applies only explicitly selected reference statements to a newly created test draft after confirmation. No real profile is read or sent to a provider. The accepted benchmark and provider strategy remain unchanged.

```bash
python scripts/check_ai_provider_package.py
python scripts/check_ai_bench_package.py
python scripts/check_ai001_package.py
python scripts/check_ai002_package.py
python scripts/check_ai003_package.py
python -m pytest -q
python scripts/check_document_structure.py
python scripts/check_repository_hygiene.py
```

Ordinary CI installs pinned dependencies and runs PostgreSQL 17. Paid benchmark workflow inputs remain false. No new credentials are needed for this reference review. Full local results and skips are recorded in `docs/AI003_VERIFICATION_STATUS.md`.

## 3. Source of truth

The latest supplied GitHub archive is the code baseline. Owner final PDFs dated 2026-09-15 establish AI-002 acceptance and legal deferral, overriding stale Markdown in main (33). This candidate synchronizes repository Markdown to PLAN1.5.4 / PASSPORT2.71 / AUDIT1.5.4. Historical entries remain dated. See `docs/CANONICAL_DOCUMENTS.md` and `docs/SOURCE_AUDIT.md`.

## 4. Deployment and gates

Accepted staging: Render web + Neon PostgreSQL at `20260915_0016`. Candidate migration adds only two interview tables at `20260916_0017`; back up first. `AI_ENABLED=0`, `AI_KILL_SWITCH=1`, `AI_SYNTHETIC_ACCESS_ENABLED=0`, `AI_ANALYSIS_REVIEW_ENABLED=0` stay unchanged. `AI_INTERVIEW_REVIEW_ENABLED=0` is the new default. Only temporarily set it to `1` for verified allowlisted administrators during the runbook smoke. Return it to `0` afterward.

LEGAL-001 remains deferred and blocks public real-data AI, paid subscriptions and commercial launch. Verification email delivery remains unresolved. INFRA-001 and production restore/domain migration stay pre-release work. AI-004 is not started before AI-003 acceptance.

## 5. Upload and security

Full ZIP is a complete source snapshot; PATCH is an overlay of changed/new paths for main (33) only. Do not delete the repository or `.git` first. Preserve `.github/workflows/ci.yml` when uploading. Never commit `.env`, tokens, databases, backups, virtualenvs, caches or bytecode. No package command sends mail, calls Alice or changes a remote account.
