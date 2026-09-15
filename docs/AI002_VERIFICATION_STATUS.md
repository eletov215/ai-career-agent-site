# AI Career Agent - AI-002 / Rebuild verification status

| Field | Value |
|---|---|
| Version | 1.0-r2 / 2026-09-15 |
| Status | NEEDS_VERIFICATION / НУЖНА ПРОВЕРКА |
| Source | main (32).zip / bc177dd |
| Migration | 20260915_0016, not yet applied on owner's staging |

## 1. Rebuild, not recovery evidence

The original AI-002 v1.5.2 delivery links were unavailable. Those claims do not establish saved code or test results. This is a separately reconstructed candidate r2. The definitive file list and actual local test results are in docs/evidence/ai-002/rebuild_verification.json. Previous AI-001 local/CI evidence is historical, not proof of AI-002.

## 2. External gates

GitHub CI for this patch: PENDING. Owner Neon migration/readiness: PENDING. Private reference UI, owner isolation and export/restart smoke: PENDING. New billable provider call: NOT RUN. Public real-data AI: NOT AUTHORIZED. LEGAL-001: deferred, not passed.

## 3. Acceptance boundary

The candidate provides only pinned synthetic analysis/report/review plumbing. Reference UI results are not new Alice outputs. New semantic checks do not validate arbitrary real resumes. AI-001 runtime and paid benchmark gates stay closed; no external tests are inferred from local checks. Do not mark AI-002 complete before required external evidence.


## 4. Actual local measurements / rebuilt r2

All 69 repository test modules were executed in four complete non-overlapping groups: 544 passed, 19 skipped, 82 subtests passed, no failures. Skipped Flask/Psycopg/PostgreSQL scenarios still require CI. A single-process full run timed out; it is not represented as a passed full run. An initial outdated PRIV migration head assertion was corrected to 0016, retaining its historical rollback checks.

After the final service/docs adjustments a relevant subset passed again: 105 passed, 2 skipped, 58 subtests. These are part of the above test coverage, not extra tests to add to the total. Dependency-free AI-002/AI-001/provider/benchmark gates, document structure, infra manifests and Python AST/Jinja parsing passed. No browser-render or real PostgreSQL result is claimed locally.
