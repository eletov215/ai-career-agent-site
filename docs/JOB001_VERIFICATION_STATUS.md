# AI Career Agent - JOB-001 verification status

| Field | Value |
|---|---|
| Release | 1.2 FINAL / 2026-09-17; accepts r1.1 REBUILT |
| Status | ВЫПОЛНЕНО / COMPLETE in the server-saved vacancy scope |
| Accepted application | `c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c` |
| Accepted tree | `6bb34aba4c05213a3d68f784e9d9b385c6d577d3`; 608 source files |
| Accepted staging schema | `20260917_0019`; owner-confirmed |
| External CI | Main #283 / run 35219447896 / completed / success |
| Public AI | Unavailable/manual; no live provider activation |
| Publication of this closure | Local only; no new commit or new remote CI claimed |

## 1. Decision, scope and evidence sources

The owner confirmed each requested manual block, then stated that all final checks passed. JOB-001 is accepted as ordinary verified-account server-saved vacancies, including the first stored search snapshot, known source aliases, private notes, access rules and privacy operations. It is not a live AI matching or cover-letter release. The actual GitHub main and commit/tree were read again; the preserved rebuilt FULL materializes all608 files into the exact accepted Git tree. Equivalence to the unavailable original r1 remains NOT ESTABLISHED.

Sources are separated: GitHub workflow/job-step reads establish CI status; the owner's confirmations establish the described staging/browser/log observations. No production browser session, private account export or raw Render log was collected by the assistant. The older r1.1 local results below are historical measurements and are not a replacement for the new external evidence.

## 2. Historical local rebuild measurements

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


## 3. Verified GitHub CI of the accepted application

| Gate | Observed result |
|---|---|
| Main commit | `c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c` |
| Workflow | CI #283 / run35219447896; push to main; completed/success |
| Python job | 105195697162; success |
| JOB-001 controls | Verify JOB-001 server-saved vacancy controls; success |
| PostgreSQL | Migration/integration steps success |
| Backup/restore | Encrypted PostgreSQL test backup/restore step success; not real Neon recovery |
| Earlier packages and infrastructure | Previous package gates, Compose, container builds/smoke and Run tests success |
| AI benchmark package gate | Success |
| Billable Alice / Live Yandex | Skipped; no new paid calls required |

These are directly read workflow and job-step conclusions. Exact passed/skipped test counts for CI283 were not separately extracted, so no numerical total is invented. The successful CI belongs to the accepted application, not this later local documentation/status-guard update. CI source: https://github.com/eletov215/ai-career-agent-site/actions/runs/35219447896. A sanitized field summary is in evidence/job-001/ci283_verified_summary.json.

### 3.1 Owner-confirmed manual matrix

| Scenario | Result |
|---|---|
| PostgreSQL persistent; current=expected=20260917_0019; migrations.ok=true | PASS - owner confirmation |
| generation_available=false; mode=manual; reason=runtime_not_activated | PASS - owner confirmation |
| Fresh search save; available title, employer, content and sources retained | PASS - owner confirmation |
| Saved record and note remain after refresh and logout/login | PASS - owner confirmation |
| Explicit note save, refresh and editing after conflict | PASS - owner confirmation |
| Same-object stale editor refuses overwrite and preserves the newer note | PASS - owner confirmation |
| Repeated source save returns the same saved ID and retains the private note | PASS - owner confirmation |
| Saved-library filter by note/title/employer, empty result and reset | PASS - owner confirmation |
| saved_vacancies and saved_vacancy_sources present; note matches the saved text | PASS - owner confirmation |
| An older delete form cannot remove a record with a newer note | PASS - owner confirmation |
| Confirmation required; only selected object removed; detail/API unavailable | PASS - owner confirmation |
| Anonymous pages redirect to login; private API refuses anonymous read | PASS - owner confirmation |
| Dashboard/profile/resumes/builder/preview/PDF/search/admin and prior AI histories | PASS - owner confirmation |
| Final readiness/manual mode, closed AI review gates and Render log review | PASS - owner confirmation |

