# AI Career Agent - AI-004 verification status

| Field | Value |
|---|---|
| Version | 1.1 FINAL / 2026-09-17 |
| Status | ВЫПОЛНЕНО / COMPLETE in synthetic/reference-only scope |
| GitHub baseline | c683520058cc1f729c79ed49ac5c213811e4c9f3 |
| Target schema | 20260916_0018 |
| Accepted application | d5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4 |
| External acceptance | CI #280/#281 PASS and owner-confirmed final staging review |
| Manual two-account isolation | NOT RUN; no second active account |
| Paid provider execution | NOT RUN; not required for reference mode |

## 1. Historical verified starting state / 2026-09-16

Direct GitHub reads confirmed main/tree and CI #276 (run 35132463421) completed successfully for the exact baseline. Its Python tests job 104916531960 includes green AI-003, PostgreSQL, backup/restore, container and full-test steps. Paid jobs were skipped. A computed Git tree over all 527 local baseline files exactly matched the GitHub tree `6458daea23371dadfbbd49d830abcdde44df1293`. No ZIP freshness is guessed.

The final AI-003 1.5.5 documentation was not yet on main. Its already-confirmed owner acceptance is preserved and that documentation synchronization is included in the original r1 candidate. Neither this fact nor CI #276 is proof of the new AI-004 code.

## 2. Historical local measurements / r1 preparation

Final measured command outputs and environment are recorded in `evidence/ai-004/local_verification.json`. New tests cover deterministic scoring/rounding/unknown semantics; strict fixed-fixture evidence; reference and fake-provider paths; immutable versions/replays/concurrent writes; source/integrity failures; privacy/export/delete; migration round trips; UI and package boundaries.

Flask/Flask-WTF/Flask-Limiter and Psycopg/PostgreSQL are not available in this local runtime. Installing the pinned missing packages was attempted and failed because no package source was available. The entire Flask route module and disposable PostgreSQL scenario are explicit skips, not passes. They were subsequently executed in the installed GitHub CI environment; final results are recorded in section 3.

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

## 3. Final external acceptance

| Evidence | Result | Provenance / limits |
|---|---|---|
| Pull request | #38 merged; candidate 39229d8 -> main d5e0dac | GitHub direct read |
| PR CI #280 | PASS; run 35149229406 | Automated candidate verification |
| Main CI #281 | PASS; run 35151012823; Python job 104979035501 | Exact accepted main commit |
| Dedicated AI-004 tests | 71 passed in 6.83s; zero skips | Read from the actual CI log |
| Final full pytest | 804 collected, 804 passed in 80.40s; zero skips | Single completed CI run, not the historical local partitions |
| Flask HTTP / PostgreSQL | Executed and passed in CI | Includes route, migration and cross-owner tests |
| Encrypted backup / restore and Docker | CI gates PASS at schema0018 | Disposable CI data only; match tables in that dump had zero rows |
| Paid Alice jobs | Skipped | Not needed for reference review |
| Render/Neon readiness | current=expected=20260916_0018; migrations.ok=true | Owner-confirmed in this conversation |
| Public runtime | unavailable/manual; reason runtime_not_activated | Owner-confirmed after deployment and final review |

### 3.1 Owner-confirmed browser matrix

The owner confirmed each requested block, then explicitly confirmed the final block. The following are owner-reported staging observations, not assistant-run browser telemetry or a fresh read of production logs.

| Scenario | Recorded result |
|---|---|
| Admin session gate; synthetic-origin notice | PASS |
| RU: 67%, formula6/9, five requirements, mandatory Docker warning | PASS |
| EN: 71%, formula5/7, four requirements, mandatory Next.js warning | PASS |
| Source facts, origin, hashes and policy display | PASS |
| Refresh/relogin: same stored report and version | PASS |
| New form creates next version; old reports retained | PASS |
| GET refresh does not create another version | PASS; this is not a raw POST replay test |
| Export vacancy_matches / vacancy_match_series | PASS; private export not collected by assistant |
| Deletion confirmation, only selected report removed, old URL unavailable | PASS |
| Deleted version number not reused | PASS |
| Profile, resumes, autosave, PDF, search, dashboard, admin regressions | PASS |
| Prior AI-003 saved interview and closing its review | PASS |
| Closing AI-004 review: index/report/API denied; logout/login boundary | PASS |
| Final readiness/manual status; Render privacy/error log review | PASS, owner confirmation |
| Manual two-account isolation | NOT RUN: no second active account |

