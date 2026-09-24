# LEGAL-001 Runbook

## Current status / 24 September 2026

Status: **TECHNICAL_ACCEPTED / LEGAL_PENDING**.

Accepted technical main: `309afe0089356e6fb0d1c205ce7ca2c7cb682ae2`. Post-merge main CI #324, Package preflight #11 and dedicated PostgreSQL verification #5 are SUCCESS. Production runtime QA was completed on `28db01b719003149a0d616934e469b1b83c0237f`; compare to accepted main changes only verification workflow/guard/tests, not application runtime.

No further consent mutation is required for acceptance. Keep the QA account's withdrawn/cycle-4/revision-2 history unchanged unless a future product test explicitly requires a new cycle.

Before any real-data provider test:

1. Record operator/legal entity, jurisdiction, launch countries, audience/age and user contact channel.
2. Record application/database/backup regions, processors/subprocessors, cross-border route and final retention.
3. Produce reviewed final Terms, Privacy Policy and AI-consent wording/version/hash.
4. Implement a separate reviewed code change that makes production legal policy ACTIVE; do not use an environment-variable bypass.
5. Re-run CI, PostgreSQL verification, production readiness and consent UI smoke.
6. Only then run a controlled real-data AI-005 test, followed by human quality acceptance. Do not start AI-006 first.

Operational limits remain explicit: natural 24h privacy-cleanup cycle is not yet observed; historical pre-migration production backup evidence is unavailable; baseline consent ID was not captured.

## Historical follow-up references

See `LEGAL001_LAYOUT_QA.md` and `LEGAL001_OPS_HEARTBEAT_FIX.md` for the dated defect/fix evidence. CI #304 remains historical candidate evidence only.
