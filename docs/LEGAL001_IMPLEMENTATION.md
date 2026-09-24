# LEGAL-001 Implementation

Status: IMPLEMENTED / TECHNICAL_ACCEPTED; LEGAL_PENDING.

Implemented layers:

- `AIConsent` table/model with user FK `ON DELETE CASCADE`, version/hash/provider/purpose/status/cycle/revision timestamps and one-active-policy partial uniqueness.
- `ConsentRepository` provides owner-scoped history, active lookup, explicit accept/withdraw and stale-state/concurrency checks.
- `ConsentService` fixes policy server-side; forms cannot choose provider, purpose or policy version.
- `/privacy-center/ai-consent` exposes the DRAFT technical disclosure, current status, history, accept and withdraw controls.
- `LegalLetterAdmission` requires current acceptance, then separately requires reviewed-code production policy activation and `REAL_DATA_SUPPORTED`.
- Existing `LetterRuntime` preflight checks admission before dispatch; result settlement rechecks admission in the transaction before proposal insertion.
- PRIV-001 export/count/delete paths include consent history; provider raw response and credentials are not added.
- Existing AI-005 predecessor guards are preserved through explicit successor evidence rather than bypasses.

## Final technical acceptance / 24 September 2026

Accepted technical main: `309afe0089356e6fb0d1c205ce7ca2c7cb682ae2`, tree `2616a3b15df09f85bf7ae261e605356fb9f52f9d`. Main CI #324, Package preflight #11 and dedicated PostgreSQL verification #5 are SUCCESS. T-05/T-06 close the previously blocked PostgreSQL migration/history/concurrency/CASCADE/backup/restore/downgrade/regression scenarios.

Production QA ran on `28db01b719003149a0d616934e469b1b83c0237f`. The only paths changed between that production runtime and accepted main are the LEGAL-001 PostgreSQL workflow, package guard and test file; application runtime is unchanged across that delta. Health/readiness, privacy/anonymous behavior, consent conflicts, responsive layouts, ZIP export and TXT export passed. The heartbeat startup/resume failure did not recur in two observed starts.

Natural 24h cleanup cycle, historical pre-migration production backup evidence and the old baseline consent record ID remain recorded limits. Policy is still DRAFT/NOT_ACTIVE, `REAL_DATA_SUPPORTED=False`, real-data Alice CLOSED and paid provider calls 0.

Signed consent forms bind the displayed policy, owner, action, optimistic state and expiry; signed AI previews pin the exact admission scope across dispatch and result commit. See `LEGAL001_SOURCE_REVIEW.md`. CI304 remains historical evidence for its exact SHA.
