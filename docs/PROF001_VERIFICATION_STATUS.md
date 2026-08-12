# AI Career Agent — статус проверки PROF-001

| Поле | Значение |
|---|---|
| Документ | PROF001_VERIFICATION_STATUS |
| Пакет | PROF-001 |
| Версия | 1.0 |
| Дата | 11 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Candidate revision | `20260811_0010` |

## 1. Контрольный статус

Код, migration, UI, validation and local focused evidence подготовлены. Статус ВЫПОЛНЕНО запрещён до green Pull Request CI, Render `0010` и production E2E.

## 2. Local evidence

| Проверка | Результат |
|---|---|
| full available pytest | 240 passed, 9 skipped |
| extended focused PROF-001 checks | 26 passed, 3 skipped |
| profile migration/service core | 4 passed |
| SQLite 0010 upgrade/downgrade/upgrade | passed |
| Alembic check | passed |
| compileall | passed |
| Jinja parse | 21 templates passed |
| architecture/template/document/infra/hygiene checks | passed |
| Flask routes | prepared; Flask unavailable locally, authoritative in CI |
| PostgreSQL integration | prepared; Psycopg/service required in CI |

## 3. CI gate

Обязательный Pull Request step:

```text
Verify PROF-001 structured career profile controls
```

Он должен включать migration, service, route, auth/repository/template and PostgreSQL integration tests. Full workflow, backup/restore and Docker/Compose smoke также должны быть green.

## 4. Render gate

Ожидаемый `/health/ready` после merge/deploy:

```text
status=ok
database.backend=postgresql
database.persistent=true
migrations.current_revision=20260811_0010
migrations.expected_revision=20260811_0010
migrations.ok=true
auth.email_backend=gmail_api
auth.email_delivery_configured=true
oauth_configured=true
```

## 5. Positive production matrix

| Проверка | Ожидаемый результат |
|---|---|
| owner opens empty `/profile` | profile start state, no error |
| partial save | version 1, incomplete data accepted |
| logout/login | facts/version preserved |
| material update | version 2 created |
| history version 1 | old snapshot unchanged and read-only |
| unchanged save | no version 3 |
| mobile editor | fields/add/remove/save usable |
| Render restart | current profile and history preserved |

## 6. Negative owner/concurrency matrix

- unauthenticated `/profile*` redirects to first-party login;
- second User cannot view/edit/history/version the first User profile;
- stale `expected_version` receives safe `409` and does not overwrite current data;
- missing CSRF receives `400`;
- invalid URL, duplicate skill/language, reversed salary/date ranges receive safe validation error;
- profile facts are absent from structured logs;
- HH/SuperJob snapshots are not copied automatically.

## 7. Regression gate

- AUTH-001 registration/login/logout/session/reset remains green;
- AUTH-002 HH/SuperJob owner connection UI remains green;
- `/dashboard`, `/vacancies` and ordinary vacancy search remain healthy;
- backup inventory includes both profile tables;
- Render logs contain no unexpected `500`, traceback or migration error.

## 8. Решение о статусе

```text
PROF-001 — НУЖНА ПРОВЕРКА
Complete only after CI + Render 0010 + production owner/version/restart E2E
```

## 9. Ограничения

PROF-002 import/review, PROF-003 autosave/drafts, version restore and PRIV-001 export/delete/retention are not completion criteria for PROF-001.

## 10. Rollback

Application revert may retain `0010`. Controlled downgrade is destructive only to profile tables and requires verified backup/explicit data decision after real use.

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 11.08.2026 | Candidate verification matrix for local, CI, Render, owner, version, concurrency, restart and regression gates. |
