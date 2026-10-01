# JOB-002 implementation

JOB-002 adds an owner-scoped application tracker to saved vacancies. An absent tracker is virtual `saved`; the first explicit state change creates the current row and one immutable event in one transaction. Later accepted changes update the independent tracker revision and append one event atomically. Same-state submissions are no-ops, while stale revisions fail closed.

The UI calls every external-looking status user-reported and not employer-verified. This package performs no employer submission and imports no provider client. `REAL_DATA_SUPPORTED=False` and the legal policy remain unchanged.

Migration `20261001_0022` is additive, has no backfill, and cascades the tracker subtree through composite owner/saved-vacancy keys. Each event stores the resulting tracker revision, unique per owner and saved vacancy; history and privacy export use that revision rather than timestamps or UUIDs for deterministic ordering. Account-deletion audit counts include both tracker tables before the same cascade removes them.

The JOB-002 evidence boundary chains every changed existing runtime file and every new runtime file from accepted commit `a11ac07b09addd32f3a3e26cec4e4296dbe85ab6` / tree `52eb37b839d42df8b5c9e8192c5716c1dbf523af`. Historical evidence is unchanged; predecessor guards recognize this exact-hash successor explicitly.
