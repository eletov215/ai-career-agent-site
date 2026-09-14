# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние / 2026-09-14

| Поле | Значение |
|---|---|
| Current package | AI-PROVIDER-001 - НУЖНА ПРОВЕРКА |
| Source code | Latest uploaded GitHub snapshot `ai-career-agent-site-main (30).zip`; 407 files |
| Canonical versions | PLAN 1.4.49; PASSPORT 2.63; SOURCE_AUDIT 1.4.49; AI-BENCH verification 1.16; provider ADR 1.0 |
| AI-BENCH-001 | ВЫПОЛНЕНО; accepted artifact `34830877796`, eight cases PASS and named human acceptance |
| Provider decision | Alice primary; manual reserve without generation; proposed limits/data policy; owner approval pending |
| Production AI | Not implemented or activated; policy JSON is an offline specification |
| Staging | Render web + clean Neon PostgreSQL (Oregon); previous readiness/site/search smoke confirmed |
| Database schema | `20260819_0014`; unchanged |
| Current verification | Local results in AI_PROVIDER001_VERIFICATION_STATUS; new external CI not yet run |
| Next package | LEGAL-001 after owner strategy approval and ordinary CI; AI-001 remains later |

The supplied canonical 1.4.48/2.62/1.16 files are authentic current inputs, but repository docs still contained the pre-closure status. This release reconciles them explicitly. Older dated evidence below remains historical and is not today's gate. No benchmark rerun or Render secret change is required for this architecture-only package.

<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-PROVIDER-001
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
| AI-PROVIDER-001 | НУЖНА ПРОВЕРКА | candidate ADR; ordinary CI + owner approval |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 closure boundary

AI-BENCH-001 is complete on the synthetic grounded-v2.6.1 contract. This does not enable production AI calls. AI-PROVIDER-001 must now define provider routing, fallback, privacy/retention, cost/quotas, geography, failure policy and kill switch before AI-001 production integration.

## AI-PROVIDER-001 boundary

The strategy package is prepared but not yet approved. It does not activate AI or authorize spending. After ordinary CI and owner approval, continue to LEGAL-001; production implementation belongs to AI-001.
