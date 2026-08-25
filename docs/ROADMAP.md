# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальная точка дорожной карты — 2026-08-25

- `SEARCH-005` и все более ранние product packages — **ВЫПОЛНЕНО**.
- `AI-BENCH-001 scorer hotfix r1` — **ПОДТВЕРЖДЁН** предыдущим green GitHub Actions.
- `AI-BENCH-001 stability hotfix r2` исправил SYNC/date и dotfile contract, но run `#196` выявил новый upload-layout defect: live workflow потерял `.yml` suffix.
- `AI-BENCH-001 stability hotfix r3 / evals 1.1.2` — **НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS**.
- Live Yandex job теперь находится в existing `CI` workflow, default-off и зависит от всех ordinary gates.
- Manual Alice AI LLM Playground smoke — **PASS**; GitHub Actions Secrets и role `ai.languageModels.user` настроены.
- После green ordinary CI: `Actions -> CI -> Run workflow -> run_ai_bench_live=true` -> sanitized artifact -> human rubric.
- `AI-PROVIDER-001` — **ЗАБЛОКИРОВАН ДО ЗАВЕРШЕНИЯ AI-BENCH-001**.
- Production schema remains `20260819_0014`; production routes and migrations are unchanged.
<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-BENCH-001 stability hotfix r3 -> green ordinary CI
-> CI workflow_dispatch(run_ai_bench_live=true)
-> comparative run: Alice AI LLM / Flash / YandexGPT Pro 5.1
-> download sanitized run.json/report/responses artifact
-> manual quality rubric
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
| AI-BENCH-001 | НУЖНА ПРОВЕРКА | green ordinary CI -> integrated live job -> artifact -> manual rubric |
| AI-PROVIDER-001 | ЗАБЛОКИРОВАНО | AI-BENCH-001 complete |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 current boundary

No provider is selected and no production AI route/schema is added. The integrated manual job is an evaluation-only transport and cannot run until the complete ordinary CI matrix succeeds.
