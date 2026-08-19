# AI Career Agent — runbook PRIV-001

| Поле | Значение |
|---|---|
| Документ | PRIV001_RUNBOOK |
| Пакет | PRIV-001 |
| Версия | 1.1 |
| Дата | 19 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |

## 1. Назначение

Safe deploy/verification для export/delete/retention. Никогда не публиковать export ZIP, `data.json`, email, password, hashes, cookies, session/OAuth tokens или image bytes в screenshots/log reports.

## 2. Pre-deploy

1. Branch from current GitHub `main` after PROF-003 COMPLETE.
2. Проверить `app.py`, WSGI `app:app`, `database.CURRENT_REVISION=20260813_0013`.
3. `infra/vps/.env.example` должен присутствовать; actual `.env`, DB/dumps/backups/caches/bytecode отсутствуют.
4. Проверить `0013 -> 0012 -> 0013`; backup inventory includes `privacy_audit_events`.
5. New privacy env knobs contain no secrets.

## 3. GitHub gate

Обязательные steps:

```text
Verify PRIV-001 privacy export deletion and retention controls
Verify PROF-003 server resume draft and version controls
Verify PROF-002 resume import review controls
Verify PROF-001 structured career profile controls
Verify AUTH-001 / AUTH-002
Verify PostgreSQL migrations + integration
Verify PostgreSQL encrypted backup and restore
Docker/Compose/runtime smoke
Run tests
```

При любом failure merge запрещён.

## 4. Deploy

Start command не меняется:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

После Live `/health/ready` должен показать current=expected `20260813_0013`, persistent PostgreSQL, status=ok. Privacy cleanup worker запускается sibling process на Render; Compose/VPS может использовать отдельный profile `privacy`.

## 5. Export E2E

На throwaway account A создать минимум: verified account, profile version, resume draft/version/photo, при возможности HH/SJ local connection. Затем:

1. `/privacy-center` -> `Скачать мои данные`.
2. Открыть ZIP локально, не отправлять его в чат.
3. `manifest.json` readable; `data.json` readable.
4. Photo/logo files открываются.
5. Поиск по archive: не должно быть известного password, OAuth access/refresh token, session/token hash.
6. PDF binary не ожидается, потому что server его не хранит.

## 6. Delete negative/positive E2E

1. Wrong phrase -> 400, account remains.
2. Correct phrase + wrong password -> 400, account remains.
3. Убедиться, что account B работает.
4. Correct phrase `УДАЛИТЬ АККАУНТ` + current password A -> success.
5. Browser A session terminated; relogin A fails.
6. Old A profile/resume/history/version URLs не раскрывают данные.
7. B remains unaffected.
8. Не утверждать remote HH/SJ grant revoked; подтверждается только local credential removal.

## 7. Retention worker

Production не требует ожидания 30/180 дней. CI time fixtures доказывают cleanup rules. В Render Logs достаточно увидеть штатный `privacy_retention_cleanup` event с aggregate counts. Не запускать ручную очистку с искусственно изменёнными production timestamps.

One-shot command для controlled maintenance/test environment:

```text
python scripts/cleanup_privacy.py
```

## 8. Restart/regression

После E2E выполнить Render restart. Проверить `/health/ready=0013`, account B, `/profile`, PROF-002 import, `/resumes`, `/vacancies`, ordinary search и login/logout.

## 9. Logs/privacy

Allowed: event, aggregate counts, status/revision. Forbidden: exported data, User/email, resume/profile content, asset IDs/bytes, filename/hash, deletion password, cookies/session/OAuth tokens.

## 10. Rollback

1. Остановить new privacy operations при incident.
2. Сделать verified backup если требуется rollback schema.
3. Application revert может оставить `0013`.
4. Downgrade `0013 -> 0012` removes only identifier-free audit table.
5. Account deletion cannot be undone by application/schema rollback.

## 11. Закрытие

После full green CI + Render 0013 + destructive E2E + restart/log regression: PRIV-001 -> ВЫПОЛНЕНО, следующий SEARCH-005.

## 12. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Created deploy/export/delete/retention/restart/log verification runbook. |

## Hardened candidate v1.4.28

Повторный privacy/security аудит перед внешней проверкой усилил candidate: экспорт требует повторного текущего пароля и формируется как согласованный PostgreSQL snapshot; добавлены raw/archive size bounds, SpooledTemporaryFile, safe ZIP entry paths, OAuth profile sanitization и fail-closed owner/draft asset integrity. Account deletion повторно сверяет password hash под User row lock и использует единый lock order для Auth/OAuth rows. Retention cleanup получил bounded batches, orphan ResumeAsset cleanup (7d, только без current/history references), cross-process worker lock/heartbeat и индекс `idx_resume_assets_created`. Backup copies не переписываются account deletion; remote provider-side OAuth revoke не заявляется. Candidate schema остаётся `20260813_0013`; production до merge остаётся `20260812_0012`.
