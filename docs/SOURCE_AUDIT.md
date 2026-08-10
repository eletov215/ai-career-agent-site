# AI Career Agent — аудит источников v1.4.13

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.13 |
| Дата | 10 августа 2026 |
| Проверяемый пакет | AUTH-001 candidate implementation |
| Рабочий источник кода | `ai-career-agent-site-main (6).zip` из актуального GitHub `main` |
| Канонический план до обновления | PLAN_CURRENT 1.4.12 |
| Канонический паспорт до обновления | PROJECT_PASSPORT 2.26 |
| Результат | AUTH-001 реализован локально; требуется GitHub/Render/SMTP verification |

## 1. Контрольный статус

SEARCH-004 остаётся ВЫПОЛНЕНО. AUTH-001 переводится из ГОТОВО К СТАРТУ в НУЖНА ПРОВЕРКА. Candidate schema head = `20260810_0008`; production до deploy остаётся `20260809_0007`. DOC-STD-001 v1.1 обязателен.

## 2. Проверка актуального источника кода

| Область | Результат |
|---|---|
| WSGI | `app.py`, `app:app` сохранены |
| Database | `0007` baseline подтверждён; additive `0008` создан |
| Identity | existing `users`, parallel user table не создаётся |
| Password | versioned bounded scrypt, no plaintext/dependency addition |
| Sessions | server-side revocable `auth_sessions`, hash-only bearer storage |
| Action tokens | hash-only, TTL, purpose, supersede/single-use |
| Email | disabled/memory/SMTP STARTTLS adapter; production memory forbidden |
| HTTP security | CSRF, rate limits, no-store/no-referrer, local redirect validation |
| OAuth compatibility | HH/SJ browser identities remain independent until AUTH-002 |
| Backups | inventory includes `auth_sessions` and `auth_tokens` |
| Prohibited artifacts | `.env`, secrets, DB/dump/backup/venv/cache/bytecode excluded from release |

## 3. Реализованный scope AUTH-001

- register/verification/resend/login/logout;
- forgot/reset password;
- active sessions list and revoke controls;
- atomic token use/password reset/session revocation;
- generic register/reset/login failure copy;
- disabled email fail-closed UI;
- auth dashboard/navigation/templates;
- migration/config/Compose/Render/VPS/backup updates;
- focused tests and dedicated CI gate.

AUTH-002 binding, profile, PRIV-001 retention/deletion, MFA/admin/AI/billing не входят.

## 4. Локальные доказательства

```text
compileall passed
full available pytest: 217 passed, 7 skipped
focused AUTH-001 gate: 83 passed, 2 skipped
SQLite migration 0008 -> 0007 -> 0008 passed
Alembic check passed
Jinja parsing passed
```

Flask/Psycopg/PostgreSQL scenarios подтверждаются только GitHub Actions. Checksums фиксируются в release package.

## 5. Ожидаемые внешние доказательства

1. Green `Verify AUTH-001 first-party account controls` и весь workflow.
2. Render `/health/ready`: current/expected `20260810_0008`.
3. `AUTH_EMAIL_BACKEND=smtp`, configured boolean true, secrets absent from logs.
4. Register/verify/login/logout and two-session revoke E2E.
5. Forgot/reset single-use and old-session invalidation E2E.
6. CSRF/rate limit/open-redirect/no-store negative smoke.

## 6. Ограничения и риски

- Production email provider not selected/configured by code package.
- `disabled` is safe default but blocks package completion.
- Existing OAuth rows are not auto-bound.
- Pending/session/token cleanup and identity erasure policy remain future PRIV/OPS work.
- Shared rate-limit storage is required before multiple replicas.

## 7. Rollback

Application revert without touching search/OAuth/sync data. Keep additive `0008` after any real user exists. Downgrade only before account creation or after verified backup and explicit data decision.

## 8. Следующее действие

```text
AUTH-001 CANDIDATE
-> GitHub green
-> Render 0008 + SMTP
-> account E2E
-> AUTH-001 COMPLETE
-> AUTH-002 START
```

## 9. Новые канонические версии

```text
PLAN_CURRENT 1.4.13
PROJECT_PASSPORT 2.27
SOURCE_AUDIT 1.4.13
AUTH001_IMPLEMENTATION 1.0
AUTH001_VERIFICATION_STATUS 1.0
AUTH001_RUNBOOK 1.0
AUTH001_SECURITY_REFERENCE 1.0
DOCUMENT_STANDARD 1.1 (без изменений)
```

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.12 | 10.08.2026 | SEARCH-004 final; AUTH-001 prepared. |
| 1.4.13 | 10.08.2026 | AUTH-001 candidate implemented with migration 0008; external verification pending. |
