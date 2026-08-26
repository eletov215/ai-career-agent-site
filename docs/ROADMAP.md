# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальная точка дорожной карты - 2026-08-26

- `SEARCH-005` и все более ранние product packages - **ВЫПОЛНЕНО**.
- grounded-v2 ordinary CI on `main` - **GREEN** before live run #2.
- Yandex live run #2 - **TRANSPORT PARTIAL / QUALITY REVIEWED**: Alice 5/8, Flash 4/8, YandexGPT Pro 3/8 with one provider-envelope error; no provider decision.
- `AI-BENCH-001 grounded-v2.1 / evals 1.3.0` - **НУЖНА ПРОВЕРКА**.
- Next: green ordinary CI -> manual live run #3 -> artifact review -> named human rubric.
- `AI-PROVIDER-001` - **ЗАБЛОКИРОВАН ДО ЗАВЕРШЕНИЯ AI-BENCH-001**.
- Production schema remains `20260819_0014`; production routes and migrations are unchanged.
<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-BENCH-001 grounded-v2.1 -> green ordinary CI
-> CI workflow_dispatch(run_ai_bench_live=true)
-> live run #3: Alice AI LLM / Flash / YandexGPT Pro 5.1
-> sanitized artifact review
-> named manual writing-quality rubric
-> AI-PROVIDER-001
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
| AI-BENCH-001 | НУЖНА ПРОВЕРКА | grounded-v2.1 CI -> live run #3 -> artifact review -> manual rubric |
| AI-PROVIDER-001 | ЗАБЛОКИРОВАНО | AI-BENCH-001 complete |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 current boundary

No provider is selected and no production AI route/schema is added. The integrated manual job is an evaluation-only transport and cannot run until the complete ordinary CI matrix succeeds.
