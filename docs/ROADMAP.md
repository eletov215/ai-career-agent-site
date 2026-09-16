# AI Career Agent - ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние / 2026-09-16

| Поле | Значение |
|---|---|
| Current package | AI-003 - НУЖНА ПРОВЕРКА; synthetic/reference-only adaptive interview candidate r1 |
| Source code | Owner main (33).zip; archive comment 20947f2e015097010cbe33772f7662bef4503f37; SHA-256 3f46536638fb541310c15a5520dc5a445d4916d8af90baf14292c99866971533 |
| Canonical versions | PLAN 1.5.4; PASSPORT 2.71; SOURCE_AUDIT 1.5.4 |
| Completed AI foundation | AI-BENCH-001 / AI-PROVIDER-001 / AI-001 / AI-002 - ВЫПОЛНЕНО in accepted boundaries |
| LEGAL-001 | ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА; public real-data AI and paid launch remain blocked |
| Schema | Last accepted staging 20260915_0016; AI-003 target 20260916_0017, two additive tables; NOT YET verified on staging |
| Candidate boundary | Private RU/EN reference interviews; pinned choice IDs; persisted history; explicit confirmation into isolated synthetic draft; no provider call |
| Verification | Local evidence in AI003_VERIFICATION_STATUS; GitHub CI, PostgreSQL 17, Render and owner browser acceptance PENDING |
| Next action | Ordinary CI, backup, staging migration and private AI-003 review; then disable review flag; no AI-004 start before acceptance |
<!-- ACA-CANONICAL-STATUS:END -->

## 1. Current sequence

FND/DATA/SEC/OPS/INFRA-PREP/SYNC/SEARCH/AUTH/PROF/PRIV: ВЫПОЛНЕНО in historical accepted scope. Regressions remain mandatory.

```text
AI-BENCH-001 COMPLETE -> AI-PROVIDER-001 COMPLETE
-> AI-001 COMPLETE -> AI-002 COMPLETE
-> AI-003 NEEDS_VERIFICATION (synthetic/reference-only r1)
-> AI-004..006 (technical development only)
-> JOB-001..004
```

AI-003: bounded reference interview/history/explicit confirmation, not arbitrary live Alice. Latest accepted staging is 0016; candidate 0017 must pass ordinary CI and owner staging review.

## 2. Deferred gates

LEGAL-001: ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА. It is not passed or removed. No public real-data AI, paid subscriptions or commercial release before the actual operator/data/consent decision. No boolean switch substitutes legal review. Email verification delivery is still unresolved.

INFRA-001 -> REED-COMPAT-001 -> HOST-001 -> OPS-002 restore drill -> DOMAIN-001 -> MIG-001 -> REL-001 remain pre-release tasks. BILL-001 is deferred; exact Free/Standard quotas remain unset, Max reserved.

## 3. Next action

Follow AI003_RUNBOOK. Confirm GitHub CI, staging current/expected 20260916_0017, manual AI status, private branching/history/confirmation/owner/stale/mobile tests and core regressions. Turn review off. Only then decide AI-003 closure and AI-004 start. No remote checks are claimed by this release.
