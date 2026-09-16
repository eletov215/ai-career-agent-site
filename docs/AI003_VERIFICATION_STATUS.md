# AI Career Agent - AI-003 verification status

| Field | Value |
|---|---|
| Version | 1.1 FINAL / 2026-09-16 |
| Status | ВЫПОЛНЕНО / PASS in synthetic/reference-only scope |
| Source lineage | owner `ai-career-agent-site-main-2.zip` + r1.2 session-review hotfix |
| Accepted schema | 20260916_0017 |
| Public generation | Disabled / manual mode |
| Provider calls for acceptance | None; not required |

## 1. Local implementation evidence

The r1 implementation introduced the adaptive reference-interview foundation and migration `20260916_0017`. The measured local suite before external acceptance completed four non-overlapping partitions with **608 passed, 21 skipped and 82 passing subtests**. Focused AI-003 coverage was **56 passed, 2 skipped**; later r1.2 hotfix checks reported **61 passed, 2 skipped** in the locally available non-Flask suite. Python compilation, Jinja parsing, migration round-trip, package checks, repository hygiene and offline UI checks passed. Local skips were kept explicit and were not treated as external proof.

## 2. External CI and staging

The owner confirmed the AI-003 GitHub workflow passed green after deployment of the accepted hotfix line; the subsequent direct GitHub inspection identified CI #276 (run 35132463421) as successful for accepted r1.2 commit `c683520058cc1f729c79ed49ac5c213811e4c9f3`. This is a source verification, not a new AI-004 test. Earlier CI #274 established the 0017 candidate before the review-access hotfix sequence. Paid Alice Final / Live Yandex jobs were not required for this package.

Render/Neon `/health/ready` was confirmed with:

- `status=ok`;
- PostgreSQL persistent storage;
- `current_revision=20260916_0017`;
- `expected_revision=20260916_0017`;
- `migrations.ok=true`.

`/api/ai/status` remained closed throughout acceptance: `generation_available=false`, `mode=manual`, `reason=runtime_not_activated`.

## 3. Review-access hotfix history

The initial private route returned 404. The exact deployment-time cause was not established from a running-process diagnostic; it must not be treated as a proven Blueprint overwrite. r1.1 removed the hardcoded Render Blueprint value. A fresh owner GitHub ZIP then showed the r1.1 manifest was present, but the route was still operationally dependent on deployment-time flag propagation.

r1.2 therefore added `/ai-interview/review`: an active, verified `SEARCH_ADMIN_EMAILS` administrator may unlock the synthetic interview only for the current signed browser session. Non-admin access remains 404, CSRF protects the POST controls, logout/session rotation clears the unlock, and the optional global environment override remains default-off. This did not add a provider call, real-data input, schema change or public-AI activation.

The owner confirmed r1.2 opened the private interview successfully.

## 4. Owner browser acceptance

The owner confirmed the following production/staging scenarios work as designed:

1. RU adaptive branching: a vague answer asks for clarification; a concrete action advances to the result question.
2. Persistence: answers and current question survive refresh and logout/login; the saved interview resumes at the expected step.
3. Unsupported metric handling: entering `12` and then declining to confirm its period/source keeps that number out of the proposed final text.
4. Explicit control: unselected suggestions are not added; confirmation is required before writing a version; the career profile remains unchanged.
5. Confirmed metric path: a period/source-supported metric can appear in the final proposal.
6. Rewind/change path: changing an earlier answer invalidates the later active branch while preserving history in the event log.
7. Same-session stale-write protection: two browser tabs on the same interview cannot silently overwrite a newer revision.
8. Manual-builder conflict protection: if the linked synthetic draft is edited and synchronized in the normal builder, a stale interview confirmation is rejected and the manual edit is preserved.
9. EN reference scenario: adaptive flow, confirmed metric handling and final version creation work.
10. Core regression smoke: dashboard, profile, resumes/builder, preview/PDF, vacancies/search and logout/login remained operational.
11. Privacy integration: account export contains `resume_interviews`; deleting one synthetic interview draft removes only its associated interview data while other drafts/interviews remain intact.
12. Final closure: private review access was closed, `/ai-interview` returned 404 again, health stayed on 0017, AI status stayed manual/unavailable, and Render logs showed no new 500/Traceback/IntegrityError/migration errors or interview/resume text leakage according to the owner review.

A separate fresh two-account manual isolation run was not explicitly evidenced in chat. Ownership/isolation remains covered by the green automated route/service tests; this document does not invent a second-account manual proof.

## 5. Accepted boundary

AI-003 is complete only as a **synthetic/reference-only adaptive interview foundation**. It does not accept arbitrary free-form experience text, does not run a live multi-turn Alice conversation, does not attach to arbitrary real resume drafts, and does not authorize public real-data AI. Final text remains user-controlled and writes only to the isolated synthetic resume draft used by the review flow.

LEGAL-001 remains deferred and mandatory before public real-data AI, paid subscriptions or commercial release. Email-verification delivery remains a separate operational issue. The next technical package AI-004 uses directly verified GitHub main `c683520058cc1f729c79ed49ac5c213811e4c9f3`. Its new CI/staging checks are separate.
