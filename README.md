# AI Career Agent

## Current candidate / AI-005 r1

General owned letter documents, manual editor, reviewed versions, local extractive templates, comparison/TXT/privacy are implemented locally. Full AI-005 is IN_PROGRESS; r1 NEEDS_VERIFICATION and LIVE_NOT_ACCEPTED. General real-input Alice runtime is not integrated. Accepted0019 / proposed0020; new CI/deploy NOT RUN. See docs/AI005_SCOPE.md and docs/AI005_RUNBOOK.md. The following JOB-001 block is the accepted predecessor, not a claim that letters are complete.

## Current accepted package / JOB-001

PLAN_CURRENT1.6.1 / PROJECT_PASSPORT2.76. JOB-001 is ВЫПОЛНЕНО / COMPLETE on `c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c`, schema20260917_0019. Main CI283 succeeded; the owner confirmed stepwise and final staging checks. Saved vacancy snapshots, notes, search, export/delete and access boundaries are accepted. Optional manual and real-recovery gaps remain explicit in docs/JOB001_VERIFICATION_STATUS.md. Public AI remains manual/unavailable.

<!-- ACA-CANONICAL-STATUS:START -->
## Canonical state / JOB-001 accepted / 2026-09-17

| Field | Value |
|---|---|
| Current package | JOB-001 r1.1 REBUILT - ВЫПОЛНЕНО / COMPLETE; ordinary verified-account saved vacancies |
| Accepted foundation | AI-004 COMPLETE in synthetic/reference-only scope; previous package boundaries unchanged |
| Accepted code | `c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c`; tree `6bb34aba4c05213a3d68f784e9d9b385c6d577d3`; 608 source files |
| Canonical versions | PLAN 1.6.1; PASSPORT 2.76; SOURCE_AUDIT 1.6.1 |
| Accepted staging | `20260917_0019`; PostgreSQL persistent, current=expected, migrations.ok=true; owner-confirmed |
| Automated evidence | Main CI #283 / run 35219447896 / success; JOB-001, previous gates, PostgreSQL, backup/restore, containers and full tests |
| Manual evidence | Stepwise save/relogin, notes/conflicts, duplicates/filter, export/delete and final regression/access/log confirmations |
| Optional manual evidence | Two-account NOT RUN; legacy import and second-device results not separately confirmed; no deliberate restart claimed |
| Public AI | Disabled/manual; generation_available=false; existing AI-003/004 review gates closed, owner-confirmed |
| Next package | AI-005 preparation; JOB-001 dependency satisfied. Live input/quality/consent/legal activation remain separate |
| Recovery and other limits | Real Neon recovery point and production restore not evidenced; email delivery and LEGAL-001 stay open |
| Publication | This final documentation/status-guard update is local only; no new GitHub commit, CI or deploy claimed |
| Historical lineage | Accepted r1.1 REBUILT; equivalence to unavailable original r1 remains NOT ESTABLISHED |
<!-- ACA-CANONICAL-STATUS:END -->

This local closure changes only documentation/evidence and status guards. A new docs commit/CI is not claimed. AI-005 preparation follows the approved order; no new feature code or provider call is started. Do not overlay older closure/rebuild patches after this release.

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
