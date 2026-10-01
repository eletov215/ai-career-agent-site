# JOB-002 implementation

JOB-002 adds an owner-scoped application tracker to saved vacancies. An absent tracker is virtual `saved`; the first explicit state change creates the current row and one immutable event in one transaction. Later accepted changes update the independent tracker revision and append one event atomically. Same-state submissions are no-ops, while stale revisions fail closed.

The UI calls every external-looking status user-reported and not employer-verified. This package performs no employer submission and imports no provider client. `REAL_DATA_SUPPORTED=False` and the legal policy remain unchanged.

Migration `20261001_0022` is additive, has no backfill, and cascades the tracker subtree through composite owner/saved-vacancy keys.
