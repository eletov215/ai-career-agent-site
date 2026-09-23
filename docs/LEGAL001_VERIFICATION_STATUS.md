# LEGAL-001 Verification Status

## LEGAL-OPS-01 follow-up / 2026-09-23

The consolidated owner-supplied QA report now records a repeated privacy-worker
heartbeat failure on deployed `97944ef2efb4d81f9e416868aabff234fdc7dc70`.
The targeted worker correction is **IMPLEMENTED / LOCAL_ISOLATED_CHECKS_PASS**;
new GitHub CI and production verification are separate gates, not inferred from
CI314 or the earlier layout retest. See `LEGAL001_OPS_HEARTBEAT_FIX.md` for the
exact source, reproduction, changes, test limits and rollout checklist.
No new migration, consent mutation, policy activation or paid AI call is involved.
Full technical QA remains incomplete; final legal decisions remain outstanding.


The table below preserves historical CI304 evidence for its exact SHA. The
2026-09-23 layout defect, correction and partial owner-provided QA follow-up
are tracked in `LEGAL001_LAYOUT_QA.md`; no final production acceptance is claimed.

| Field | Status |
| --- | --- |
| Package | LEGAL-001 |
| Implementation | IMPLEMENTED |
| Verification | CI_PASS |
| Candidate branch | legal001-consent-foundation |
| Candidate commit | fe3a7e1b553ccc9ebb5b956efce3779287291c04 |
| Candidate tree | 55f03c287a3132aa9a2a55b7429c24d35e2a1957 |
| Baseline commit | f5ce1f42836e3872854332324f2ebdd9c8934b36 |
| Schema candidate | 20260922_0021 |
| GitHub CI | #304 SUCCESS |
| Dedicated LEGAL-001 gate | SUCCESS |
| PostgreSQL/migrations | SUCCESS |
| Full Run tests | SUCCESS |
| Production legal state | DRAFT / NOT_ACTIVE |
| Real-data Alice | CLOSED |
| Paid provider calls | 0 |
| Paid Yandex/Alice CI jobs | SKIPPED as intended |
| Render deploy | NOT RUN |
| Production /health/ready 0021 | NOT RUN |
| Production QA | NOT RUN |
| Legal-owner decisions | PENDING |
| Acceptance | NOT YET |
| Complete | NO |

CI #304 establishes only `CI_PASS`. It does not activate the legal policy, does not authorize real-data processing, and does not prove production deployment.

The preceding #303 code-equivalent run completed the full pytest collection with `1103 passed` before GitHub canceled the job at the old 25-minute timeout. The CI timeout was raised to 40 minutes; #304 then completed successfully, including the final Run tests step.

Known legal placeholders remain unresolved: operator/legal entity, jurisdiction, launch countries, age/audience, storage regions, processor/subprocessor and cross-border scheme, final retention, Terms, Privacy Policy and final AI consent wording.
