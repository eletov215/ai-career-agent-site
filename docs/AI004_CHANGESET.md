# AI Career Agent - AI-004 changeset

| Field | Value |
|---|---|
| Version | 1.0 r1 / 2026-09-16 |
| Baseline | GitHub main c683520058cc1f729c79ed49ac5c213811e4c9f3 |
| Package | NEEDS_VERIFICATION |

## 1. Scope

New technical matching foundation plus pending AI-003 final-document synchronization. Two additive tables in0018. No source deletion, dependency update, accepted prompt/schema/evals change, new real-data input or public activation. Seven existing runtime paths have explicit reviewed hashes; new modules and tests are listed below.

The repository's historical package-checker test copies now include the AI-004 successor manifest. The old AI003 migration test explicitly targets0017 before asserting its two-table delta; the latest-head assertion elsewhere is0018. A stale negative provider-document-version fixture was aligned with the current version so it actually tests rejection rather than a no-op replacement. These are regression-test maintenance, not weakening scope or behavior tests.

## 2. Modified existing paths

- `.github/workflows/ci.yml`
- `README.md`
- `app.py`
- `database.py`
- `docs/AI002_VERIFICATION_STATUS.md`
- `docs/AI003_CHANGESET.md`
- `docs/AI003_IMPLEMENTATION.md`
- `docs/AI003_RUNBOOK.md`
- `docs/AI003_VERIFICATION_STATUS.md`
- `docs/CANONICAL_DOCUMENTS.md`
- `docs/CHANGELOG.md`
- `docs/PLAN_CURRENT.md`
- `docs/PROJECT_PASSPORT.md`
- `docs/ROADMAP.md`
- `docs/SOURCE_AUDIT.md`
- `models/__init__.py`
- `operations/backup.py`
- `repositories/privacy.py`
- `scripts/check_ai001_package.py`
- `scripts/check_ai002_package.py`
- `scripts/check_ai003_package.py`
- `scripts/check_ai_provider_package.py`
- `scripts/check_document_structure.py`
- `services/privacy.py`
- `services/storage.py`
- `tests/test_ai001_package.py`
- `tests/test_ai002_package.py`
- `tests/test_ai003_migration.py`
- `tests/test_ai003_package.py`
- `tests/test_ai_provider_policy.py`
- `tests/test_priv001_migration.py`

## 3. New paths

- `docs/AI004_CHANGESET.md`
- `docs/AI004_IMPLEMENTATION.md`
- `docs/AI004_RUNBOOK.md`
- `docs/AI004_VERIFICATION_STATUS.md`
- `docs/evidence/ai-004/baseline_files_sha256.json`
- `docs/evidence/ai-004/change_boundary.json`
- `docs/evidence/ai-004/local_verification.json`
- `docs/evidence/ai-004/offline_ui_checks.json`
- `docs/evidence/ai-004/pytest_ai004.txt`
- `docs/evidence/ai-004/pytest_ai_benchmark.txt`
- `docs/evidence/ai-004/pytest_ai_runtime.txt`
- `docs/evidence/ai-004/pytest_foundation.txt`
- `docs/evidence/ai-004/pytest_profile_privacy.txt`
- `docs/evidence/ai-004/pytest_search_sync.txt`
- `docs/evidence/ai-004/source_audit.json`
- `docs/evidence/ai-004/static_checks.json`
- `domain/vacancy_match.py`
- `migrations/versions/20260916_0018_vacancy_match.py`
- `models/vacancy_match.py`
- `prompts/matching/reference/vacancy-match-en-01.json`
- `prompts/matching/reference/vacancy-match-ru-01.json`
- `repositories/vacancy_match.py`
- `routes/vacancy_match.py`
- `scripts/check_ai004_package.py`
- `services/ai/match_labels.py`
- `services/ai/match_reference_manifest.json`
- `services/ai/match_validation.py`
- `services/vacancy_match.py`
- `static/vacancy_match.css`
- `templates/matching/detail.html`
- `templates/matching/error.html`
- `templates/matching/index.html`
- `templates/matching/review_gate.html`
- `tests/test_ai004_migration.py`
- `tests/test_ai004_package.py`
- `tests/test_ai004_routes.py`
- `tests/test_ai004_scoring.py`
- `tests/test_ai004_service.py`

## 4. Installation and rollback

PATCH is an overlay only for the verified source commit; FULL is a complete candidate with one project folder. Never apply the older AI003 final patch after AI004. No remote commit/deploy is performed by these files. Follow AI004_RUNBOOK.md: backup before automatic migration, new ordinary CI, private review, public runtime closed. Downgrade0018 drops matching reports/series, so preserve a backup and coordinate old exact-revision readiness.

## Documentation closure / 1.5.7 / 2026-09-17

The accepted 565-file application tree `53d86b0ff72f5090f214c20979df493e6f1f0ee3` at main `d5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4` is unchanged by runtime logic. The final release updates canonical Markdown and adds acceptance evidence and next-package readiness notes only. No migrations, prompts, workflow, dependencies, application sources or assets change. Two documentation-status checkers and their two existing test files are updated to require the recorded closure evidence, not the old candidate status. The separate generated PATCH manifest contains the exact documentation paths/hashes; it is not the original AI-004 31-modified/38-added code delta. A later documentation merge has not been inferred.