### 3.2 Separate automated evidence

The main CI suite includes both named tests:

- `tests/test_ai004_routes.py::test_different_allowlisted_admin_cannot_read_or_delete_other_reports`;
- `tests/test_ai004_service.py::test_cross_owner_read_delete_and_privacy_export`.

They establish automated cross-owner coverage, not manual two-account production evidence. The runbook expressly allows recording the unavailable second-account scenario as NOT RUN. Duplicate POST/replay and parallel operation semantics are covered by the automated `test_duplicate_operation_is_a_noop_and_cross_source_reuse_is_conflict` and `test_parallel_duplicate_creates_one_report_and_independent_requests_are_serialized` tests. No separate manual raw-request replay or deliberately triggered restart is inferred.

### 3.3 Recovery and evidence gaps

A real Neon snapshot/backup was discussed, but its creation and verification were not explicitly confirmed before merge. No snapshot ID, verified production backup or production restore drill is available. The release records this gap rather than retroactively marking it passed. This is separate from functional AI-004 acceptance and remains operational work before future migrations and in OPS-002/REL-001. A CI backup containing zero match rows does not establish recovery of populated production match history.

No real account was destructively deleted, no arbitrary real resume was sent to Alice, and no new paid provider run was required. Verification email delivery and LEGAL-001 remain unresolved. Exact dates/times of the owner's manual steps are not inferred from GitHub timestamps.

### 3.4 Closure decision

AI-004 is **ВЫПОЛНЕНО / COMPLETE** in its accepted synthetic/reference-only boundary. It is not general live candidate-vacancy matching. The publication of this documentation-only release is separate from the already accepted application; no later docs commit or new CI result is invented.

Evidence files: `evidence/ai-004/acceptance.json` and `evidence/ai-004/ci281_verified_excerpt.txt`.

## 4. Limits

Pinned synthetic inputs only; reference outputs are not live provider responses. Fixed-fixture classification tests are not general extraction/semantic-quality validation. No provider prose is used as report fact. Evidence coverage is not statistical confidence or hiring probability. Missing evidence does not prove lack of ability. LEGAL-001 and email delivery remain unresolved. This reference acceptance does not establish a finished public/live AI-004 product.

## 5. Documentation-closure checks / 2026-09-17

The closure synchronizes two status checkers and their existing negative-test files; runtime logic, workflows, dependencies, source hashes and migration0018 remain unchanged. Local closure suite: **118 passed, 2 skipped, 59 passing subtests**. These subtests are counted separately. The skipped items are the entire Flask-dependent AI-004 HTTP module and disposable PostgreSQL scenario in this local environment. They are not counted as local successes, even though the accepted r1 CI already exercised them.

The status guards now require recorded accepted-commit/CI/manual-runtime evidence and reject invented second-account or real-backup completion. They no longer insist on the old candidate status. All earlier provider/safety/source-integrity gates remain active. Local source/package/document/hygiene checks passed. A new remote CI for this documentation revision has not been run or inferred.

## 6. Source references and version history

- Main CI log: https://github.com/eletov215/ai-career-agent-site/actions/runs/35151012823/job/104979035501
- Accepted application: https://github.com/eletov215/ai-career-agent-site/commit/d5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4
- PR: https://github.com/eletov215/ai-career-agent-site/pull/38
- Owner evidence: stepwise and final acceptance messages in the current project conversation; second active account explicitly unavailable.
- Version 1.1 / 2026-09-17: closure evidence recorded; manual NOT RUN and recovery gaps preserved.
- Historical version 1.0 r1 / 2026-09-16: **NEEDS_VERIFICATION**, external gates **PENDING**, baseline **CI #276**. These are historical labels, not current status.
