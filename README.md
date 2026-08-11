# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.16 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.30 |
| Текущий пакет | `AUTH-001 — НУЖНА ПРОВЕРКА` |
| Следующий пакет | `AUTH-002` после подтверждения AUTH-001 |
| Candidate database revision | `20260810_0008` |
| Production до deploy | Render revision `20260810_0008` |

> GitHub является главным источником кода. Более новый ZIP текущего чата становится рабочей основой. Секреты, `.env`, базы, dumps, backups, virtualenv, caches и bytecode не входят в репозиторий.

## 1. Назначение проекта

AI Career Agent — Flask-сервис карьерного сопровождения. WSGI entrypoint: `app:app`. SEARCH-001..004 подтверждены; AUTH-001 добавляет собственный email/password account поверх существующего `User`.

## 2. Статусы пакетов

| Пакет | Статус |
|---|---|
| FND/DATA/SEC/OPS/INFRA-PREP | ВЫПОЛНЕНО |
| SYNC-001/002, SEARCH-001..004 | ВЫПОЛНЕНО |
| DOC-001 | В РАБОТЕ как постоянный процесс |
| AUTH-001 | НУЖНА ПРОВЕРКА |
| AUTH-002 / PROF / PRIV / SEARCH-005 | ЗАПЛАНИРОВАНО |
| INFRA-001 | ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА |

## 3. AUTH-001 candidate

```text
existing users + password fields
auth_sessions + auth_tokens
versioned scrypt
/auth registration, verification, login, logout, reset, session revoke
provider-neutral disabled/memory/SMTP email
```

Ключевые свойства: password/token plaintext не сохраняется; sessions server-side revocable; reset отзывает все sessions; public account-recovery/login copy enumeration-safe; HH/SJ остаются independent до AUTH-002.

## 4. Email delivery

Production default `AUTH_EMAIL_BACKEND=disabled` fail-closed. Текущий Render Free staging использует `AUTH_EMAIL_BACKEND=gmail_api` через HTTPS и OAuth refresh token; SMTP adapters сохраняются для VPS/paid infrastructure. `memory` используется только в test и запрещён в production. Gmail API — временный staging transport: до beta/commercial release обязателен sender собственного домена с SPF/DKIM/DMARC.

## 5. Основной стек

Python 3.11, Flask/Gunicorn, SQLAlchemy/Alembic, PostgreSQL 17/Psycopg 3, GitHub Actions, Docker/Compose, server-rendered HTML/CSS/JS.

## 6. Локальный запуск

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
export APP_ENV=development
python scripts/manage_db.py upgrade
python scripts/start_runtime.py
```

Для no-network local mail sink можно использовать `AUTH_EMAIL_BACKEND=memory` только не в production.

## 7. Проверки качества

```bash
python scripts/check_repository_hygiene.py
python scripts/check_document_structure.py
python scripts/infra_manifest_check.py
python -m compileall -q .
python -m pytest -q
python -m alembic check
```

Локально подтверждено: `229 passed, 7 skipped`; focused AUTH-001 gate: `95 passed, 2 skipped`; migration `0008 -> 0007 -> 0008` и `alembic check` пройдены. GitHub Actions дополнительно выполняет dedicated AUTH-001 gate, PostgreSQL migration/integration, SEC/OPS/SYNC/SEARCH regressions, backup/restore и container smoke.

## 8. Render staging

Start Command не меняется:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

Ожидаемая revision после candidate deploy: `20260810_0008`. Полная verification требует SMTP и account E2E по `docs/AUTH001_RUNBOOK.md`.

## 9. Ближайшие действия

1. Branch `auth-001-first-party-account`.
2. Green GitHub Actions.
3. Configure SMTP secrets вне GitHub/chat.
4. Merge/deploy; readiness `0008`.
5. Register/verify/login/session revoke/logout/reset E2E.
6. Закрыть AUTH-001 и начать AUTH-002.
