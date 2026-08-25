# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальная точка дорожной карты — 2026-08-25

- `SEARCH-005` — **ВЫПОЛНЕНО**.
- `AI-BENCH-001 hotfix r1 / evals 1.0.1` — **ПОДТВЕРЖДЁН GITHUB ACTIONS**.
- Manual Alice AI LLM Playground smoke — **PASS**.
- GitHub Actions Secrets `AI_BENCH_YANDEX_API_KEY` и `AI_BENCH_YANDEX_FOLDER_ID` — **НАСТРОЕНЫ ПОЛЬЗОВАТЕЛЕМ**; значения не входят в репозиторий.
- `AI-BENCH-001 live Yandex candidate / evals 1.1.0` — **НУЖНА ПРОВЕРКА**: запустить manual workflow, скачать sanitized artifact, выполнить human rubric.
- `AI-PROVIDER-001` — **ЗАБЛОКИРОВАН ДО ЗАВЕРШЕНИЯ AI-BENCH-001**.
- Production schema remains `20260819_0014`; production routes and migrations are unchanged.
<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-BENCH-001 live Yandex candidate
-> manual GitHub workflow with Alice AI LLM / Flash / YandexGPT Pro 5.1
-> comparative run on one dataset fingerprint
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
| AI-BENCH-001 | НУЖНА ПРОВЕРКА | live comparison artifact + manual rubric |
| AI-PROVIDER-001 | ЗАБЛОКИРОВАНО | AI-BENCH-001 complete |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 current boundary

Hotfix r1 is confirmed green. The live Yandex workflow remains isolated from production and compares approved models without selecting a provider, connecting production AI, changing the database or exposing new user routes.
