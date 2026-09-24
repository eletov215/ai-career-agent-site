# LEGAL-001 Verification Status

## Final technical acceptance / 24 September 2026

| Field | Status |
| --- | --- |
| Package | LEGAL-001 |
| Implementation | IMPLEMENTED |
| Verification | TECHNICAL_ACCEPTED |
| Accepted technical main | 309afe0089356e6fb0d1c205ce7ca2c7cb682ae2 |
| Accepted technical tree | 2616a3b15df09f85bf7ae261e605356fb9f52f9d |
| Production runtime commit | 28db01b719003149a0d616934e469b1b83c0237f |
| Schema | 20260922_0021 |
| Main GitHub CI | #324 SUCCESS |
| Package preflight | #11 SUCCESS |
| Dedicated PostgreSQL verification | #5 SUCCESS |
| T-05 | PASS |
| T-06 | PASS |
| Production /health/ready 0021 | PASS |
| Production QA | PASS_WITH_RECORDED_LIMITS |
| Production legal state | DRAFT / NOT_ACTIVE |
| Real-data Alice | CLOSED |
| Paid provider calls | 0 |
| Legal-owner decisions | PENDING |
| Technical acceptance | ACCEPTED |
| Complete | NO |

Technical acceptance is based on combined evidence. Production QA ran on `28db01b719003149a0d616934e469b1b83c0237f`. GitHub compare to accepted main `309afe0089356e6fb0d1c205ce7ca2c7cb682ae2` changes only the LEGAL-001 verification workflow, package guard and PostgreSQL tests; no application runtime path changed. Post-merge CI #324, Package preflight #11 and disposable PostgreSQL verification #5 all succeeded.

T-05 covers migration `20260917_0020 -> 20260922_0021`, no implicit consent creation, non-empty consent cycles/revisions, concurrent stale protection, owner CASCADE, encrypted backup/restore with exact consent-row equality, destructive downgrade and re-upgrade. T-06 covers the eight requested PostgreSQL regression files without treating SKIPPED as PASS.

Production QA records health/live/status, no-store privacy headers, unauthenticated isolation, stale/conflict behavior, responsive 1280/768/390/360 layouts, privacy ZIP and TXT export. The heartbeat fix was observed across two worker starts without the former FileNotFoundError/exit-code-1 pattern.

Recorded limits remain: the natural 86400-second periodic cleanup cycle was not observed; a historical production backup before the original migration is not evidenced; the old baseline consent record ID was never captured. These are not retroactively converted to PASS.

The legal boundary is unchanged. Policy remains `DRAFT / NOT_ACTIVE`; `REAL_DATA_SUPPORTED=False`; real-data Alice is CLOSED. Operator/legal entity, jurisdiction, launch countries, audience/age, storage/processors/cross-border/final retention and final Terms/Privacy/AI-consent are still pending. Therefore LEGAL-001 is technically accepted but not legally complete or production-AI activated.

## Historical evidence retained

- CI #304 on `fe3a7e1b553ccc9ebb5b956efce3779287291c04` remains the original technical candidate CI evidence.
- `LEGAL001_LAYOUT_QA.md` records the layout defect/fix/retest boundary.
- `LEGAL001_OPS_HEARTBEAT_FIX.md` records LEGAL-OPS-01 root cause and narrow correction.
- `docs/evidence/legal-001/ci304_verified_summary.json` is historical and is not rewritten.
