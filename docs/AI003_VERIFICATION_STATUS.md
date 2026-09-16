# AI Career Agent - AI-003 verification status

| Поле | Значение |
|---|---|
| Version | 1.0 r1 / 2026-09-16 |
| Status | НУЖНА ПРОВЕРКА / NEEDS_VERIFICATION |
| Code baseline | main (33), 20947f2e015097010cbe33772f7662bef4503f37 |
| Target schema | 20260916_0017 |
| External acceptance | PENDING |
| Provider calls | NOT RUN; not required for reference mode |

## 1. Local checks

The final local suite was executed in four separate, non-overlapping partitions covering all 73 `tests/test_*.py` files. Each final partition exited zero. This is not a completed single-process full-suite run.

| Partition | Passed | Skipped | Passing subtests |
|---|---:|---:|---:|
| AI / benchmark / provider | 330 | 7 | 82 |
| Account / database / infrastructure | 138 | 8 | 0 |
| Profile / resume / privacy | 32 | 4 | 0 |
| Search / sync | 108 | 2 | 0 |
| **Total** | **608** | **21** | **82** |

The 21 skips include 13 entire Flask-dependent modules, not only individual test functions. Subtests are separate and not added to the passed-test count. Focused AI-003: **56 passed, 2 skipped**, already included above (41 service, 14 package, one SQLite migration test; Flask routes and PostgreSQL scenario skipped).

Additional local checks:
- Python compilation: 236 files; Jinja parsing: 35 templates; YAML parsing: CI, Compose, Render. PASS.
- AI-001/002/003, provider and benchmark source/package checks: PASS, including dependency-free execution. Accepted benchmark/prompts/policy preserved.
- SQLite 0016 -> 0017 -> 0016 -> 0017 migration and metadata checks: PASS in the migration tests.
- Offline Chromium/Jinja rendering: 36 layouts (nine states, widths 1440/768/390/320), no horizontal overflow; native required inputs, CSRF form fields and safe templates checked. PASS. Actual CSS was inlined; external requests were blocked and web fonts used fallbacks. This is **not Flask HTTP or account E2E**.
- Existing builder JavaScript script blocks are byte-identical to the input ZIP; the new interview uses native server forms, no new feature JavaScript.

Environment: Python 3.13.5, SQLAlchemy 2.0.50, Alembic 1.18.4, pytest 9.0.2. Pinned application dependencies were not changed. CI must repeat with its pinned requirements and Python/PostgreSQL environment.

Machine-readable measurements, reproducible per-partition commands and logs: `evidence/ai-003/local_verification.json`, `pytest_*.txt`, `static_checks.json`, `offline_ui_checks.json`. No GitHub or staging PASS is inferred.

## 2. Required external checks

GitHub ordinary CI with pinned requirements and PostgreSQL 17: PENDING. Real Flask HTTP/CSRF suite: PENDING in CI (Flask unavailable in local environment). Psycopg/PostgreSQL: PENDING. Container/backup integration: PENDING in CI. Render/Neon migration/current=expected 20260916_0017: PENDING. Owner browser branching/confirmation/relogin/stale/ownership/mobile/regression and review flag returned off: PENDING.

No billable Alice run, real-resume provider dispatch or remote deployment was performed. Public runtime remains closed by code defaults; the actual deployed status must be checked after deployment.

## 3. Accepted baseline versus candidate

AI-002 acceptance came from the supplied final documents: CI #270, accepted staging 0016 and owner review. It is not an AI-003 test. The original local full-suite attempt timed out and is not a passed baseline. Final local tests run in measured partitions, with skips recorded rather than treated as passes.

## 4. Known limits

Synthetic reference-only, pinned choices, no arbitrary free text or live multi-turn Alice. LEGAL-001 is still deferred. Verification email delivery remains unresolved. No new manual two-account proof exists until the owner supplies it. Do not close this package or start AI-004 without the required external acceptance.
