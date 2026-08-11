# AI Career Agent — статус проверки AUTH-001

| Поле | Значение |
|---|---|
| Документ | AUTH001_VERIFICATION_STATUS |
| Пакет | AUTH-001 |
| Версия | 1.2 |
| Дата | 11 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Candidate revision | `20260810_0008` |

## 1. Контрольный статус

Safari CSRF hotfix подтверждён production register POST. v1.4.15 GitHub Actions и Render readiness green; Mail.ru реальная отправка на Render Free остановилась `OSError` из-за SMTP egress restriction. v1.4.16 Gmail API HTTPS candidate локально проверяется. Пакет остаётся НУЖНА ПРОВЕРКА до green GitHub Actions и real Render Gmail API email/account E2E.

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
| Dedicated AUTH-001 CI gate | v1.4.15 GREEN; v1.4.16 GMAIL CANDIDATE ОЖИДАЕТСЯ |
| Render current/expected revision `0008` | ПРОЙДЕНО |
| Email transport configured without secret leakage | SMTP readiness ПРОЙДЕНО; MAIL.RU BLOCKED BY RENDER FREE EGRESS; GMAIL API RETEST ОЖИДАЕТСЯ |
| Register/verify/login/logout/revoke E2E | ОЖИДАЕТСЯ RENDER |
| Forgot/reset + old sessions invalid E2E | ОЖИДАЕТСЯ RENDER |

## 3. Локальные доказательства

```text
Full available pytest: 229 passed, 7 skipped
Compileall: passed
Focused AUTH-001 gate: 95 passed, 2 skipped
Config validation: passed
Migration round-trip + Alembic check: passed
Jinja parse: passed
```

Skipped locally: Flask runtime routes, Psycopg and real PostgreSQL service. Они не объявляются пройденными до CI.

## 3.1 Local evidence — SMTP SSL/TLS fallback v1.4.15

```text
python -m compileall config.py services tests scripts     passed
focused config/email/infra/auth tests                     79 passed, 1 skipped
infra_manifest_check.py                                   passed
repository hygiene after cache cleanup                    passed
full pytest in this isolated runtime                      not completed (runtime timeout)
```

The single focused skip is the existing Flask runtime skip in the current isolated environment; the full GitHub workflow remains the authoritative gate. No external SMTP network call is made in CI tests.

## 3.2 Local evidence — Gmail API HTTPS candidate v1.4.16

```text
focused config/email/infra tests                            77 passed
compileall config/services/tests/scripts                   passed
external Google calls in tests                             mocked
database migration                                         none; expected revision 20260810_0008
```

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
auth.email_backend = gmail_api
auth.email_delivery_configured = true
```

Затем пройти runbook с новым test email. В application logs допустимы только `event`, `purpose`, backend, safe `delivery_stage`, provider HTTP status code и exception type; raw email/password/token/provider response отсутствуют.

## 6. Ограничения

AUTH-001 не может быть закрыт при `AUTH_EMAIL_BACKEND=disabled`, даже если migration и login unit tests зелёные: пользователь не сможет подтвердить новый account или выполнить reset. `memory` запрещён в production.

## 7. Rollback

Application revert безопасен. Schema `0008` рекомендуется оставить additive после появления первой real identity. Downgrade — только после backup и подтверждения отсутствия/допустимости потери auth data.

## 8. Следующее действие

```text
GitHub green
-> Render 0008
-> Gmail API HTTPS delivery green
-> full account E2E
-> AUTH-001 COMPLETE
```

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 10.08.2026 | Создана candidate verification matrix AUTH-001. |
| 1.1 | 11.08.2026 | Safari CSRF pass подтверждён; Yandex anti-spam blocker зафиксирован; Mail.ru implicit SSL/TLS candidate ожидает CI/Render E2E. |
| 1.2 | 11.08.2026 | v1.4.15 CI/readiness green; Render Free SMTP egress blocker зафиксирован; Gmail API HTTPS candidate добавлен и ожидает CI/Render E2E. |
