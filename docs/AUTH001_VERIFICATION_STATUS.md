# AI Career Agent — статус проверки AUTH-001

| Поле | Значение |
|---|---|
| Документ | AUTH001_VERIFICATION_STATUS |
| Пакет | AUTH-001 |
| Версия | 1.0 |
| Дата | 10 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Candidate revision | `20260810_0008` |

## 1. Контрольный статус

Код и локальные проверки готовы. Пакет остаётся НУЖНА ПРОВЕРКА до green GitHub Actions и real Render email/account E2E.

## 2. Матрица критериев

| Критерий | Статус |
|---|---|
| Existing `users` используется как identity root | ПРОЙДЕНО ЛОКАЛЬНО |
| Email normalization + unique identity | ПРОЙДЕНО ЛОКАЛЬНО |
| Scrypt salted/versioned hash; no plaintext | ПРОЙДЕНО ЛОКАЛЬНО |
| Verification/reset TTL + one-way + single-use | ПРОЙДЕНО ЛОКАЛЬНО |
| Atomic verification/reset/session revocation | ПРОЙДЕНО ЛОКАЛЬНО |
| Session rotation + server-side logout/revoke | ПРОЙДЕНО ЛОКАЛЬНО |
| Enumeration-safe register/reset/login copy | ПРОЙДЕНО ЛОКАЛЬНО |
| CSRF/rate-limit/no-store/strict-origin templates | SAFARI HOTFIX ПОДГОТОВЛЕН; CI/RENDER RETEST ОЖИДАЕТСЯ |
| Migration `0008 -> 0007 -> 0008` | ПРОЙДЕНО SQLITE; POSTGRESQL CI ОЖИДАЕТСЯ |
| Dedicated AUTH-001 CI gate | ОЖИДАЕТСЯ GITHUB |
| Render current/expected revision `0008` | ОЖИДАЕТСЯ |
| SMTP configured without secret leakage | ОЖИДАЕТСЯ OPERATOR/RENDER |
| Register/verify/login/logout/revoke E2E | ОЖИДАЕТСЯ RENDER |
| Forgot/reset + old sessions invalid E2E | ОЖИДАЕТСЯ RENDER |

## 3. Локальные доказательства

```text
Full available pytest: 217 passed, 7 skipped
Compileall: passed
Focused AUTH-001 gate: 83 passed, 2 skipped
Config validation: passed
Migration round-trip + Alembic check: passed
Jinja parse: passed
```

Skipped locally: Flask runtime routes, Psycopg and real PostgreSQL service. Они не объявляются пройденными до CI.

## 4. GitHub gate

Ожидаемый workflow step:

```text
Verify AUTH-001 first-party account controls
```

Он должен включать password, service, route, migration, config/template и PostgreSQL integration tests. Все SEC/OPS/SYNC/SEARCH/backup/container regressions также должны остаться зелёными.

## 5. Render gate

После deploy:

```text
/health/ready
current_revision  = 20260810_0008
expected_revision = 20260810_0008
database.ok       = true
persistent        = true
auth.email_backend = smtp
auth.email_delivery_configured = true
```

Затем пройти runbook с новым test email. В application logs допустимы только `event`, `purpose`, backend и безопасный result code; raw email/password/token/SMTP response отсутствуют.

## 6. Ограничения

AUTH-001 не может быть закрыт при `AUTH_EMAIL_BACKEND=disabled`, даже если migration и login unit tests зелёные: пользователь не сможет подтвердить новый account или выполнить reset. `memory` запрещён в production.

## 7. Rollback

Application revert безопасен. Schema `0008` рекомендуется оставить additive после появления первой real identity. Downgrade — только после backup и подтверждения отсутствия/допустимости потери auth data.

## 8. Следующее действие

```text
GitHub green
-> Render 0008
-> SMTP green
-> full account E2E
-> AUTH-001 COMPLETE
```

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 10.08.2026 | Создана candidate verification matrix AUTH-001. |
