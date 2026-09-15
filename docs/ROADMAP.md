# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние / 2026-09-14

| Поле | Значение |
|---|---|
| Current package | AI-001 - НУЖНА ПРОВЕРКА; synthetic-only technical foundation |
| Source code | Owner-supplied `main (31).zip`; documented closure overlay and AI-001 changes; remote GitHub not queried |
| Canonical versions | PLAN 1.5.0; PASSPORT 2.67; SOURCE_AUDIT 1.5.0 |
| Completed AI foundation | AI-BENCH-001 and AI-PROVIDER-001 - ВЫПОЛНЕНО; accepted evidence remains unchanged |
| LEGAL-001 | ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА; operator, jurisdiction and launch countries not selected |
| Public AI / real data | Disabled in code; no generation POST route or real-data payload API |
| Technical candidate | Central policy, usage ledger, reservations, idempotency, Alice adapter, structured output, manual notice |
| Schema | Last verified staging: `20260819_0014`; candidate target: `20260914_0015` |
| Staging | Render web + clean Neon PostgreSQL; previous data not migrated |
| Verification | Local evidence only for AI-001; new ordinary GitHub CI, migration and staging smoke still required |
| Next action | Verify AI-001; then AI-002 technical development. LEGAL-001 must return before public AI/release |

Решение владельца: юридические вопросы отложены, но не отменены. Техническая разработка продолжается без передачи реальных резюме провайдеру.

<!-- ACA-CANONICAL-STATUS:END -->

## 1. Текущая очередь

```text
AI-BENCH-001 COMPLETE -> AI-PROVIDER-001 COMPLETE
-> AI-001 CANDIDATE -> AI-002..006 (technical development only)
-> JOB-001..004
```

| Package | Status | Acceptance boundary |
|---|---|---|
| FND/DATA/SEC/OPS/INFRA-PREP/SYNC/SEARCH/AUTH/PROF/PRIV | ВЫПОЛНЕНО | Historical accepted scope; regressions remain mandatory |
| AI-BENCH-001 / AI-PROVIDER-001 | ВЫПОЛНЕНО | Accepted synthetic benchmark and owner strategy/CI262 |
| LEGAL-001 | ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА | Return before public AI, paid subscriptions or release |
| AI-001 | НУЖНА ПРОВЕРКА | Exact candidate CI + staging0015 + manual-mode smoke |
| AI-002..006 | ЗАПЛАНИРОВАНО | Technical development does not authorize public AI |
| BILL-001 | ОТЛОЖЕНО | Free+Standard values based on actual usage; Max reserved |
| INFRA/HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | Pre-release deployment and recovery work |

## 2. Обязательный возврат к LEGAL-001

Operator country, legal form/requisites, legal contact, launch countries and final data-processing scheme remain open owner decisions. The package is deferred, not passed. No public AI/real-data entry points are added until those questions and actual consent are resolved. See `LEGAL001_DEFERRED_DECISION.md`.
