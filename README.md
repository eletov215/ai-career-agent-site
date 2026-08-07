# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.1 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.15 |
| Текущий пакет | `SYNC-001 — НУЖНА ПРОВЕРКА НА GITHUB/RENDER` |
| Следующий пакет | `SYNC-002` после подтверждения SYNC-001 |
| Database revision | `20260807_0003` |
| Production | Render остаётся staging/rollback; real VPS отложен до предрелизного INFRA-001 |

> GitHub является главным источником кода. Более новый ZIP текущего чата становится рабочей основой. Секреты, `.env`, базы, dumps, backups, virtualenv, caches и bytecode не входят в репозиторий.

## 1. Назначение проекта

AI Career Agent — Flask-сервис карьерного сопровождения: резюме, карьерный профиль, поиск вакансий, OAuth HeadHunter/SuperJob, PostgreSQL cache Trudvsem и будущий AI-контур.

WSGI entrypoint:

```text
app:app
```

## 2. Статусы пакетов

| Пакет | Статус |
|---|---|
| FND-001 | ВЫПОЛНЕНО |
| FND-002 | ВЫПОЛНЕНО |
| DATA-001 | ВЫПОЛНЕНО |
| DATA-002 | ВЫПОЛНЕНО |
| SEC-001 | ВЫПОЛНЕНО |
| OPS-001 | ВЫПОЛНЕНО; production restore drill перенесён в OPS-002/REL-001 |
| INFRA-PREP-001 | ВЫПОЛНЕНО |
| DOC-001 | В РАБОТЕ как постоянный процесс |
| SYNC-001 | НУЖНА ПРОВЕРКА НА GITHUB/RENDER |
| INFRA-001 | ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА |

## 3. SYNC-001

Trudvsem provider I/O больше не принадлежит Gunicorn/Flask lifecycle.

```text
web request -> PostgreSQL cache -> durable enqueue
external worker -> claim -> provider API -> upsert -> persisted result
```

Компоненты:

- `services/trudvsem_sync.py` — application service;
- `repositories/sync_runs.py` — durable queue/run lifecycle;
- `repositories/sync_workers.py` — heartbeat/liveness;
- `services/sync_lock.py` — PostgreSQL advisory lock / SQLite lockfile;
- `scripts/trudvsem_sync_worker.py` — long-running worker;
- `scripts/sync_trudvsem.py` — one-shot/queue CLI;
- `scripts/start_runtime.py` — Render staging supervisor;
- migration `20260807_0003`.

Архитектурный отчёт: `docs/SYNC001_IMPLEMENTATION.md`. Полный runbook: `docs/SYNC001_RUNBOOK.md`.

## 4. Основной стек

- Python 3.11, Flask, Gunicorn;
- SQLAlchemy 2, Alembic, PostgreSQL 17/Psycopg 3;
- Flask-WTF, Flask-Limiter, Cryptography;
- GitHub Actions;
- Docker multi-target images, Docker Compose и Caddy test TLS;
- HTML, CSS и JavaScript без отдельного frontend build.

## 5. Локальный запуск без контейнеров

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
export APP_ENV=development
python scripts/manage_db.py upgrade
python scripts/start_runtime.py
```

Для запуска только web без worker:

```bash
TRUDVSEM_SYNC_ENABLED=0 gunicorn app:app
```

Production/development требуют реальные secrets из `config.py`. Не помещайте их в команды, screenshots или GitHub.

## 6. SYNC-001 команды

### 6.1 Enqueue only

```bash
python scripts/sync_trudvsem.py --enqueue-only --trigger manual-cli
```

### 6.2 One-shot execution

```bash
python scripts/sync_trudvsem.py --trigger manual-cli
```

### 6.3 Long-running worker

```bash
python scripts/trudvsem_sync_worker.py
```

### 6.4 Docker Compose worker

```bash
docker compose --env-file .env --profile sync up -d sync-worker
```

## 7. Render staging

Для существующего вручную созданного web service Start Command должен быть:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

`render.yaml` содержит это значение. На free staging Gunicorn и worker запускаются как sibling OS processes в одном service container. На будущем VPS worker станет отдельным Compose service без изменения business logic.

## 8. Проверки качества

```bash
python scripts/check_repository_hygiene.py
python scripts/check_document_structure.py
python scripts/infra_manifest_check.py
python -m compileall -q app.py config.py database.py observability.py security.py domain models repositories services operations scripts tests infra
python -m pytest -q
```

GitHub Actions дополнительно:

- поднимает PostgreSQL 17;
- применяет migration `20260807_0003` и выполняет integration tests;
- проверяет SEC-001, OPS-001 и SYNC-001;
- создаёт/восстанавливает encrypted backup;
- валидирует Compose;
- собирает targets `runtime` и `ops`;
- выполняет runtime image smoke.

## 9. Структура репозитория

```text
app.py                         Flask routes, cache reads, durable enqueue
database.py                    SQLAlchemy runtime, revision 20260807_0003
services/trudvsem_sync.py      external sync application service
services/sync_lock.py          cross-process execution lock
repositories/sync_runs.py      durable queue/run lifecycle
repositories/sync_workers.py   external worker heartbeat
scripts/start_runtime.py       Render staging supervisor
scripts/trudvsem_sync_worker.py long-running worker
scripts/sync_trudvsem.py       one-shot/queue CLI
migrations/                    Alembic 0001/0002/0003
Dockerfile / compose.yaml      portable runtime and separate sync profile
docs/                          canonical documents and runbooks
```

## 10. Ближайшие действия

1. Загрузить SYNC-001 в отдельную GitHub-ветку.
2. Получить полностью зелёный CI.
3. На Render изменить Start Command на `scripts/start_runtime.py` и дождаться deploy.
4. Подтвердить revision `20260807_0003`, worker heartbeat и queue-to-terminal smoke.
5. После подтверждения перевести SYNC-001 в ВЫПОЛНЕНО и начать SYNC-002.
