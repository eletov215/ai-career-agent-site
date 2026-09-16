# AI-003 r1 - measured changes against main (33)

Date: 2026-09-16. Final status: ACCEPTED / COMPLETE in synthetic/reference-only scope.

- Input files: **491** (directories excluded).
- Existing files modified: **35**.
- Files added: **35**.
- Files deleted: **0**.
- Input files preserved byte-for-byte: **456**.
- Total full-package files: **526**.
- PATCH files: **70**.

The original archive is SHA-256 `3f46536638fb541310c15a5520dc5a445d4916d8af90baf14292c99866971533`; its literal comment/commit is `20947f2e015097010cbe33772f7662bef4503f37`. These do not assert a new remote CI run.

## Existing files modified

- `.github/workflows/ci.yml`
- `README.md`
- `app.py`
- `compose.yaml`
- `config.py`
- `database.py`
- `docs/AI002_IMPLEMENTATION.md`
- `docs/AI002_RUNBOOK.md`
- `docs/AI002_VERIFICATION_STATUS.md`
- `docs/CANONICAL_DOCUMENTS.md`
- `docs/CHANGELOG.md`
- `docs/LEGAL001_DEFERRED_DECISION.md`
- `docs/PLAN_CURRENT.md`
- `docs/PROJECT_PASSPORT.md`
- `docs/ROADMAP.md`
- `docs/SOURCE_AUDIT.md`
- `infra/vps/.env.example`
- `models/__init__.py`
- `operations/backup.py`
- `render.yaml`
- `repositories/privacy.py`
- `routes/resume_drafts.py`
- `scripts/check_ai001_package.py`
- `scripts/check_ai002_package.py`
- `scripts/check_ai_provider_package.py`
- `scripts/check_document_structure.py`
- `services/privacy.py`
- `services/storage.py`
- `templates/resume_builder.html`
- `tests/conftest.py`
- `tests/test_ai001_package.py`
- `tests/test_ai002_migration.py`
- `tests/test_ai002_package.py`
- `tests/test_ai_provider_policy.py`
- `tests/test_priv001_migration.py`

## New files

- `docs/AI003_CHANGESET.md`
- `docs/AI003_IMPLEMENTATION.md`
- `docs/AI003_RUNBOOK.md`
- `docs/AI003_VERIFICATION_STATUS.md`
- `docs/evidence/ai-003/baseline_files_sha256.json`
- `docs/evidence/ai-003/change_boundary.json`
- `docs/evidence/ai-003/local_verification.json`
- `docs/evidence/ai-003/offline_ui_checks.json`
- `docs/evidence/ai-003/pytest_account_infra.txt`
- `docs/evidence/ai-003/pytest_ai.txt`
- `docs/evidence/ai-003/pytest_focused.txt`
- `docs/evidence/ai-003/pytest_profile_privacy.txt`
- `docs/evidence/ai-003/pytest_search_sync.txt`
- `docs/evidence/ai-003/static_checks.json`
- `domain/resume_interview.py`
- `migrations/versions/20260916_0017_resume_interview.py`
- `models/resume_interview.py`
- `prompts/interview/reference/resume-interview-en-01.json`
- `prompts/interview/reference/resume-interview-ru-01.json`
- `repositories/resume_interview.py`
- `routes/resume_interview.py`
- `schemas/interview/reference_v1.schema.json`
- `scripts/check_ai003_package.py`
- `services/ai/interview_labels.py`
- `services/ai/interview_reference.py`
- `services/ai/interview_reference_manifest.json`
- `services/resume_interview.py`
- `static/resume_interview.css`
- `templates/interview/detail.html`
- `templates/interview/error.html`
- `templates/interview/index.html`
- `tests/test_ai003_migration.py`
- `tests/test_ai003_package.py`
- `tests/test_ai003_routes.py`
- `tests/test_ai003_service.py`

## Scope and installation

Runtime changes add private reference interviews, two additive tables, owner-scoped history and confirmation, privacy export/deletion and guarded builder integration. Existing benchmark/provider contracts and dependencies are unchanged. Source gates now recognize the strictly measured AI-003 successor. Documentation separates accepted AI-002 / 0016 from accepted AI-003 / 0017 and preserves the synthetic/reference-only boundary.

The FULL ZIP has one `ai-career-agent-site-main/` project folder. Upload the contents of that folder to the repository root, not as a nested second project. The PATCH ZIP contains modified/new paths relative to the repository root, with no enclosing project folder. It is an alternative overlay ONLY for unchanged main (33). Applying PATCH to that baseline must produce byte-identical contents to FULL. Neither archive contains local caches, environments, databases or credentials. Do not delete `.git`, remote secrets or production data.

Local measurements: `docs/evidence/ai-003/local_verification.json`. User acceptance procedure: `docs/AI003_RUNBOOK.md`. GitHub/Render/Neon and owner browser acceptance are recorded in `AI003_VERIFICATION_STATUS.md` v1.1 FINAL.

## r1.2 hotfix delta against the owner-supplied current GitHub ZIP

The r1.2 delivery is based on `ai-career-agent-site-main-2.zip` (SHA-256 `ce5fe48c531dba9dc57e982e1f2223be14b767bac720c309ffc3ce93ab88fa9a`), supplied after the owner reported that r1.1 CI/deploy remained 404. The repository already contains the r1.1 Render manifest hotfix. After excluding generated `__pycache__`, `.pyc` and `.pytest_cache` artifacts from the comparison, the current GitHub snapshot contains **526** project files. r1.2 contains **527**: **8 existing project files modified, 1 new file added, 0 project source files deleted**. The new file is `templates/interview/review_gate.html`. Database revision remains `20260916_0017`.

The eight modified paths are `routes/resume_interview.py`, `scripts/check_ai003_package.py`, `tests/test_ai003_routes.py`, `docs/AI003_CHANGESET.md`, `docs/AI003_IMPLEMENTATION.md`, `docs/AI003_RUNBOOK.md`, `docs/AI003_VERIFICATION_STATUS.md` and `docs/CHANGELOG.md`. Generated cache artifacts present in the supplied ZIP are intentionally excluded from the delivery archives and are not treated as project-source deletions.

## Final closure delta after r1.2

After the owner completed the acceptance run, the final documentation/checker synchronization changes 14 files relative to the delivered r1.2 code snapshot: README, ten canonical/package Markdown files, `AI003_CHANGESET.md` itself, and the AI-003 / provider package checkers. Runtime interview code, migration 0017, templates, CSS and database behavior are unchanged by this closure-only delta.

The closure records staging 0017, public AI still disabled/manual, RU/EN browser acceptance, history/rewind/stale/conflict/privacy/core regressions, final private-review shutdown, and the fact that the exact final r1.2 Git SHA/run number was not supplied. AI-004 becomes the next technical package after a fresh GitHub ZIP is supplied and inspected.
