# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние — 2026-08-25

| Поле | Значение |
|---|---|
| Production schema | `20260819_0014` |
| Последний завершённый пакет | `SEARCH-005` |
| Текущий пакет | `AI-BENCH-001` — live Yandex benchmark candidate; НУЖНА ПРОВЕРКА |
| Подтверждено | hotfix r1 GitHub Actions GREEN; manual Alice AI LLM Playground smoke PASS; benchmark secrets configured in GitHub Actions |
| Следующий gate | manual `AI-BENCH-001 Live Yandex` workflow, artifact review and human writing-quality rubric |
| Следующий пакет | `AI-PROVIDER-001`, заблокирован до завершения AI-BENCH-001 |
| Канонические документы | PLAN `v1.4.34`, PROJECT PASSPORT `v2.48`, SOURCE AUDIT `v1.4.34`, AI-BENCH verification `v1.2` |

`evals 1.1.0` adds a Yandex-only live evaluation transport for Alice AI LLM, Alice AI LLM Flash and YandexGPT Pro 5.1. Credentials remain outside Git in GitHub Actions Secrets; the workflow is manual-only and does not change Flask routes, production dependencies, database schema or Render runtime.
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

## 3. AI-BENCH-001 live Yandex candidate

Hotfix r1 already passed the external GitHub gate. `evals 1.1.0` now adds the isolated live comparison stage:

- manual-only `AI-BENCH-001 Live Yandex` workflow;
- Alice AI LLM, Alice AI LLM Flash and YandexGPT Pro 5.1;
- Yandex OpenAI-compatible endpoint with `Api-Key` + `OpenAI-Project`;
- model URI values constructed from GitHub-secret environment data, never committed;
- per-case JSON Schema structured output;
- latency/token/cost collection using a dated pricing snapshot;
- sanitized artifact upload and a separate transport-error gate;
- runtime `evals/artifacts/` ignored by Git.

Before upload:

```bash
python scripts/check_ai_bench_package.py
python -m unittest discover -s tests -p 'test_ai_bench_*.py' -v
```

After upload, confirm ordinary CI and manually run:

```text
GitHub Actions -> AI-BENCH-001 Live Yandex -> Run workflow
```

A successful workflow is still not a provider decision: download the artifact and complete the human rubric first.

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
