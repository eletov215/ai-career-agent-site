# LEGAL-001 Scope

Status: IMPLEMENTED / NEEDS_VERIFICATION.

LEGAL-001 adds a versioned, owner-bound technical consent record for cover-letter external-AI processing. It does not supply missing operator/jurisdiction/legal-entity facts and does not activate real-data Alice.

The current policy is code-defined as `DRAFT / PLACEHOLDER REQUIRED`. User acceptance and production legal activation are separate gates. `domain/ai.py::REAL_DATA_SUPPORTED` remains `False`.

Persistence records policy version/hash, provider, purpose, acceptance, withdrawal, cycle and optimistic revision. Withdrawal blocks future admission checks; reacceptance creates a new cycle. Account deletion cascades records. Privacy export includes the owner history.

Historical predecessor: `docs/LEGAL001_DEFERRED_DECISION.md` remains preserved. This package implements the technical foundation while the owner/legal decisions listed there remain unresolved.

Baseline: `f5ce1f42836e3872854332324f2ebdd9c8934b36`, tree `350ddf3f136a490b6504fc962f64822ba1985a86`.
Schema candidate: `20260922_0021`.
Paid provider calls: 0.
