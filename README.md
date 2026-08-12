# AI Career Agent

| Поле | Значение |
|---|---|
| Канонический план | `docs/PLAN_CURRENT.md` — 1.4.20 |
| Паспорт | `docs/PROJECT_PASSPORT.md` — 2.34 |
| Текущий пакет | `PROF-001 — НУЖНА ПРОВЕРКА` |
| Следующий после завершения | `PROF-002` |
| Candidate database revision | `20260811_0010` |
| Production до deploy | Render revision `20260811_0009` |

> GitHub является главным источником кода. Более новый ZIP текущего чата становится рабочей основой. Секреты, `.env`, базы, dumps, backups, virtualenv, caches и bytecode не входят в репозиторий.

## 1. Назначение

AI Career Agent — Flask-сервис карьерного сопровождения. WSGI entrypoint: `app:app`. SEARCH-001..004, AUTH-001 и AUTH-002 выполнены. PROF-001 добавляет структурированный owner-scoped карьерный профиль с неизменяемой историей подтверждённых версий.

## 2. PROF-001 candidate

```text
first-party User is the owner
one current CareerProfile per User
material save -> immutable CareerProfileVersion
incomplete profile allowed
unchanged save -> no duplicate version
stale editor -> safe conflict
provider/PDF/AI data -> no automatic confirmed facts
migration 20260811_0010
```

UI:

```text
/profile
/profile/edit
/profile/history
/profile/history/<version>
```

Sections: contacts, goals, geography, salary, skills, employment, achievements, education, languages and professional positioning.

## 3. Основной стек

Python 3.11, Flask/Gunicorn, SQLAlchemy/Alembic, PostgreSQL 17/Psycopg 3, GitHub Actions, Docker/Compose, server-rendered HTML/CSS/JS.

## 4. Локальный запуск

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
export APP_ENV=development
python scripts/manage_db.py upgrade
python scripts/start_runtime.py
```

## 5. Проверки качества

```bash
python scripts/check_repository_hygiene.py
python scripts/check_document_structure.py
python scripts/infra_manifest_check.py
python -m compileall -q .
python -m pytest -q
python -m alembic check
```

Dedicated CI step:

```text
Verify PROF-001 structured career profile controls
```

Flask/PostgreSQL route integration is authoritative in GitHub Actions because the isolated local environment may not contain Flask/Psycopg services.

## 6. Branch/merge/deploy gate

```text
branch prof-001-candidate-v1.4.20
-> Pull Request
-> all CI green
-> merge main
-> Render upgrade 0009 -> 0010
-> /health/ready current=expected=20260811_0010
-> profile owner/version/concurrency/restart E2E
-> regression smoke
-> PROF-001 COMPLETE
```

Не загружать candidate напрямую в `main` до Pull Request CI.

## 7. Документация

- `docs/PROF001_IMPLEMENTATION.md`
- `docs/PROF001_VERIFICATION_STATUS.md`
- `docs/PROF001_RUNBOOK.md`
- `docs/PROF001_PROFILE_REFERENCE.md`
- `docs/PLAN_CURRENT.md`
- `docs/PROJECT_PASSPORT.md`
- `docs/SOURCE_AUDIT.md`

Документы следуют DOC-STD-001 v1.1. Gmail API остаётся staging-only; domain sender + SPF/DKIM/DMARC до beta/commercial release не отменяется.


## 8. Инфраструктурная граница

`INFRA-001` остаётся отложенным до предрелизного окна. Render используется как staging/резервная площадка; PROF-001 не меняет hosting strategy, WSGI `app:app` или Start Command.
