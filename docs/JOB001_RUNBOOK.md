# AI Career Agent - JOB-001 rollout and verification

| Field | Value |
|---|---|
| Version | 1.2 FINAL / 2026-09-17; accepted r1.1 REBUILT |
| Status | ВЫПОЛНЕНО / COMPLETE |
| Accepted schema | 20260917_0019 |
| Current action | Local final documentation; accepted code already on main |

## Acceptance note / 2026-09-17

Main `c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c` / CI283 and the owner's final staging confirmation establish JOB-001 acceptance at0019. The original r1.1 REBUILT procedure and design below remain a historical implementation/regression reference, not a request to repeat accepted tests. Manual two-account isolation is NOT RUN; legacy transfer and second-device results are not separately confirmed. Real Neon recovery-point creation remains NOT EVIDENCED. See JOB001_VERIFICATION_STATUS.md for the exact matrix. This local closure changes no application logic or migration and performs no remote write.

## 1. Publication and recovery gate

Use the rebuilt PATCH against verified main d5e0dac2ba87d4d7e14fc5b48fbb6b9182c885a4, or the equivalent FULL project contents. Recheck any intervening main changes before applying. Do not overlay the previous AI-004 FINAL patch afterwards. Do not upload .env, keys, databases, account exports, backups or local caches.

Publish only on the owner's subsequent instruction. Use a separate branch/PR and ordinary CI, including Verify JOB-001 server saved vacancies controls. The existing optional paid Alice/Live Yandex jobs must remain off. Do not merge on a partial green result or treat old CI281 as new JOB-001 evidence.

Before migration/deployment, record a confirmed recovery point for the real Neon database. Its earlier creation is not evidenced. Restoring an account export is not a database backup. Do not reset/stamp Alembic or run downgrade as a routine test. New variables/keys are not needed; public AI remains disabled/manual.

## 2. Deployment checks

After approved CI and deployment, /health/ready must return PostgreSQL/persistent, status=ok, current_revision=expected_revision=20260917_0019 and migrations.ok=true. /api/ai/status remains generation_available=false, mode=manual, reason=runtime_not_activated. Log the exact deployed commit and CI run separately from this document.

## 3. Save, replay, persistence and source content

Log in with the existing active verified account. Run a fresh normal /vacancies search. Save one vacancy, open /saved-vacancies, and compare its employer/title/available description/requirements/salary/source links to the server search example. A saved snapshot is not a new source fetch. Repeat the same save; the list must contain one object, preserving note and first snapshot.

Refresh, sign out/in, and open the same saved URL. Verify it persists. Test a second device in the same account when available. If not run, record it explicitly; never substitute a refresh for a cross-device or intentional restart test. A controlled service restart may be tested only when appropriate; it is not implied by normal login.

Expired form: keeping a search page beyond30minutes or search snapshot TTL may reject a save with a request to repeat search; no bogus success. Exact malformed-reference and raw-payload attempts are automated cases, not instructions to alter the production database.

## 4. Notes and two tabs

Open the SAME saved URL in two tabs. Save a visible note in tab1. Submit the older tab2 form without refreshing. Expect409 conflict preserving tab1's note and displaying tab2's unsaved text for manual recovery. Reload and make a new explicit edit; no-op save preserves revision. A stale delete form also must not erase a newer note silently.

Filter your library by a word in title/company/location/note; check results and pagination when enough entries exist. No need to create hundreds of vacancies solely for the manual check; boundaries are automated tests.

## 5. Source state and old marks

The snapshot remains even when local search data expire. A missing cache state is not a claim that the job has closed. No manual production cache deletion is required; cache purge and explicit closed states are tested on disposable databases. Do not alter provider data to manufacture a manual pass.

If existing legacy browser marks exist, inspect the import panel. Without confirmation, do not import. With confirmation, only exact resolvable records are saved; unresolved marks remain. Repeat should not create duplicates. If no old marks are available, record this manual subcase as NOT RUN and cite automated recovery tests. Never assign unknown old marks to another person's account.

## 6. Export, ownership and deletion

Use /privacy-center to export privately. data.json must contain saved_vacancies and saved_vacancy_sources. Do not share the ZIP or personal content with the assistant. Check only the current owner's saved objects and notes. Password/session/OAuth secrets and internal signing keys must not appear.

Delete one unwanted saved object. Without the confirmation checkbox it must not delete; with confirmation only that item and its alias rows disappear. Its old detail/API URL becomes404, while another saved item/profile/resume remains. A later fresh search save may create a new object. Never delete the real account for this acceptance; account cascade is tested on disposable data.

A second already-active verified account may test foreign detail/API/note/delete access. Without one, record manual isolation NOT RUN and keep automated ownership evidence separate. Logout redirects private page reads to login and returns401 for private API reads; these are not failures.

## 7. Regression and logs

Verify /dashboard, /profile, /resumes, a test draft autosave, preview/PDF, normal /vacancies search and /admin/sources. Briefly reopen prior AI-003/004 reference flows only as needed, confirm saved history and close their session review again. There is no review switch to turn off for ordinary saved vacancies. Do not change AI flags.

Review Render logs for unexpected500/Traceback/IntegrityError/migration errors and leaked resume/note/token/connection contents; do not send raw logs with secrets. Repeat readiness0019/manual status. Acceptance requires exact new CI plus owner observations; code delivery alone is not COMPLETE.

## 8. Rollback

Stop writes and preserve a verified backup including populated saved objects, notes and sources before any destructive rollback. Controlled0019->0018 drops both new saved tables. Coordinate compatible application rollback because old releases require exact revision0018. Do not revert application code blindly while keeping an unexplained0019 schema mismatch, and do not restore over production as part of ordinary testing. Real recovery drill stays OPS-002/REL-001.

## 9. Version history

1.2 FINAL: functional acceptance, evidence distinctions and recovery exclusions; no runtime delta. 1.1 REBUILT: replacement implementation and candidate procedure, NEEDS_VERIFICATION at original delivery.
