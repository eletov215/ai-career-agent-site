# AI Career Agent

<!-- ACA-CANONICAL-STATUS:START -->
## Каноническое состояние — 2026-08-24

| Поле | Значение |
|---|---|
| Production schema | `20260819_0014` |
| Последний завершённый пакет | `SEARCH-005` |
| Текущий пакет | `AI-BENCH-001 hotfix r1` — исправление готово, требуется повторный GitHub Actions |
| Следующий функциональный gate | live comparative benchmark + manual rubric |
| Следующий пакет | `AI-PROVIDER-001`, заблокирован до завершения AI-BENCH-001 |
| Канонические документы | PLAN `v1.4.33`, PROJECT PASSPORT `v2.47`, SOURCE AUDIT `v1.4.33`, AI-BENCH verification `v1.1` |

Первый AI-BENCH-001 candidate был отклонён GitHub CI: unsupported-number gate повторно сканировал весь корневой JSON-контейнер и ошибочно считал разрешённые `match_score` 78/72 неподтверждёнными числами. Hotfix `evals 1.0.1` проверяет только scalar leaves, сохраняет запрет на действительно выдуманные числа и добавляет регрессионные тесты. Production routes, migrations и Flask runtime не изменялись.
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

## 3. AI-BENCH-001 hotfix r1

Root cause первого CI failure находился в `evals/ai_bench/scoring.py`: `iter_paths()` выдавал root/container nodes, а numeric scorer строкифицировал их и повторно видел вложенный `match_score` по пути `$`. Hotfix:

- игнорирует `dict/list/tuple/set` в unsupported-number scan;
- проверяет scalar leaves;
- сохраняет hard failure для реально неподтверждённых чисел в narrative;
- включает positive/negative regression tests;
- поднимает benchmark package version до `1.0.1`.

Проверка перед upload:

```bash
python scripts/check_ai_bench_package.py
python -m unittest discover -s tests -p 'test_ai_bench_*.py' -v
```

Authoritative gate после upload:

```text
GitHub Actions / AI-BENCH-001 package gate
GitHub Actions / Python tests
```

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
