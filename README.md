# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.3 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.17 |
| Текущий пакет | `SYNC-002 — НУЖНА ПРОВЕРКА` |
| Следующий пакет | `SEARCH-001` после подтверждения SYNC-002 |
| Database revision candidate | `20260807_0004` |
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
| FND-001 / FND-002 | ВЫПОЛНЕНО |
| DATA-001 / DATA-002 | ВЫПОЛНЕНО |
| SEC-001 | ВЫПОЛНЕНО |
| OPS-001 | ВЫПОЛНЕНО; production restore drill перенесён в OPS-002/REL-001 |
| INFRA-PREP-001 | ВЫПОЛНЕНО |
| DOC-001 | В РАБОТЕ как постоянный процесс |
| SYNC-001 | ВЫПОЛНЕНО / PRODUCTION VERIFIED |
| SYNC-002 | НУЖНА ПРОВЕРКА |
| INFRA-001 | ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА |

## 3. SYNC-002

SYNC-002 добавляет incremental freshness/cleanup поверх external worker SYNC-001:

```text
committed watermark
→ bounded modifiedFrom/modifiedTo window
→ persistent page offset/total
→ idempotent lifecycle upsert
→ complete window
→ TTL closure + retention purge
```

Основные компоненты:

- `models/sync_checkpoint.py` — durable watermark/cursor/retry;
- `repositories/sync_checkpoints.py` — checkpoint contract;
- `services/trudvsem_provider.py` — page/total/modified window/lifecycle;
- `services/trudvsem_sync.py` — bootstrap/incremental continuation;
- `services/vacancy_store.py` и `repositories/vacancies.py` — active/closed/cleanup;
- migration `20260807_0004`;
- `docs/SYNC002_IMPLEMENTATION.md` и `docs/SYNC002_RUNBOOK.md`.

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

## 6. Sync-команды

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

## 7. SYNC-002 policy defaults

```text
TRUDVSEM_SYNC_INTERVAL=1800
TRUDVSEM_SYNC_ITEMS=300
TRUDVSEM_SYNC_BATCH=10
TRUDVSEM_SYNC_WATERMARK_OVERLAP_SECONDS=300
TRUDVSEM_VACANCY_TTL_DAYS=45
TRUDVSEM_CLOSED_RETENTION_DAYS=30
TRUDVSEM_RETRY_BASE_SECONDS=60
TRUDVSEM_RETRY_MAX_SECONDS=3600
```

Defaults безопасны; существующий Render service может работать без ручного добавления новых variables. Для явной production policy их можно задать в Environment.

## 8. Render staging

Start Command:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

На free staging Gunicorn и worker работают как sibling OS processes в одном container. На будущем VPS worker станет отдельным Compose service.

## 9. Проверки качества

```bash
python scripts/check_repository_hygiene.py
python scripts/check_document_structure.py
python scripts/infra_manifest_check.py
python -m compileall -q app.py config.py database.py observability.py security.py domain models repositories services operations scripts tests infra
python -m pytest -q
```

GitHub Actions дополнительно:

- поднимает PostgreSQL 17;
- применяет migration `20260807_0004` и выполняет integration tests;
- проверяет SEC-001, OPS-001, SYNC-001 и SYNC-002;
- создаёт/восстанавливает encrypted backup с `sync_checkpoints` inventory;
- валидирует Compose, builds и runtime image smoke.

## 10. Структура репозитория

```text
app.py                          Flask routes/cache/status
database.py                     SQLAlchemy runtime, revision 20260807_0004
models/sync_checkpoint.py       incremental checkpoint state
repositories/sync_checkpoints.py watermark/cursor/retry persistence
services/trudvsem_sync.py       resumable external sync service
services/trudvsem_provider.py   Trudvsem page/change-feed adapter
repositories/vacancies.py       lifecycle upsert/cleanup
scripts/start_runtime.py        Render staging supervisor
scripts/trudvsem_sync_worker.py long-running worker
scripts/sync_trudvsem.py        one-shot/queue CLI
migrations/                     Alembic 0001/0002/0003/0004
Dockerfile / compose.yaml       portable runtime and sync profile
docs/                           canonical documents and runbooks
```

## 11. Ближайшие действия

1. Загрузить candidate SYNC-002 в отдельную ветку.
2. Получить полностью зелёный CI.
3. Merge только после зелёного CI.
4. На Render подтвердить revision `20260807_0004`, checkpoint/window/watermark, continuation, retry preservation и cleanup.
5. После подтверждения перевести SYNC-002 в ВЫПОЛНЕНО и начать SEARCH-001.
