# AI Career Agent

## Current accepted package / AI-004

PLAN_CURRENT 1.5.7 / PROJECT_PASSPORT 2.74. AI-004 is ВЫПОЛНЕНО only in the synthetic/reference-only scope, on application `d5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4`, schema `20260916_0018`. Main CI #281: 804 passed; dedicated AI-004: 71 passed, no skips. Owner final review passed; no second active account exists, so manual two-account isolation is NOT RUN. Public AI remains manual/unavailable and session review is closed. Real backup/snapshot evidence and production recovery are not established by this acceptance.

This release changes documentation and its status guards only. See `docs/AI004_VERIFICATION_STATUS.md` for evidence and `docs/NEXT_PACKAGE_PREPARATION.md` for the unresolved AI-005/JOB-001 dependency; no next-package implementation or unapproved reorder is included.

<!-- ACA-CANONICAL-STATUS:START -->
## Canonical state / JOB-001 r1.1 REBUILT / 2026-09-17

| Field | Value |
|---|---|
| Current candidate | JOB-001 r1.1 REBUILT - НУЖНА ПРОВЕРКА / NEEDS_VERIFICATION |
| Verified GitHub baseline | `d5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4`; tree `53d86b0ff72f5090f214c20979df493e6f1f0ee3`; 565 files |
| Accepted foundation | AI-004 COMPLETE in synthetic/reference-only scope; prior accepted packages unchanged |
| Canonical versions | PLAN 1.6.0; PASSPORT 2.75; SOURCE_AUDIT 1.6.0 |
| Accepted staging | `20260916_0018`; owner-confirmed for AI-004, not a deployment of JOB-001 |
| Candidate migration | `20260917_0019`; new saved_vacancies and saved_vacancy_sources |
| Approved sequence | JOB-001 before AI-005; explicitly approved by the owner in this conversation |
| Rebuild provenance | The previous JOB-001 r1 bytes were unavailable. This is a newly implemented replacement, not a byte-identical reissue |
| Verification | New local measurements only; JOB-001 remote CI and staging acceptance remain NOT RUN |
| Publication | Local files only; no GitHub write, merge, workflow dispatch or deployment in this rebuild |
| Public AI | Disabled/manual; no new provider calls, keys, consent or legal activation |
| Remaining limits | No second active account; actual Neon backup/restore unconfirmed; email delivery and LEGAL-001 remain open |
<!-- ACA-CANONICAL-STATUS:END -->

## JOB-001 rebuilt candidate

Local candidate r1.1: see `docs/JOB001_IMPLEMENTATION.md`, `docs/JOB001_RUNBOOK.md` and `docs/JOB001_VERIFICATION_STATUS.md`. Do not upload the old AI-004 closure patch over this candidate. New migration0019 has not been applied to the real database. The historical section below describes the accepted AI-004 baseline, not acceptance of JOB-001.

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
