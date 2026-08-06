# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.3.5 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.13 |
| Текущий пакет | `INFRA-001 — НУЖНА ПРОВЕРКА НА VPS` |
| OPS-001 | Нужен production backup/restore drill |
| Database revision | `20260804_0002` |
| Production | Render остаётся staging/rollback |

> GitHub является главным источником кода. Более новый ZIP текущего чата становится рабочей основой. Секреты, `.env`, базы, backups, virtualenv, caches и bytecode не входят в репозиторий.

## 1. Назначение проекта

AI Career Agent — Flask-сервис карьерного сопровождения: резюме, карьерный профиль, поиск вакансий, OAuth HeadHunter/SuperJob, кэш Trudvsem и будущий AI-контур.

Текущий WSGI entrypoint:

```text
app:app
```

## 2. Подтверждённые пакеты

| Пакет | Статус |
|---|---|
| FND-001 | ВЫПОЛНЕНО |
| FND-002 | ВЫПОЛНЕНО |
| DATA-001 | ВЫПОЛНЕНО |
| DATA-002 | ВЫПОЛНЕНО |
| SEC-001 | ВЫПОЛНЕНО |
| OPS-001 | НУЖНА ФИНАЛЬНАЯ ПРОВЕРКА |
| INFRA-001 | НУЖНА ПРОВЕРКА НА VPS |

Подробные доказательства: `docs/OPS001_VERIFICATION_STATUS.md` и `docs/INFRA001_VERIFICATION_STATUS.md`.

## 3. Основной стек

- Python 3.11, Flask, Gunicorn;
- SQLAlchemy 2, Alembic, PostgreSQL 17/Psycopg 3;
- Flask-WTF, Flask-Limiter, Cryptography;
- GitHub Actions;
- Docker multi-target images, Docker Compose и Caddy для тестового VPS;
- HTML, CSS и JavaScript без отдельного frontend build.

## 4. Локальный запуск без контейнеров

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
export APP_ENV=development
python scripts/manage_db.py upgrade
gunicorn app:app
```

Production/development требуют реальные секреты из `config.py`. Не помещайте их в команды, screenshots или GitHub.

## 5. INFRA-001: тестовый VPS

### 5.1 Подготовка environment

```bash
cp infra/vps/.env.example .env
chmod 600 .env
```

Заполните `CHANGE_ME` только на сервере.

### 5.2 Direct IPv4 smoke

```bash
python3 scripts/infra_manifest_check.py
docker compose --env-file .env build web ops
docker compose --env-file .env up -d db
docker compose --env-file .env run --rm migrate
docker compose --env-file .env up -d web
curl -fsS http://127.0.0.1:8000/health/ready
```

### 5.3 TLS profile

После создания временной DNS A-записи:

```bash
docker compose --env-file .env --profile tls up -d gateway
```

Полный runbook: `docs/INFRA001_VPS_TEST.md`.

## 6. Автоматический VPS probe

```bash
python scripts/infra_probe.py \
  --base-url https://infra-test.example.com \
  --candidate-id provider-region-plan \
  --country RU \
  --city Moscow \
  --network mobile \
  --device iphone \
  --optional-providers \
  --strict \
  --json-output infra/reports/vps-probe.json \
  --markdown-output infra/reports/vps-probe.md
```

Отчёт очищает credentials, query strings и response bodies. Reed transport reachability не заменяет пакет `REED-COMPAT-001`.

## 7. Проверки качества

```bash
python scripts/check_repository_hygiene.py
python scripts/check_document_structure.py
python scripts/infra_manifest_check.py
python -m compileall -q app.py config.py database.py observability.py security.py domain models repositories services operations scripts tests infra
python -m pytest -q
```

GitHub Actions дополнительно:

- поднимает PostgreSQL 17;
- проверяет миграции и integration tests;
- проверяет SEC-001 и OPS-001;
- создаёт/восстанавливает encrypted backup в отдельную test database;
- валидирует Compose;
- собирает targets `runtime` и `ops`;
- выполняет non-root container health smoke.

## 8. Структура репозитория

```text
app.py                       Flask routes, app:app
config.py                    development/test/production settings
database.py                  SQLAlchemy runtime and health
security.py                  CSRF, rate limits, headers, request limits
observability.py             JSON logs, request ID, metrics, alerts
domain/                      detached domain records
models/                      ORM schema
repositories/                persistence layer
operations/backup.py         encrypted backup/restore
migrations/                  Alembic 0001/0002
infra/gunicorn.conf.py       container/VPS Gunicorn policy
infra/vps/                   env template, Caddy, CI env
scripts/infra_probe.py       VPS/network probe
scripts/infra_manifest_check.py manifest invariants
scripts/infra_container_smoke.sh Docker smoke
docs/                        canonical structured documents
```

## 9. Следующие действия

1. Загрузить пакет в отдельную GitHub-ветку и получить зелёный CI.
2. Создать тестовый VPS-кандидат.
3. Выполнить `docs/INFRA001_VPS_TEST.md` из сетей РФ и РБ.
4. На том же VPS завершить production backup/restore drill OPS-001.
5. Зафиксировать решение в `docs/INFRA001_PROVIDER_DECISION.md`.
6. После подтверждения перейти к `AI-BENCH-001`.
