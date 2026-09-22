# LEGAL-001 Implementation

Status: IMPLEMENTED / CI_PASS.

Implemented layers:

- `AIConsent` table/model with user FK `ON DELETE CASCADE`, version/hash/provider/purpose/status/cycle/revision timestamps and one-active-policy partial uniqueness.
- `ConsentRepository` provides owner-scoped history, active lookup, explicit accept/withdraw and stale-state/concurrency checks.
- `ConsentService` fixes policy server-side; forms cannot choose provider, purpose or policy version.
- `/privacy-center/ai-consent` exposes the DRAFT technical disclosure, current status, history, accept and withdraw controls.
- `LegalLetterAdmission` requires current acceptance, then separately requires reviewed-code production policy activation and `REAL_DATA_SUPPORTED`.
- Existing `LetterRuntime` preflight checks admission before dispatch; result settlement rechecks admission in the transaction before proposal insertion.
- PRIV-001 export/count/delete paths include consent history; provider raw response and credentials are not added.
- Existing AI-005 predecessor guards are preserved through an explicit LEGAL-001 successor hash map.

No paid/external provider call is added by this package. Production policy remains DRAFT. GitHub CI #304 passed on candidate `fe3a7e1b553ccc9ebb5b956efce3779287291c04`; this is not deployment or legal acceptance.


## Pre-merge source review

Signed consent forms bind the displayed policy, owner, action, optimistic state and expiry; signed AI previews pin the exact admission scope across dispatch and result commit. See `LEGAL001_SOURCE_REVIEW.md`. The recorded CI304 above is historical evidence for its exact SHA; subsequent hardening requires its own green branch/PR CI. Production remains closed.
