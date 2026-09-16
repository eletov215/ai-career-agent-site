# AI Career Agent - AI-002 / Patch and verification runbook

## 0. Accepted status / 2026-09-15

AI-002: **ВЫПОЛНЕНО** in synthetic/reference-only scope. Final owner-supplied documents dated 2026-09-15 establish CI #270 PASS after the import hotfix, Neon staging at `20260915_0016`, owner review/relogin persistence and the final conditional-actions UI smoke. `AI_ANALYSIS_REVIEW_ENABLED` was returned to disabled; `/api/ai/status` remained manual/unavailable. No new paid Alice call and no real resume dispatch were required. A post-UI-hotfix CI run number is not known; the current main (33) archive comment is recorded as source evidence, not a new CI claim.

The detailed reconstruction instructions below are historical AI-002 procedures. Current deployment target and review steps are in AI003_RUNBOOK; do not downgrade the current candidate to 0016 as an ordinary deployment step.


| Field | Value |
|---|---|
| Version | 1.0-r2 / 2026-09-15 |
| Package | AI-002 v1.5.2 rebuilt candidate |
| Source | main (32).zip / bc177dd |
| Schema | accepted 0015 -> candidate 0016 |

## 1. Install safely

Back up Neon before push: Render auto-deploy may apply migration. Do not delete the repository directory. Copy only contents inside the patch project folder over the clean main (32) tree; keep .git and secrets untouched. This patch is not for main (31) or earlier. No dependency or accepted benchmark prompt changes.

Keep AI_ENABLED=0, AI_KILL_SWITCH=1 and AI_SYNTHETIC_ACCESS_ENABLED=0. AI_ANALYSIS_REVIEW_ENABLED defaults false. Do not add Alice keys or change DATABASE_URL. Commit then run ordinary CI; both paid Alice job inputs remain false.

## 2. Automated verification

```
python scripts/check_ai002_package.py
python scripts/check_ai001_package.py
python scripts/check_ai_provider_package.py
python scripts/check_ai_bench_package.py
python -m pytest -q tests/test_ai002_service.py tests/test_ai002_routes.py tests/test_ai002_migration.py tests/test_ai002_package.py
python scripts/check_document_structure.py
```

Full CI supplies Flask and PostgreSQL dependencies absent locally where noted. Existing AI-001 migration tests target their own explicit 0015 revision; new tests verify 0015 -> 0016 and rollback without dropping older tables. Do not skip full regression/infrastructure/backup gates.

## 3. Staging review

After success, verify /health/ready reports current_revision=expected_revision=20260915_0016. /api/ai/status must stay manual and generation_available=false. Existing search/profile/resume/privacy flows should work unchanged. Default /ai-analysis must be 404.

For a separate private UI test, set only AI_ANALYSIS_REVIEW_ENABLED=1, restart, and use an existing verified allowlisted administrator. This does NOT authorize provider calls. Open /ai-analysis, save RU and EN reference reports, follow evidence links, accept/reject/reset a recommendation, verify stale conflicting forms return 409 and the report survives relogin/restart. Another account must not see that report. Export and delete a throwaway account to verify isolation. Then return AI_ANALYSIS_REVIEW_ENABLED=0. Do not share keys, passwords or database dumps in chat.

## 4. Rollback

Disable review writes, back up the database and explicitly preserve any report/review data. Downgrade to 20260914_0015 only after an explicit rollback decision; it deletes all three new tables and their contents. Then deploy the compatible prior application. Leaving schema 0016 with an application expecting exact 0015 is not a guaranteed healthy rollback. Never reset the database.
