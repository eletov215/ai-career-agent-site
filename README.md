# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние — 2026-08-25

| Поле | Значение |
|---|---|
| Production schema | `20260819_0014` |
| Последний завершённый пакет | `SEARCH-005` |
| Текущий пакет | `AI-BENCH-001` — stability hotfix r3; НУЖНА ПОВТОРНАЯ ПРОВЕРКА GITHUB ACTIONS |
| Причина run #196 | GitHub upload сохранил live workflow как extensionless `.github/workflows/ai-bench-live`, поэтому executable `.yml` отсутствовал |
| Исправлено | billable live job перенесён в существующий `.github/workflows/ci.yml`; отдельный workflow-файл больше не является зависимостью |
| Локально подтверждено | 298 passed, 14 environment-dependent skips; deterministic AI-BENCH, YAML structure, repository/document/infra gates PASS |
| Следующий gate | green ordinary CI; затем manual `CI` workflow с `run_ai_bench_live=true` и review artifact/manual rubric |
| Следующий пакет | `AI-PROVIDER-001`, заблокирован до завершения AI-BENCH-001 |
| Канонические документы | PLAN `v1.4.36`, PROJECT PASSPORT `v2.50`, SOURCE AUDIT `v1.4.36`, AI-BENCH verification `v1.4` |

`evals 1.1.2` устраняет зависимость от нового workflow filename. Обычные push/PR запускают прежние package gates; live Yandex job доступен только через `workflow_dispatch`, имеет boolean-confirmation и зависит от успешных `Python tests` и `AI-BENCH-001 package gate`. Credentials остаются только в GitHub Actions Secrets; Flask routes, production dependencies, database schema и Render runtime не изменялись.
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

`evals 1.1.2` сохраняет изолированный comparative benchmark и делает запуск устойчивым к browser upload:

- Alice AI LLM, Alice AI LLM Flash и YandexGPT Pro 5.1;
- Yandex OpenAI-compatible endpoint с `Api-Key` + `OpenAI-Project`;
- model URI строятся из GitHub-secret environment data и не коммитятся;
- per-case JSON Schema output, grounding/hallucination checks, latency/token/cost evidence;
- live job встроен в существующий `.github/workflows/ci.yml`, поэтому не требует добавления отдельного workflow-файла;
- на push/pull request live job всегда пропускается;
- на ручном запуске он выполняется только при `run_ai_bench_live=true` и только после успешных jobs `tests` и `ai-bench-001`;
- sanitized artifact загружается через `actions/upload-artifact@v7`;
- runtime output создаётся в `${{ runner.temp }}`, а не в repository checkout.

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