The group containing optional second-device testing was confirmed generally; no distinct device/result was supplied. The last group containing optional legacy transfer was also confirmed generally without identifying whether the panel existed or whether an import occurred. Neither is recorded as a separate manual PASS. This does not invalidate the unambiguous required scenarios above.

### 3.2 Explicit manual exclusions

| Scenario | Recorded status and reason |
|---|---|
| Cross-account isolation | NOT RUN; no second active account, explicitly stated by the owner |
| Transfer of old browser marks | NOT SEPARATELY CONFIRMED; actual panel/import result not identified |
| Second device | NOT SEPARATELY CONFIRMED; general group confirmation only |
| Intentional service restart | NOT RUN; refresh or login is not a restart |
| More than20 saved items / expired search form | NOT SEPARATELY CONFIRMED; no manufactured production workload |
| Real cache purge / destructive account delete | NOT RUN; covered on disposable automated data |

### 3.3 Separate automated coverage

The accepted test sources contain the following named cases, included in the successful JOB-001 and full-test gates:

- `tests/test_job001_routes.py::test_cross_owner_reads_notes_deletion_and_reference_fail`.
- `tests/test_job001_service.py::test_owner_reference_and_read_edit_delete_export_are_isolated`.
- `tests/test_job001_routes.py::test_legacy_needs_explicit_confirmation_and_is_partial`.
- `tests/test_job001_service.py::test_legacy_only_explicit_exact_matches_and_partial_results`.
- `tests/test_job001_service.py::test_server_snapshot_persists_after_cache_cleanup_and_reconnect`.
- `tests/test_job001_service.py::test_signed_reference_expiration_and_tampering`.
- `tests/test_job001_service.py::test_limit_search_paging_and_literal_wildcards`.
- `tests/test_job001_service.py::test_composite_owner_fk_and_user_deletion_cascade`.

They are automatic test evidence, not manually observed operations on real accounts. Search TTL, bounded import, conservative source states and cascade limits do not require modifying production data to manufacture a manual pass.

## 4. Operational gaps and remaining product boundaries

A pre-deployment real Neon backup/snapshot was discussed but its creation and identifier were never separately confirmed. No production restore drill is evidenced. This omission is recorded, not retroactively marked passed; a future schema-changing deployment requires a confirmed recovery point. Actual restore remains OPS-002/REL-001. CI backup/restore is a test-environment result only.

Source status is local/cache knowledge, not a scheduled live check. Legacy transfer is explicit, bounded and may leave unresolved keys. No real vacancy receives the AI-004 fixture's67/71 score. No letter, application tracker or automatic application is implemented here. Email delivery and LEGAL-001 remain open; accepted limited AI001..004 functions are not a public/live-product approval.

## 5. Closure delta, checks and rollback

This closure changes documentation, acceptance evidence and status-checker tests only. Application logic, frontend, CI workflow, dependencies, provider policy/contracts and database revision0019 are preserved byte-for-byte. The new local closure subset passed167 tests, with2 skips and62 passing subtests counted separately. The skips are the entire Flask-dependent JOB-001 route module and the disposable PostgreSQL scenario. This is not a new full-suite or remote CI result. Initial stale version/status guard failures were corrected and the stated subset rerun successfully; commands and limits are in evidence/job-001/closure_checks.json. Remote CI of these changed status guards remains NOT RUN until publication.

Reverting only this documentation/status-guard release requires no database downgrade. An application rollback from0019 is separate and destructive to saved snapshots/notes/source aliases; follow JOB001_RUNBOOK and preserve a verified recovery point first. No rollback is part of ordinary acceptance.

## 6. Next step and version history

AI-005 follows the approved sequence. JOB-001 is no longer its missing saved-vacancy prerequisite. The next implementation still needs an input/provenance/ownership and quality/real-data/consent audit; public activation is not authorized. No next-package code is started by this closure.

1.2 FINAL / 2026-09-17: exact main CI283 and owner final acceptance recorded; manual exceptions and recovery gaps explicit. 1.1 REBUILT / 2026-09-17: local candidate NEEDS_VERIFICATION; historical760 passed/25 skipped, including83/2 for JOB-001. The lost r1 results remain excluded.
