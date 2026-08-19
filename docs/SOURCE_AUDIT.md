# AI Career Agent — аудит источников v1.4.29

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.29 |
| Дата | 19 августа 2026 |
| Проверяемый пакет | PRIV-001 production completion |
| Рабочий источник кода | GitHub `main` после hardened PRIV-001 v1.4.28 + CI hotfix r1 |
| Production revision | `20260813_0013` |
| Результат | PRIV-001 ВЫПОЛНЕНО; SEARCH-005 ГОТОВО К СТАРТУ |

## 1. Контрольный статус

PRIV-001 прошёл обязательный внешний gate и переводится в **ВЫПОЛНЕНО**. Кодовая база после merge работает на PostgreSQL revision `20260813_0013`; следующий кодовый пакет по канонической очереди — SEARCH-005.

## 2. GitHub evidence

- Full GitHub Actions GREEN после CI hotfix r1.
- Dedicated `Verify PRIV-001 privacy export deletion and retention controls` GREEN.
- PostgreSQL migrations/integration, PROF-001/002/003, AUTH-001/002, encrypted backup/restore, Docker/Compose/runtime smoke и full tests GREEN.
- CI hotfix r1 исправил только устаревшее ожидание route test после успешного account deletion: удалённый User корректно получает `401`, а не `200`; product logic не менялась.

## 3. Render gate

Production `/health/ready` подтверждён:

```text
status=ok
database.backend=postgresql
database.persistent=true
database.revision=20260813_0013
migrations.current_revision=20260813_0013
migrations.expected_revision=20260813_0013
migrations.ok=true
privacy_cleanup.enabled=true
privacy_cleanup.gating=false
privacy_cleanup.worker_alive=true
privacy_cleanup.last_status=ok
```

## 4. Production export evidence

- Export успешно требует текущий пароль и выдаёт ZIP с `manifest.json` и `data.json`.
- На аккаунте без resume assets `photoAssetId`/`universityLogoAssetId` были null и папка `assets/` отсутствовала корректно.
- Поиск по export не обнаружил `password_hash`, `access_token`, `refresh_token`, `session_token`, `token_hash`, `code_verifier`, `oauth_state`.
- На отдельном аккаунте с university logo export asset path/bytes сформировались штатно.
- Пользователь не передавал сам export payload в чат; проверка выполнялась локально.

## 5. Destructive deletion evidence

На отдельном throwaway account подтверждены:

- wrong confirmation phrase и wrong password не удаляют User;
- exact phrase `УДАЛИТЬ АККАУНТ` + current password выполняют delete;
- browser session прекращается; повторный login старого User невозможен;
- прежние owner URLs не раскрывают удалённые данные;
- основной независимый account остаётся штатным;
- `/health/ready` остаётся `0013`.

Remote HH/SJ provider-side grant revoke не считается доказанным: current contract гарантирует удаление локальных credentials и legacy mirrors.

## 6. Restart, retention and final regression

После Render restart подтверждены `0013`, healthy privacy worker, основной account/profile/resume/assets/history/privacy-center/dashboard, HH/SuperJob state и `/vacancies`/ordinary search. Render Logs не показали новых `500`, `Traceback`, `IntegrityError`, migration errors или `privacy cleanup failed`, а также чувствительных password/session/OAuth/resume/profile/image payload.

7/30/180-day time-bound retention не проверялась ожиданием реального времени. Эти semantics подтверждены automated timestamp fixtures/CI; production gate проверял worker liveness, restart safety и отсутствие повреждения active data.

## 7. Privacy/security boundaries

- Export re-authenticated, owner-scoped, bounded/spooled и `no-store`.
- OAuth/provider profile проходит sanitizer; cross-owner asset inconsistency fails closed.
- Delete повторно сверяет password hash под User row lock и координирует Auth/OAuth lock order.
- Orphan ResumeAsset cleanup имеет 7-day technical retention и сохраняет current/history referenced assets.
- Audit identifier-free по структуре, но не называется юридически anonymous.
- Existing backups не переписываются account deletion; backup retention/final legal policy остаются OPS-002/LEGAL-001.

## 8. Rollback

Application revert может оставить additive `0013`. Controlled downgrade `0013 -> 0012` удаляет `privacy_audit_events`/candidate index changes, но не восстанавливает уже удалённый аккаунт. Восстановление возможно только из заранее verified backup по explicit operational/legal decision.

## 9. Следующий пакет

`SEARCH-005 — Центр состояния источников для администратора` переводится в **ГОТОВО К СТАРТУ**. Цель канонического пакета: показывать availability API, latency, import/freshness state; admin details должны быть защищены и не содержать PII/credentials. Dependencies AUTH-001, OPS-001, SYNC-001 выполнены.

## 10. Канонические версии

```text
PLAN_CURRENT 1.4.29
PROJECT_PASSPORT 2.43
SOURCE_AUDIT 1.4.29
PRIV001_IMPLEMENTATION 1.2
PRIV001_VERIFICATION_STATUS 1.2
PRIV001_RUNBOOK 1.2
PRIV001_EXPORT_REFERENCE 1.2
PRIV001_SECURITY_REFERENCE 1.2
DOCUMENT_STANDARD 1.1
```

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.27 | 13.08.2026 | PROF-003 complete; initial PRIV-001 candidate. |
| 1.4.28 | 19.08.2026 | Hardened privacy/security candidate after second audit; external gate pending. |
| 1.4.29 | 19.08.2026 | Green CI + Render `0013` + production export/delete/restart/regression/log evidence; PRIV-001 COMPLETE, SEARCH-005 READY. |
