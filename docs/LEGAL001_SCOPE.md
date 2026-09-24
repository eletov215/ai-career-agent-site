# LEGAL-001 Scope

Status: **TECHNICAL_ACCEPTED / LEGAL_PENDING**.

LEGAL-001 provides the accepted technical foundation for versioned, owner-bound consent to cover-letter external-AI processing. It includes explicit acceptance/withdrawal, stale/replay/concurrency protection, Privacy Center UI, privacy export/delete integration and server-side `LegalLetterAdmission` rechecks.

Technical acceptance evidence: accepted main `309afe0089356e6fb0d1c205ce7ca2c7cb682ae2`, schema `20260922_0021`, main CI #324 SUCCESS, Package preflight #11 SUCCESS, dedicated PostgreSQL verification #5 SUCCESS, production QA on runtime-equivalent `28db01b719003149a0d616934e469b1b83c0237f`, paid provider calls 0.

This package still does **not** supply or invent operator/legal entity, jurisdiction, launch countries, audience/age, storage regions, processors/subprocessors, cross-border route, final retention or final Terms/Privacy/AI-consent wording. The current production policy remains code-defined as `DRAFT / PLACEHOLDER REQUIRED`; `domain/ai.py::REAL_DATA_SUPPORTED` remains `False`.

User consent and production legal activation are independent gates. A technically valid accepted consent record does not authorize provider dispatch while policy is DRAFT. Withdrawal continues to block future admission; reacceptance creates a new cycle. Account deletion cascades consent rows; privacy export includes owner history.

Recorded evidence limits remain: natural 24h cleanup cycle NOT_RUN, historical pre-migration production backup not evidenced, and old baseline consent record ID not captured.

Historical predecessor `LEGAL001_DEFERRED_DECISION.md` remains preserved. LEGAL-001 is not COMPLETE until the owner/legal decisions and final policy activation are separately resolved.
