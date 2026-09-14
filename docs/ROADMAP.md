# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние / 2026-09-14

| Поле | Значение |
|---|---|
| Current package | AI-PROVIDER-001 - НУЖНА ПРОВЕРКА |
| Source code | GitHub `main` after AI-PROVIDER-001 candidate r1; ordinary CI #261 green; this r2 records owner-approved strategy and awaits final CI |
| Canonical versions | PLAN 1.4.50; PASSPORT 2.64; SOURCE_AUDIT 1.4.50; AI-BENCH verification 1.16; provider ADR 1.1 |
| AI-BENCH-001 | ВЫПОЛНЕНО; accepted artifact `34830877796`, 8/8 machine PASS and named human acceptance |
| Provider decision | APPROVED by Шекунов Д.С.: Alice primary; manual mode with explicit warning; internal technical guards only; Free + Standard launch intent; Max architecture reserved |
| Commercial quotas | Exact Free/Standard action quotas intentionally unset until usage evidence and BILL-001; users see feature actions, not tokens |
| Production AI | Not implemented or activated; policy JSON remains an offline architecture specification |
| Staging | Render web + clean Neon PostgreSQL (Oregon); schema `20260819_0014` |
| Current verification | Previous r1 ordinary CI green; r2 local checks recorded in AI_PROVIDER001_VERIFICATION_STATUS; final ordinary CI pending |
| Next package | LEGAL-001 after final ordinary CI; AI-001 remains the later runtime integration package |

This revision separates technical cost guards from commercial entitlements. Internal caps protect the service during development/beta; tariff quotas belong to BILL-001 and must not be hard-coded in the provider adapter.

<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-PROVIDER-001 (owner approved; final CI)
-> LEGAL-001
-> AI-001..006
-> JOB-001..004
```

## Статусы

| Пакет | Статус | Следующий gate |
|---|---|---|
| FND/DATA/SEC/OPS/INFRA-PREP | ВЫПОЛНЕНО | regression only |
| SYNC-001/002, SEARCH-001..005 | ВЫПОЛНЕНО | regression only |
| AUTH-001/002 | ВЫПОЛНЕНО | regression only |
| PROF-001/002/003, PRIV-001 | ВЫПОЛНЕНО | regression only |
| AI-BENCH-001 | ВЫПОЛНЕНО | final Alice 8/8 + named human PASS |
| AI-PROVIDER-001 | НУЖНА ПРОВЕРКА | owner-approved ADR; r1 CI green; final r2 ordinary CI |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 closure boundary

AI-BENCH-001 is complete on the synthetic grounded-v2.6.1 contract. This does not enable production AI calls. AI-PROVIDER-001 must now define provider routing, fallback, privacy/retention, cost/quotas, geography, failure policy and kill switch before AI-001 production integration.

## AI-PROVIDER-001 boundary

The strategy is approved by the owner but does not activate AI or authorize spending. Technical cost guards are separate from commercial Free/Standard entitlements; Max is reserved. After final r2 ordinary CI, continue to LEGAL-001; production implementation belongs to AI-001.
