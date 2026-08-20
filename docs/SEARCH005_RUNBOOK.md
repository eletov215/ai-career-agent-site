# AI Career Agent — runbook SEARCH-005

| Поле | Значение |
|---|---|
| Документ | SEARCH005_RUNBOOK |
| Пакет | SEARCH-005 |
| Версия | 1.0 |
| Дата | 19 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |

## 1. Pre-deploy

1. Use the verified current GitHub main ZIP.
2. Confirm `database.CURRENT_REVISION=20260819_0014` in candidate.
3. Set `SEARCH_ADMIN_EMAILS` in Render to the verified test administrator email; do not commit real emails into repository examples.
4. Keep `SOURCE_HEALTH_RECORDING_ENABLED=1` and default stale threshold unless intentionally changed.
5. Confirm `.env`, databases, dumps, backups and secrets are absent from GitHub/PATCH.

## 2. GitHub gate

Required:

```text
Verify SEARCH-005 admin source health controls
Verify SEARCH-001..004 regressions
Verify SYNC-001/002
Verify AUTH-001/002
Verify PROF-001/002/003
Verify PRIV-001
Verify PostgreSQL migrations/integration
Verify encrypted backup/restore
Run tests
Docker/Compose runtime smoke
```

Any failure blocks merge.

## 3. Deploy

Start command unchanged. After Live, `/health/ready` must show current=expected `20260819_0014`, PostgreSQL persistent and status ok.

## 4. Access E2E

- unauthenticated `/admin/sources` -> login;
- verified ordinary User -> neutral 404;
- allowlisted verified admin -> source center;
- remove email from env/redeploy -> access disabled.

## 5. Functional E2E

1. Open HTML and JSON; four providers present.
2. Confirm no tokens, body, user query, email or IDs.
3. Execute ordinary searches that touch HH/SuperJob/Reed.
4. Refresh admin center; timestamps/latency/safe state update.
5. Trigger/observe Trudvsem sync; run/worker freshness appears.
6. Restart Render; latest persistent source states remain.
7. Public `/vacancies` and public source-state UI unchanged.

## 6. Negative/security E2E

- direct URL ordinary User -> 404;
- repeated requests -> bounded rate limit;
- table/API do not expose env values;
- simulated provider failure stores category/class only, not exception message/body;
- page load performs no external probe.

## 7. Logs

Allowed: provider key, safe outcome, bounded latency, failure category, record/update result. Forbidden: credentials, response body, URL query, user search terms, PII, OAuth/session tokens.

## 8. Rollback

1. Remove/empty `SEARCH_ADMIN_EMAILS` for immediate access shutdown.
2. Application revert may keep 0014.
3. Controlled downgrade 0014 -> 0013 removes only source health state.
4. No user/search/profile/resume/privacy data is deleted.

## 9. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 19.08.2026 | Deploy, authorization, provider observation, restart, privacy and rollback runbook created. |
