# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.7 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.21 |
| Текущий пакет | `SEARCH-002 — НУЖНА ПРОВЕРКА` |
| Следующий пакет | `SEARCH-003` после подтверждения SEARCH-002 |
| Database revision candidate | `20260809_0006` — dedup metadata и reversible grouping |
| Production | Render остаётся staging/rollback; real VPS отложен до предрелизного INFRA-001 |

> GitHub является главным источником кода. Более новый ZIP текущего чата становится рабочей основой. Секреты, `.env`, базы, dumps, backups, virtualenv, caches и bytecode не входят в репозиторий.

## 1. Назначение проекта

AI Career Agent — Flask-сервис карьерного сопровождения: резюме, карьерный профиль, поиск вакансий, OAuth HeadHunter/SuperJob, PostgreSQL cache Trudvsem и будущий AI-контур. WSGI entrypoint: `app:app`.

## 2. Статусы пакетов

| Пакет | Статус |
|---|---|
| FND-001 / FND-002 | ВЫПОЛНЕНО |
| DATA-001 / DATA-002 | ВЫПОЛНЕНО |
| SEC-001 / OPS-001 / INFRA-PREP-001 | ВЫПОЛНЕНО |
| DOC-001 | В РАБОТЕ как постоянный процесс |
| SYNC-001 / SYNC-002 | ВЫПОЛНЕНО |
| SEARCH-001 | ВЫПОЛНЕНО |
| SEARCH-002 | НУЖНА ПРОВЕРКА |
| SEARCH-003 | ГОТОВО К СТАРТУ ПОСЛЕ SEARCH-002 |
| INFRA-001 | ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА |

## 3. SEARCH-002 candidate

```text
canonical provider results
→ exact canonical filters
→ conservative cross-source dedup
→ stable sort
→ presenter
→ one card + all provider links
```

Ключевые компоненты:

- `services/vacancy_deduplication.py` — versioned fingerprint, hard gates, complete-link grouping и explainability;
- `services/vacancy_store.py` / `repositories/vacancies.py` — exact grouping, сохранение нескольких source rows и reversible split;
- `services/vacancy_presenter.py` — multi-source card contract;
- `templates/vacancies_unified.html` — stacked logos и список площадок;
- `tests/test_search_deduplication.py` — positive/negative/persistence/security cases;
- отдельный CI gate `Verify SEARCH-002 cross-source deduplication controls`.

SEARCH-002 добавляет только nullable dedup metadata revision `20260809_0006`, не меняет `/vacancies/internal` и не решает stable total/pagination — это SEARCH-003.

## 4. Основной стек

- Python 3.11, Flask, Gunicorn;
- SQLAlchemy 2, Alembic, PostgreSQL 17/Psycopg 3;
- GitHub Actions;
- Docker/Compose/Caddy test TLS;
- HTML/CSS/JavaScript без отдельного frontend build.

## 5. Локальный запуск

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
export APP_ENV=development
python scripts/manage_db.py upgrade
python scripts/start_runtime.py
```

## 6. Проверки качества

```bash
python scripts/check_repository_hygiene.py
python scripts/check_document_structure.py
python scripts/infra_manifest_check.py
python -m compileall -q app.py config.py database.py observability.py security.py domain models repositories services operations scripts tests infra
python -m pytest -q
```

GitHub Actions дополнительно запускает PostgreSQL 17, migration/integration, SEC/OPS/SYNC/SEARCH gates, encrypted backup/restore, Docker build и runtime smoke.

## 7. Render staging

Start Command:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

После merge SEARCH-002 ожидается revision `20260809_0006`.

## 8. Ближайшие действия

1. Загрузить SEARCH-002 candidate в отдельную branch.
2. Получить полностью зелёный GitHub Actions.
3. Merge в `main`.
4. Проверить Render readiness и multi-source positive/negative smoke.
5. Закрыть SEARCH-002 и начать SEARCH-003.
