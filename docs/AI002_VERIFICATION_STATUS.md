# AI Career Agent - AI-002 / Rebuild verification status

| Field | Value |
|---|---|
| Version | 1.0-r2 + ci-import-hotfix-r1 / 2026-09-15 |
| Status | NEEDS_VERIFICATION / НУЖНА ПРОВЕРКА |
| Source | main (32).zip / bc177dd |
| Migration | 20260915_0016, not yet applied on owner's staging |

## 1. Rebuild, not recovery evidence

The original AI-002 v1.5.2 delivery links were unavailable. Those claims do not establish saved code or test results. This is a separately reconstructed candidate r2. The definitive file list and actual local test results are in docs/evidence/ai-002/rebuild_verification.json. Previous AI-001 local/CI evidence is historical, not proof of AI-002.

## 2. External gates

GitHub CI for rebuild-r2: FAILED at route-test collection (owner screenshot). GitHub CI for ci-import-hotfix-r1: PENDING. Owner Neon migration/readiness: PENDING. Private reference UI, owner isolation and export/restart smoke: PENDING. New billable provider call: NOT RUN. Public real-data AI: NOT AUTHORIZED. LEGAL-001: deferred, not passed.

## 3. Acceptance boundary

The candidate provides only pinned synthetic analysis/report/review plumbing. Reference UI results are not new Alice outputs. New semantic checks do not validate arbitrary real resumes. AI-001 runtime and paid benchmark gates stay closed; no external tests are inferred from local checks. Do not mark AI-002 complete before required external evidence.


## 4. Actual local measurements / rebuilt r2

All 69 repository test modules were executed in four complete non-overlapping groups: 544 passed, 19 skipped, 82 subtests passed, no failures. Skipped Flask/Psycopg/PostgreSQL scenarios still require CI. A single-process full run timed out; it is not represented as a passed full run. An initial outdated PRIV migration head assertion was corrected to 0016, retaining its historical rollback checks.

After the final service/docs adjustments a relevant subset passed again: 105 passed, 2 skipped, 58 subtests. These are part of the above test coverage, not extra tests to add to the total. Dependency-free AI-002/AI-001/provider/benchmark gates, document structure, infra manifests and Python AST/Jinja parsing passed. No browser-render or real PostgreSQL result is claimed locally.


## 5. CI import failure and narrow hotfix / 2026-09-15

Owner-supplied CI screenshot shows `check_ai002_package.py` returning `ok: true`, then pytest failing while collecting `tests/test_ai002_routes.py` at `from test_ai002_service import env`. The error is `ModuleNotFoundError: No module named 'test_ai002_service'`; it does not establish an application or database failure. Steps below that failure were skipped and are not accepted as passed.

`tests/__init__.py` makes the tests a package. The shared fixture import must therefore be `from tests.test_ai002_service import env` (or a correct relative import), without relying on a manually modified `PYTHONPATH`.

The previous local run skipped the route module at `pytest.importorskip('flask')` before executing this faulty import. That environment-dependent skip hid the collection defect; the previous local pass counts did not validate the Flask route tests.

This hotfix changes the import and adds two protections: a dependency-free AST guard in the AI-002 package checker and a subprocess regression that executes the actual fixture-import statement from the route-test file from the repository root. The regression does not need Flask and does not pretend to execute the route suite. Reintroducing the old import fails both checks, as verified by a temporary mutation that was reverted before packaging.

## 6. Hotfix local verification and unchanged boundary

- Exact AI-002 CI command: 55 passed, 2 skipped (Flask route module and disposable PostgreSQL integration).
- AI-002 package tests: 13 passed, included in the 55 above.
- AI-001 package/runtime/migration/route subset: 81 passed, 3 skipped.
- Accepted AI-BENCH tests: 90 passed, 24 subtests passed.
- AI-002 / AI-001 / AI-PROVIDER / AI-BENCH package scripts passed with `python -S` (without site packages).
- Restoring the original import is rejected by both the fresh-process fixture regression and the dependency-free package guard.

The three executed suites are disjoint: 226 passed and 5 skip entries in total. These are focused checks, not a claim of a new full-suite run. Python 3.13.5 / pytest 9.0.2 / SQLAlchemy 2.0.50 were available locally; the pinned CI Python/dependency environment must still run. Flask/Psycopg and a PostgreSQL server were not available, and attempted dependency installation did not succeed.

No runtime application, schema, AI prompt, feature flag, dependency list or workflow configuration changes are included. Code revision remains `20260915_0016`; this is not confirmation that this schema is deployed on the owner's Neon. Public AI remains off, LEGAL-001 remains deferred, and a new paid Alice call was NOT RUN. AI-002 remains NEEDS_VERIFICATION pending ordinary green CI and required staging checks.

Machine-readable evidence: `docs/evidence/ai-002/ci_import_hotfix_r1.json`.

Technical reference for package test imports: https://docs.pytest.org/en/stable/explanation/pythonpath.html (checked 2026-09-15).
