# AI Career Agent - AI-004 verification status

| Field | Value |
|---|---|
| Version | 1.0 r1 / 2026-09-16 |
| Status | НУЖНА ПРОВЕРКА / NEEDS_VERIFICATION |
| GitHub baseline | c683520058cc1f729c79ed49ac5c213811e4c9f3 |
| Target schema | 20260916_0018 |
| New external acceptance | PENDING |
| Paid provider execution | NOT RUN; not required for reference mode |

## 1. Verified starting state

Direct GitHub reads confirmed main/tree and CI #276 (run 35132463421) completed successfully for the exact baseline. Its Python tests job 104916531960 includes green AI-003, PostgreSQL, backup/restore, container and full-test steps. Paid jobs were skipped. A computed Git tree over all 527 local baseline files exactly matched the GitHub tree `6458daea23371dadfbbd49d830abcdde44df1293`. No ZIP freshness is guessed.

The final AI-003 1.5.5 documentation was not yet on main. Its already-confirmed owner acceptance is preserved and that documentation synchronization is included in this candidate. Neither this fact nor CI #276 is proof of the new AI-004 code.

## 2. Local measurements

Final measured command outputs and environment are recorded in `evidence/ai-004/local_verification.json`. New tests cover deterministic scoring/rounding/unknown semantics; strict fixed-fixture evidence; reference and fake-provider paths; immutable versions/replays/concurrent writes; source/integrity failures; privacy/export/delete; migration round trips; UI and package boundaries.

Flask/Flask-WTF/Flask-Limiter and Psycopg/PostgreSQL are not available in this local runtime. Installing the pinned missing packages was attempted and failed because no package source was available. The entire Flask route module and disposable PostgreSQL scenario are explicit skips, not passes. The installed GitHub CI environment must execute them.

### Final local result / 2026-09-16

| Partition | Passed | Skipped | Passing subtests |
|---|---:|---:|---:|
| ai_runtime | 193 | 7 | 0 |
| ai004 | 61 | 2 | 0 |
| ai_benchmark | 137 | 0 | 82 |
| profile_privacy | 32 | 4 | 0 |
| search_sync | 104 | 2 | 0 |
| foundation | 142 | 8 | 0 |
| Total | 669 | 23 | 82 |

All six non-overlapping partitions exited zero and cover all 78 test modules. The 82 subtests are separate, not added to 669. Focused AI-004 is 61 passed / 2 skipped and already included. The 23 skips include 14 entire Flask-dependent modules. Local third-party pytest plugins were disabled; this does not change repository CI or installed production requirements. Single-process/combined attempts exceeded execution limits; they are not a passed full-suite result.

Compilation/AST: 250 Python sources. Jinja parsing: 40 templates. CI/Compose/Render YAML parse: PASS. Offline actual-base-template/inline-existing-CSS Chromium checks: 36 layouts across nine states and widths1440/768/390/320, no horizontal overflow and no summary/notice overlap after the namespace fix. External requests/fonts were blocked; fonts used fallbacks. Required confirmation and CSRF form presence were checked. This is not Flask HTTP or real account E2E.

A local preview exposed a collision with the landing-page `.match-score` class; the new feature now consistently uses `.ai004-match-*` and a regression test. Old styles/templates are unchanged. The checker chain retains old source hashes and tests explicitly include the new successor boundary instead of dropping checks.

## 3. Required external gates

New ordinary GitHub CI and the AI-004 step: PENDING. Real Flask HTTP/CSRF and PostgreSQL/backup/container verification of this candidate: PENDING. Render/Neon target0018 deployment/readiness: PENDING. Owner private RU/EN reports, versions/relogin/deletion/export, mobile/core regressions and final closure/log review: PENDING. Manual two-account isolation: NOT RUN unless separately documented.

Actual production data/account deletion and live billable Alice run: NOT RUN. The last owner-accepted staging revision remains0017. Default closed AI settings are unchanged, but deployed status must be checked after the new deployment.

## 4. Limits

Pinned synthetic inputs only; reference outputs are not live provider responses. Fixed-fixture classification tests are not general extraction/semantic-quality validation. No provider prose is used as report fact. Evidence coverage is not statistical confidence or hiring probability. Missing evidence does not prove lack of ability. LEGAL-001 and email delivery remain unresolved. Do not announce a finished public/live AI-004 product from these local results.
