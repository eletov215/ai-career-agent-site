# AI Career Agent — статус проверки PRIV-001

| Поле | Значение |
|---|---|
| Документ | PRIV001_VERIFICATION_STATUS |
| Пакет | PRIV-001 |
| Версия | 1.1 |
| Дата | 19 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Production revision | `20260812_0012` |
| Candidate revision | `20260813_0013` |
| Остаточный gate | Pull Request CI + Render 0013 + destructive production E2E |

## 1. Контрольный статус

Code candidate готов локально. Production ещё не содержит migration `0013`, поэтому PRIV-001 не может считаться выполненным.

## 2. Local automated evidence

| Проверка | Статус |
|---|---|
| Python compile | ПОДТВЕРЖДЕНО |
| PRIV migration/service/config/infra/architecture focused tests | ПОДТВЕРЖДЕНО |
| Route suite in isolated local runtime | expected skip: Flask package absent |
| SQLite 0012 -> 0013 -> 0012 -> 0013 | ПОДТВЕРЖДЕНО |
| Alembic check | ПОДТВЕРЖДЕНО |
| Jinja parse 28 templates | ПОДТВЕРЖДЕНО |
| repository hygiene | ПОДТВЕРЖДЕНО |
| infra manifest | ПОДТВЕРЖДЕНО |

## 3. Required GitHub gate

Dedicated step `Verify PRIV-001 privacy export deletion and retention controls` должен пройти вместе с PostgreSQL migrations/integration, AUTH-001/002, PROF-001/002/003, backup/restore, Docker/Compose/runtime smoke и full tests. При любом failure merge запрещён.

## 4. Required Render gate

После merge/deploy:

```text
status=ok
database.backend=postgresql
database.persistent=true
database.revision=20260813_0013
migrations.current_revision=20260813_0013
migrations.expected_revision=20260813_0013
migrations.ok=true
```

Restart не должен менять revision или повреждать existing profile/resume/search state.

## 5. Production E2E matrix

Использовать отдельный throwaway account A для destructive проверки и независимый account B для isolation.

| Проверка | Ожидание |
|---|---|
| unauth `/privacy-center` | login gate |
| export A | ZIP downloads; manifest/data readable; owned photo/logo included |
| secret scan export | нет password/session/token hashes и OAuth access/refresh |
| wrong confirmation | 400; A остаётся активен |
| wrong password | 400; A остаётся активен |
| correct delete | success page; session cleared |
| relogin A | невозможен |
| old profile/resume URLs A | недоступны |
| account B | данные/сессия B не затронуты |
| local HH/SJ credentials A | удалены; remote provider grant не считается проверенным |
| retention worker | aggregate-only completion event; no identifiers/content |
| restart | `/health/ready` остаётся `0013`; B and system data persist |
| regressions | registration/login, `/profile`, PROF-002, `/resumes`, `/vacancies` штатны |
| Render Logs | no 500/Traceback/migration errors; no export payload/delete password/tokens |

## 6. Automated-only time retention checks

Не ждать 30/180 дней вручную. Time-bound cleanup подтверждается CI fixtures с injected timestamps: stale pending/auth/audit удаляются, active User data сохраняется.

## 7. Security notes

Destructive E2E не выполнять на основном production test account с нужной историей. Remote provider revoke вне current scope; проверяется только local credential deletion.

## 8. Решение о статусе

```text
PRIV-001 — НУЖНА ПРОВЕРКА
Remaining — full CI + Render 0013 + production export/delete/restart/log E2E
Next after completion — SEARCH-005
```

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Local candidate evidence and mandatory external gate recorded. |

## Hardened candidate v1.4.28

Повторный privacy/security аудит перед внешней проверкой усилил candidate: экспорт требует повторного текущего пароля и формируется как согласованный PostgreSQL snapshot; добавлены raw/archive size bounds, SpooledTemporaryFile, safe ZIP entry paths, OAuth profile sanitization и fail-closed owner/draft asset integrity. Account deletion повторно сверяет password hash под User row lock и использует единый lock order для Auth/OAuth rows. Retention cleanup получил bounded batches, orphan ResumeAsset cleanup (7d, только без current/history references), cross-process worker lock/heartbeat и индекс `idx_resume_assets_created`. Backup copies не переписываются account deletion; remote provider-side OAuth revoke не заявляется. Candidate schema остаётся `20260813_0013`; production до merge остаётся `20260812_0012`.
