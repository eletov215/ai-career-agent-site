# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.11 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.25 |
| Текущий пакет | `SEARCH-004 — НУЖНА ПРОВЕРКА` |
| Следующий пакет | `AUTH-001` после подтверждения SEARCH-004 |
| Database revision | `20260809_0007` — без новой migration в SEARCH-004 |
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
| SEARCH-001 / SEARCH-002 / SEARCH-003 | ВЫПОЛНЕНО |
| SEARCH-004 | НУЖНА ПРОВЕРКА |
| SEARCH-005 | ЗАПЛАНИРОВАНО |
| INFRA-001 | ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА |

## 3. SEARCH-004 candidate

```text
/vacancies                 canonical public search
/vacancies/internal        permanent method-preserving compatibility redirect
services/source_status.py  safe public source-state contract
```

Ключевые свойства:

- raw query string, repeated `source`, SEARCH-003 `snapshot` и `page` сохраняются при redirect;
- forms, pagination, navbar/footer/home CTA генерируют `/vacancies`;
- HH/SuperJob/Reed различают `available`, `degraded`, `temporarily_unavailable`;
- Trudvsem показывается как `cached`/`degraded`, а не live provider;
- public UI не раскрывает exception bodies, tokens, credentials или имена environment variables;
- migration отсутствует, revision остаётся `20260809_0007`.

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
python -m compileall -q app.py config.py database.py observability.py security.py domain models repositories services operations scripts tests infra migrations
python -m pytest -q
python -m alembic check
```

GitHub Actions дополнительно запускает PostgreSQL 17, migration/integration, SEC/OPS/SYNC/SEARCH gates, encrypted backup/restore, Docker build и runtime smoke.

## 7. Render staging

Start Command:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

Ожидаемая revision после SEARCH-004 остаётся `20260809_0007`.

## 8. Ближайшие действия

1. Загрузить SEARCH-004 candidate в отдельную branch.
2. Получить полностью зелёный GitHub Actions.
3. Merge в `main`; проверить `/health/ready` revision `0007`.
4. Проверить `/vacancies` 200.
5. Проверить `/vacancies/internal?<query>` 308 с сохранением query/snapshot/page.
6. Проверить live/cached/degraded source states и отсутствие technical leakage.
7. Закрыть SEARCH-004 и начать AUTH-001.
