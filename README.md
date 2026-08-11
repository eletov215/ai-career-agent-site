# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.18 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.32 |
| Текущий пакет | `AUTH-002 — НУЖНА ПРОВЕРКА` |
| Следующий после завершения | `PROF-001` |
| Candidate database revision | `20260811_0009` |
| Production до deploy | Render revision `20260810_0008` |

> GitHub является главным источником кода. Более новый ZIP текущего чата становится рабочей основой. Секреты, `.env`, базы, dumps, backups, virtualenv, caches и bytecode не входят в репозиторий.

## 1. Назначение проекта

AI Career Agent — Flask-сервис карьерного сопровождения. WSGI entrypoint: `app:app`. SEARCH-001..004 и AUTH-001 выполнены. AUTH-002 связывает HeadHunter/SuperJob с подтверждённым first-party `User`.

## 2. Статусы пакетов

| Пакет | Статус |
|---|---|
| FND/DATA/SEC/OPS/INFRA-PREP | ВЫПОЛНЕНО |
| SYNC-001/002, SEARCH-001..004 | ВЫПОЛНЕНО |
| AUTH-001 | ВЫПОЛНЕНО |
| AUTH-002 | НУЖНА ПРОВЕРКА |
| DOC-001 | В РАБОТЕ как постоянный процесс |
| PROF/PRIV/SEARCH-005 | ЗАПЛАНИРОВАНО |
| INFRA-001 | ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА |

## 3. AUTH-002 candidate

```text
first-party User is the only browser identity
HH/SuperJob connect requires first-party session
OAuth state bound to user_id + auth_session_id
one external identity -> one User
one provider slot -> one User
encrypted owner-scoped refresh/reconnect/disconnect
migration 20260811_0009
```

Legacy unbound OAuth rows are not linked by email. They may be claimed only after a fresh successful provider OAuth callback. Legacy `hh_user_id`/`superjob_user_id` browser keys no longer authorize dashboard access.

## 4. Security and data

Provider access/refresh tokens remain Fernet-encrypted. Callback code/state, tokens, provider secrets and raw profile payloads are excluded from public copy and logs. Disconnect is POST + CSRF and deletes only the current User connection plus its rollback mirror.

Remote provider token revoke is not a unified candidate contract; AUTH-002 guarantees local encrypted credential deletion.

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

## 7. Проверки качества

```bash
python scripts/check_repository_hygiene.py
python scripts/check_document_structure.py
python scripts/infra_manifest_check.py
python -m compileall -q .
python -m pytest -q
python -m alembic check
```

Local available suite: `236 passed, 8 skipped`; focused AUTH-002 migration/service suite: `7 passed`. GitHub Actions additionally executes Flask routes, PostgreSQL integration, migration, SEC/OPS/SYNC/SEARCH/AUTH regressions and container smoke.

## 8. Deploy gate

Start Command remains:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

Candidate completion requires GitHub green, Render current/expected revision `20260811_0009`, real HH and SuperJob bind/reconnect/disconnect, and a negative cross-user ownership smoke. See `docs/AUTH002_RUNBOOK.md`.

## 9. Pre-release email gate

Gmail API remains staging-only. Before beta/commercial release move to a project-owned domain sender such as `noreply@ai-career-agent.ru` with production-grade transactional delivery, SPF, DKIM and DMARC.
