# AI Career Agent — ROADMAP

<!-- ACA-CANONICAL-STATUS:START -->
## Актуальная точка дорожной карты — 2026-08-25

- `SEARCH-005` и все более ранние product packages — **ВЫПОЛНЕНО**; v1.4.34 не показал production regression, но повторный CI должен подтвердить их regression gates.
- `AI-BENCH-001 scorer hotfix r1` — **ПОДТВЕРЖДЁН** предыдущим green GitHub Actions.
- `AI-BENCH-001 live Yandex candidate v1.4.34` — CI выявил два stability defects вне production runtime.
- `AI-BENCH-001 stability hotfix r2 / evals 1.1.1` — **НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS**.
- Manual Alice AI LLM Playground smoke — **PASS**; GitHub Actions Secrets configured by user. Service-account role `ai.languageModels.user` is confirmed. The existing key uses `yc.ai.languageModels.execute`, matching the AI Studio key-creation page; Completions guides also mention `yc.ai.foundationModels.execute`, so the manual workflow preflight is the decisive authorization check.
- После green ordinary CI: manual live workflow -> sanitized artifact -> human rubric.
- `AI-PROVIDER-001` — **ЗАБЛОКИРОВАН ДО ЗАВЕРШЕНИЯ AI-BENCH-001**.
- Production schema remains `20260819_0014`; production routes and migrations are unchanged.
<!-- ACA-CANONICAL-STATUS:END -->

## Текущая очередь

```text
AI-BENCH-001 stability hotfix r2 -> green ordinary CI
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
| AI-BENCH-001 | НУЖНА ПРОВЕРКА | green ordinary CI -> live comparison artifact -> manual rubric |
| AI-PROVIDER-001 | ЗАБЛОКИРОВАНО | AI-BENCH-001 complete |
| LEGAL-001, AI-001..006 | ЗАПЛАНИРОВАНО | provider strategy and legal gate |
| JOB-001..004 | ЗАПЛАНИРОВАНО | AI core and account integration |
| INFRA-001 | ОТЛОЖЕНО | pre-release VPS field test |
| HOST/OPS-002/DOMAIN/MIG/REL | ЗАПЛАНИРОВАНО | pre-release infrastructure window |

## AI-BENCH-001 current boundary

Scorer hotfix r1 remains confirmed. Stability hotfix r2 must restore all ordinary CI gates before the isolated live Yandex workflow is launched. No provider is selected and no production AI route/schema is added.
