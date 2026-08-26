# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние - 2026-08-26

| Поле | Значение |
|---|---|
| Production schema | `20260819_0014` |
| Последний завершённый production-пакет | `SEARCH-005` |
| Текущий пакет | `AI-BENCH-001` - grounded-v2.1 hardening candidate; НУЖНА ПРОВЕРКА GITHUB ACTIONS + LIVE RUN #3 |
| Ordinary CI | grounded-v2 candidate v1.4.38 прошёл ordinary CI перед live run #2; текущий v2.1 candidate требует нового green CI |
| Live run #1 | artifact `32958938365`: 24/24 API calls, 0 errors; использован для grounded-v2 hardening |
| Live run #2 | artifact `32972783843`: Alice 5/8, Flash 4/8, YandexGPT Pro 3/8; один provider error у YandexGPT Pro; provider decision НЕ принят |
| Hardening | `evals 1.3.0`, benchmark `1.2`, dataset `1.2.0` / `grounded-v2.1`: Unicode-percent normalization, scenario provenance, RU/EN language gate, cover-letter motivation kind, safe provider diagnostics and one bounded retry |
| Следующий gate | green ordinary CI -> manual `run_ai_bench_live=true` -> live run #3 artifact -> named human writing rubric -> provider decision |
| Следующий пакет | `AI-PROVIDER-001`, заблокирован до закрытия AI-BENCH-001 |
| Канонические документы | PLAN `v1.4.39`, PROJECT PASSPORT `v2.53`, SOURCE AUDIT `v1.4.39`, AI-BENCH verification `v1.7` |

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

## 3. AI-BENCH-001 grounded-v2.1 benchmark

`evals 1.3.0` усиливает изолированный comparative benchmark после анализа второго live run:

- Alice AI LLM, Alice AI LLM Flash и YandexGPT Pro 5.1;
- Yandex OpenAI-compatible endpoint с `Api-Key` + `OpenAI-Project`;
- model URI строятся из GitHub-secret environment data и не коммитятся;
- grounded-v2.1 JSON Schema/scoring output: raw evidence IDs only, structured `facts_not_verified`/`caveats`, claim-level evidence, `motivation` paragraphs and stricter hallucination controls;
- vacancy match is classified by requirement; numeric score is derived deterministically by benchmark logic rather than authored by the model;
- user-facing text cannot contain internal evidence labels/IDs; unsupported impact claims are hard failures;
- interview numbers are allowed only when supplied as source/scenario facts; percent spacing is Unicode-normalized and scenario numbers require same-question scenario evidence;
- RU/EN user-facing language consistency is a hard gate;
- live provider diagnostics persist only safe envelope shape/status metadata; raw response bodies/refusal text are not stored;
- live providers may perform at most one configured bounded retry for transient 429/5xx/transport/malformed-envelope failures; retries are visible in evidence;
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
