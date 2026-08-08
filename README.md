# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.5 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.19 |
| Текущий пакет | `SEARCH-001 — НУЖНА ПРОВЕРКА` |
| Следующий пакет | `SEARCH-002` после подтверждения SEARCH-001 |
| Database revision candidate | `20260808_0005` |
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
| SEARCH-001 | НУЖНА ПРОВЕРКА |
| SEARCH-002 | ЗАПЛАНИРОВАНО |
| INFRA-001 | ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА |

## 3. SEARCH-001 candidate

```text
raw HH / Reed / SuperJob / Trudvsem
→ provider adapter
→ NormalizedVacancy contract
→ common exact-code filters
→ canonical/source persistence
→ presenter
```

Ключевые компоненты:

- `domain/vacancy_contract.py` — typed contract и enums;
- `services/vacancy_normalizer.py` — central normalization;
- `services/search_filters.py` — common filter policy;
- migration `20260808_0005` — canonical code columns/indexes;
- provider/store/repository/presenter integration;
- `tests/test_search_normalization.py` и отдельный CI gate.

Cross-source dedup не входит и остаётся SEARCH-002.

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

После merge SEARCH-001 ожидается revision `20260808_0005`.

## 8. Структура SEARCH-001

```text
domain/vacancy_contract.py
services/vacancy_normalizer.py
services/search_filters.py
models/vacancy.py
repositories/vacancies.py
services/*_provider.py
services/vacancy_store.py
services/vacancy_presenter.py
migrations/versions/20260808_0005_*.py
tests/test_search_normalization.py
```

## 9. Ближайшие действия

1. Candidate branch.
2. Полностью зелёный GitHub Actions.
3. Merge в main.
4. Render revision/health + multi-source search smoke.
5. Закрыть SEARCH-001 и начать SEARCH-002.
