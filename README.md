# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.9 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.23 |
| Текущий пакет | `SEARCH-003 — НУЖНА ПРОВЕРКА` |
| Следующий пакет | `SEARCH-004` после подтверждения SEARCH-003 |
| Database revision candidate | `20260809_0007` — bounded persistent search snapshots |
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
| SEARCH-001 / SEARCH-002 | ВЫПОЛНЕНО |
| SEARCH-003 | НУЖНА ПРОВЕРКА |
| SEARCH-004 | ЗАПЛАНИРОВАНО |
| INFRA-001 | ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА |

## 3. SEARCH-003 candidate

```text
provider pages
→ canonical filter
→ SEARCH-002 dedup
→ deterministic global sort
→ persistent stable ordinal
→ page slice + honest totals
```

Ключевые компоненты:

- `services/search_aggregation.py` — bounded persistent aggregation и per-provider coverage invariant;
- `repositories/search_snapshots.py` — snapshot/source/candidate/item persistence;
- `models/search_snapshot.py` — isolated TTL schema;
- migration `20260809_0007`;
- `/health/search-pagination?snapshot=<uuid>` — secret-free verification;
- `tests/test_search_pagination.py` и отдельный CI gate.

SEARCH-003 не меняет dedup thresholds, OAuth strategy или canonical `/vacancies` route. Provider-reported totals больше не называются точным post-filter/dedup total.

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
python -m alembic check
```

GitHub Actions дополнительно запускает PostgreSQL 17, migration/integration, SEC/OPS/SYNC/SEARCH gates, encrypted backup/restore, Docker build и runtime smoke.

## 7. Render staging

Start Command:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

После merge SEARCH-003 ожидается revision `20260809_0007`.

## 8. Ближайшие действия

1. Загрузить SEARCH-003 candidate в отдельную branch.
2. Получить полностью зелёный GitHub Actions.
3. Merge в `main`.
4. Проверить Render readiness revision `0007`.
5. Проверить page 0/page 1/page 0 с одним snapshot ID и `/health/search-pagination`.
6. Закрыть SEARCH-003 и начать SEARCH-004.
