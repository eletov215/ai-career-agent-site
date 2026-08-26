# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние - 2026-08-26

| Поле | Значение |
|---|---|
| Production schema | `20260819_0014` |
| Последний завершённый production-пакет | `SEARCH-005` |
| Текущий пакет | `AI-BENCH-001` - grounded-v2 hardening candidate; НУЖНА ПРОВЕРКА GITHUB ACTIONS + LIVE RUN #2 |
| Ordinary CI | после stability r4 подтверждён green на `main`: `Python tests` и `AI-BENCH-001 package gate` успешны |
| Live run #1 | GitHub Actions run artifact `32958938365`: 24/24 provider requests completed, 0 API errors; machine quality status `failed`, что является benchmark evidence, а не transport failure |
| Live run #1 leader | Alice AI LLM: 4/8 strict passes, quality `0.952178`, grounding `0.957259`; provider decision НЕ принят |
| Hardening | `evals 1.2.0`, grounded-v2 schemas/prompts/scoring, structured verification/caveats, exact evidence IDs, user-facing metadata ban, deterministic vacancy match score, scenario-number policy, live-run regressions |
| Следующий gate | green ordinary CI -> manual `run_ai_bench_live=true` -> live run #2 artifact -> human rubric -> provider decision |
| Следующий пакет | `AI-PROVIDER-001`, заблокирован до закрытия AI-BENCH-001 |
| Канонические документы | PLAN `v1.4.38`, PROJECT PASSPORT `v2.52`, SOURCE AUDIT `v1.4.38`, AI-BENCH verification `v1.6` |

Production Flask routes, dependencies, models, migrations, Render runtime and database schema are unchanged. The benchmark continues to use synthetic fixtures only and GitHub-secret-only credentials.
<!-- ACA-CANONICAL-STATUS:END -->

## 1. Назначение

AI Career Agent — Flask/Gunicorn web-service карьерного сопровождения:

```text
аккаунт -> резюме -> подтверждённый профиль -> AI-анализ
-> вакансии -> объяснимый match -> сопроводительное письмо -> tracker
```

Реальный production AI пока не подключён. Текущий `evals/` package предназначен для воспроизводимого выбора AI-моделей до интеграции в пользовательские routes.

## 2. Runtime

- WSGI entrypoint: `app:app`;
- production database: PostgreSQL через SQLAlchemy/Alembic;
- current production revision: `20260819_0014`;
- local/test fallback: SQLite;
- web, Trudvsem sync worker и privacy cleanup worker разделены на процессы;
- Render остаётся staging/резервным контуром до предрелизной VPS-миграции.

## 3. AI-BENCH-001 grounded-v2 benchmark

`evals 1.2.0` усиливает изолированный comparative benchmark после анализа первого live run:

- Alice AI LLM, Alice AI LLM Flash и YandexGPT Pro 5.1;
- Yandex OpenAI-compatible endpoint с `Api-Key` + `OpenAI-Project`;
- model URI строятся из GitHub-secret environment data и не коммитятся;
- grounded-v2 JSON Schema output: raw evidence IDs only, structured `facts_not_verified`/`caveats`, claim-level evidence and stricter hallucination controls;
- vacancy match is classified by requirement; numeric score is derived deterministically by benchmark logic rather than authored by the model;
- user-facing text cannot contain internal evidence labels/IDs; unsupported impact claims are hard failures;
- interview numbers are allowed only when supplied as source/scenario facts;
- live job встроен в существующий `.github/workflows/ci.yml`, поэтому не требует добавления отдельного workflow-файла;
- на push/pull request live job всегда пропускается;
- на ручном запуске он выполняется только при `run_ai_bench_live=true` и только после успешных jobs `tests` и `ai-bench-001`;
- sanitized artifact загружается через `actions/upload-artifact@v7`;
- runtime output создаётся в `/tmp/ai-bench-yandex-live`, вне repository checkout.

Перед загрузкой:

```bash
python scripts/check_ai_bench_package.py
python -m unittest discover -s tests -p 'test_ai_bench_*.py' -v
```

После green ordinary CI запустите:

```text
GitHub Actions -> CI -> Run workflow
run_ai_bench_live = true
```

Успешный transport run ещё не является provider decision: artifact нужно скачать и заполнить human writing-quality rubric.

## 4. Документация

- `docs/PLAN_CURRENT.md` — канонический порядок работ;
- `docs/PROJECT_PASSPORT.md` — архитектура и границы продукта;
- `docs/SOURCE_AUDIT.md` — аудит текущего hotfix;
- `docs/AI_BENCH_VERIFICATION_STATUS.md` — failure evidence, root cause и gates;
- `docs/evidence/ai-bench-001/` — deterministic validation/reference evidence.

## 5. Security and release hygiene

Repository/release ZIP не должен содержать `.env`, реальные credentials/tokens, databases, dumps, backups, virtualenv, caches, bytecode или runtime benchmark artifacts. API credentials задаются только через environment/secret storage.

## 6. Hosting roadmap

Render остаётся staging/резервной площадкой. Реальная аренда и полевой тест VPS выполняются в `INFRA-001` перед beta; далее следуют HOST-001, OPS-002, DOMAIN-001, MIG-001 и REL-001.
