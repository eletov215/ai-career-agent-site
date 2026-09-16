# AI-003 r1 - measured changes against main (33)

Date: 2026-09-16. Status: NEEDS_VERIFICATION, not staging acceptance.

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

Runtime changes add private reference interviews, two additive tables, owner-scoped history and confirmation, privacy export/deletion and guarded builder integration. Existing benchmark/provider contracts and dependencies are unchanged. Source gates now recognize the strictly measured AI-003 successor. Documentation separates accepted AI-002 / 0016 from this candidate / 0017.

The FULL ZIP has one `ai-career-agent-site-main/` project folder. Upload the contents of that folder to the repository root, not as a nested second project. The PATCH ZIP contains modified/new paths relative to the repository root, with no enclosing project folder. It is an alternative overlay ONLY for unchanged main (33). Applying PATCH to that baseline must produce byte-identical contents to FULL. Neither archive contains local caches, environments, databases or credentials. Do not delete `.git`, remote secrets or production data.

Local measurements: `docs/evidence/ai-003/local_verification.json`. User acceptance procedure: `docs/AI003_RUNBOOK.md`. GitHub/Render/Neon acceptance is still pending.
