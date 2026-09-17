# AI Career Agent - JOB-001 verification status

| Field | Value |
|---|---|
| Release | 1.1 REBUILT / 2026-09-17 |
| Status | NEEDS_VERIFICATION |
| Baseline | d5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4 |
| Candidate schema | 20260917_0019 |
| Equality to lost r1 | NOT ESTABLISHED |
| New remote CI | NOT RUN |
| Deployment and browser acceptance | NOT RUN |
| Paid provider calls | NOT RUN, not required |

## 1. Evidence boundary

GitHub main and branch inventory were read again. Recomputed Git serialization over the preserved565-file baseline matches the remote tree exactly. The previously lost JOB-001 r1 code and test counts are not reused. Only commands actually executed during this rebuild are measured below. Existing main CI281/AI-004 acceptance remain historical baseline evidence.

## 2. Local environment and measurements

Final measurements are recorded in evidence/job-001/local_verification.json. All82 test modules are covered by six non-overlapping completed partitions:760 passed,25 skipped. The JOB-001 subset is83 passed,2 skipped and is already included. These are pytest terminal counts; extra unittest subcase XML entries are not added again. The local environment supplies SQLite, SQLAlchemy, Alembic, Jinja, pytest, Node and an offline browser. Flask/Flask-WTF/Flask-Limiter, psycopg, PostgreSQL and Docker are unavailable. A pinned dependency-install attempt failed on unavailable package network access. Whole Flask modules and PostgreSQL scenarios are explicit skips, not successes; the installed GitHub CI must execute them.

### Final partition results

| Partition | Passed | Skipped |
|---|---:|---:|
| job001 | 83 | 2 |
| ai_runtime | 262 | 9 |
| ai_benchmark | 137 | 0 |
| account_profile | 59 | 6 |
| search_sync | 104 | 2 |
| foundation | 115 | 6 |
| Total | 760 | 25 |

The skipped reports include15 entire Flask-dependent modules; a skipped module is not a successful execution of its tests. Local Python3.13.5 differs from the project's installed Python3.11 CI. The single full-process attempt timed out after120seconds and is not reported as passed. The final partitions all exited zero after fixing two inherited status/version assertion mismatches. No original-r1 test result is reused.

Static checks:264 Python AST parses before adding the optional UI helper,44 Jinja templates,3 YAML manifests, and node --check for the new JS passed. Offline actual-template/base-style rendering covered24 page/width combinations at320/390/768/1440 with no horizontal overflow. Separate isolated DOM/JS checks used supplied location/fetch/storage bindings to verify post-ack save display and confirmed partial legacy cleanup; they are NOT Flask HTTP, real network, or cross-device browser tests. External fonts were blocked and fallback fonts used. scripts/check_job001_offline_ui.py reproduces the optional local check with installed Chromium/Playwright.

## 3. Required external verification

Ordinary PR CI including the JOB-001 package/service/route/migration gates; the previous package protections; full pytest; PostgreSQL integration, encrypted backup/restore and container checks are pending. Deployment0019, real account search/save/relogin/cross-device behavior, notes conflicts, privacy/delete and regression/log checks remain to be completed under JOB001_RUNBOOK.md.

The owner has no second active account. Manual cross-account verification is NOT RUN; new automated tests use separate disposable owners and are not a substitute for a reported production test. Real Neon backup/snapshot and production restore have not been evidenced. Do not proceed to a schema-changing deployment by pretending those checks passed.

## 4. Limits

Only locally known source/cache states are shown; no live scheduled recheck. Legacy key recovery is bounded and can remain unresolved. Real-vacancy AI match/letters/tracker are excluded and no public AI switch is enabled. Native note edits are explicitly saved, not autosaved. Exact archive equality to the unavailable original cannot be established.
