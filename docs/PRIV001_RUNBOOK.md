# AI Career Agent — runbook PRIV-001

| Поле | Значение |
|---|---|
| Документ | PRIV001_RUNBOOK |
| Пакет | PRIV-001 |
| Версия | 1.2 |
| Дата | 19 августа 2026 |
| Статус | ВЫПОЛНЕНО |

## 1. Назначение

Safe operations/reference для completed export/delete/retention controls. Никогда не публиковать export ZIP/data.json, passwords, cookies, auth/OAuth tokens или image bytes.

## 2. Current production baseline

```text
WSGI app:app
PostgreSQL 20260813_0013
privacy cleanup enabled
worker healthy/non-gating
```

`infra/vps/.env.example` обязателен; actual `.env`, DB/dumps/backups/caches/bytecode не входят в release archive.

## 3. Verified deploy gate

Full GitHub Actions green after CI hotfix r1. Render readiness current=expected `0013`; privacy worker alive/status ok. Start command unchanged:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

## 4. Export operational check

Use current password. Open ZIP locally; do not send personal export into support chat. `manifest.json` and `data.json` must be readable. `assets/` is conditional: absent when no referenced owner assets, present when referenced owned assets exist. Search must not reveal password/auth/OAuth/session secret fields.

## 5. Delete operational check

Use throwaway account for destructive verification. Wrong phrase/password must preserve account. Correct exact phrase `УДАЛИТЬ АККАУНТ` + current password deletes owner subtree and terminates session. Old login/owner URLs must fail; other accounts remain unaffected.

## 6. Retention worker

Do not wait real 7/30/180 days or mutate production timestamps for verification. CI fixtures verify time predicates. Production check is worker health/restart/no-active-data-loss. Controlled one-shot maintenance/test command:

```text
python scripts/cleanup_privacy.py
```

## 7. Logs/privacy

Allowed: event/status/revision/bounded aggregate counts. Forbidden: export payload, email/User ID, resume/profile content, asset IDs/bytes, deletion password, cookies/session/OAuth tokens.

## 8. Incident response

Disable affected privacy route/worker, preserve evidence with secret-free request IDs/aggregates, take verified backup if appropriate, inspect owner predicates and deployment diff. Never request user credentials/export ZIP.

## 9. Rollback

Application revert can retain `0013`; downgrade does not restore deleted accounts. Recovery requires verified backup and explicit decision.

## 10. Next package handoff

SEARCH-005 begins from production `0013`. Audit current source-status/observability/SyncRun telemetry before adding admin authorization and detailed provider health UI.

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 13.08.2026 | Candidate deploy/E2E runbook. |
| 1.1 | 19.08.2026 | Hardened privacy/security deployment controls. |
| 1.2 | 19.08.2026 | Production gate completed; runbook converted to completed operational reference. |


## AI-001 delta / 1.5.0 / 2026-09-14

Verify owner-only AI metadata in export and cascade deletion on disposable accounts. Unknown reservations stay counted globally. Metadata default30days is technical, not a legal retention policy. Current-month budgets cannot be purged mid-period.
