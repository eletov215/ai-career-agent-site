# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние — 2026-08-25

| Поле | Значение |
|---|---|
| Production schema | `20260819_0014` |
| Последний завершённый пакет | `SEARCH-005` |
| Текущий пакет | `AI-BENCH-001` — stability hotfix r2; НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS |
| Исправлено | time-dependent SYNC-001 cache assertions; AI-BENCH gate no longer depends on dotfiles omitted by browser upload |
| Локально подтверждено | 298 passed, 14 environment-dependent skips, 8 subtests; deterministic AI-BENCH, SQLite migrations/Alembic, document and infra gates PASS |
| Следующий gate | green ordinary GitHub CI, then manual `AI-BENCH-001 Live Yandex` workflow and artifact/manual-rubric review |
| Следующий пакет | `AI-PROVIDER-001`, заблокирован до завершения AI-BENCH-001 |
| Канонические документы | PLAN `v1.4.35`, PROJECT PASSPORT `v2.49`, SOURCE AUDIT `v1.4.35`, AI-BENCH verification `v1.3` |

`evals 1.1.1` preserves the isolated Yandex live-evaluation workflow and hardens its repository contract for GitHub browser uploads. Credentials remain only in GitHub Actions Secrets; Flask routes, production dependencies, database schema and Render runtime are unchanged.
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

The earlier scorer hotfix remains confirmed. `evals 1.1.1` keeps the isolated live comparison stage and adds CI-stability fixes:

- manual-only `AI-BENCH-001 Live Yandex` workflow;
- Alice AI LLM, Alice AI LLM Flash and YandexGPT Pro 5.1;
- Yandex OpenAI-compatible endpoint with `Api-Key` + `OpenAI-Project`;
- model URI values constructed from GitHub-secret environment data, never committed;
- per-case JSON Schema structured output;
- latency/token/cost collection using a dated pricing snapshot;
- sanitized artifact upload and a separate transport-error gate;
- a visible `evals/artifacts/README.md` scaffold that survives browser upload; runtime outputs are generated outside the checkout and remain uncommitted;

Before upload:

```bash
python scripts/check_ai_bench_package.py
python -m unittest discover -s tests -p 'test_ai_bench_*.py' -v
```

After upload, confirm ordinary CI and manually run:

```text
GitHub Actions -> AI-BENCH-001 Live Yandex -> Run workflow
```

First obtain a green ordinary CI for this hotfix. Before the manual run, verify that the Yandex service account has `ai.languageModels.user`. Current Yandex documentation exposes two scope names: the AI Studio key-creation page lists `yc.ai.languageModels.execute` for Model Gallery text generation, while the Completions guides reference `yc.ai.foundationModels.execute`. Use the existing key for the first workflow preflight; if Yandex returns a permission error, recreate the key through AI Studio's **Create API key** flow, which assigns the current required scopes. GitHub Secrets do not expose key metadata. A successful live workflow is still not a provider decision: download the artifact and complete the human rubric first.

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
