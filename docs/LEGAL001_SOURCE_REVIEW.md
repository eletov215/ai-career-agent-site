# LEGAL-001 source review - 2026-09-22

## Additional pre-merge hardening

The complete source diff review found two gaps not exercised by the original CI304 tests. A previously rendered empty consent form could accept a newly deployed policy because it submitted only an empty record identifier and revision zero. Also, withdrawal followed by a new acceptance during generation could pass a current-status-only admission recheck.

Consent forms now carry a bounded HMAC token over the server-rendered policy descriptor, owner, permitted action, record identifier, revision and issue time. A policy version/hash/provider/purpose/scope/status/disclosure change invalidates even an empty old form. This is separate from CSRF; both checks are required. Tokens contain no plaintext owner data and are not stored, exported or logged. Existing concurrent accept/withdraw revision checks remain authoritative.

The signed AI preview now binds the exact admission scope. It is checked before dispatch and in the result transaction. A withdrawn and reaccepted consent has a different identifier, so an earlier result is not delivered as a normal proposal. The shared ledger still conservatively accounts for a completed simulated operation. Production legal policy stays DRAFT, and REAL_DATA_SUPPORTED stays False.

Tests use isolated synthetic data and fake transport only. No environment variable is added as an activation path. Historical benchmark contracts and migration 0021 are unchanged.

## Evidence boundaries

CI304 remains recorded evidence for its exact historical code commit, not evidence for these additional changes. Every subsequent branch and PR SHA must pass its own GitHub CI before merge. Source-review tests include old empty forms after policy changes, owner/action/state tampering, expiry, independent legal gates, and withdrawal/reacceptance before dispatch and during result delivery.

The source review does not declare deployment, website QA, operator/legal approval or real-data Alice acceptance. These remain separate gates. Final checked commit/tree and CI runs are recorded in the PR and distribution manifest, without rewriting historical CI304 evidence.
