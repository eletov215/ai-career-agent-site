# AI Career Agent — runbook AUTH-001

| Поле | Значение |
|---|---|
| Документ | AUTH001_RUNBOOK |
| Пакет | AUTH-001 |
| Версия | 1.3 |
| Дата | 11 августа 2026 |
| Статус | ВЫПОЛНЕНО |

## 1. Подготовка branch

```text
branch: auth-001-first-party-account
commit: auth: add first-party account and revocable sessions
```

Загрузить полный project ZIP с сохранением dotfiles. Не добавлять `.env`, credentials, DB/dumps/backups, virtualenv, caches или bytecode.

## 2. GitHub Actions

Дождаться полностью зелёного workflow, особенно:

```text
Verify AUTH-001 first-party account controls
Verify PostgreSQL migrations
Run PostgreSQL integration test
Verify SEC-001 security controls
Verify PostgreSQL encrypted backup and restore
Build/Smoke-test INFRA-001 container targets
Run tests
```

PR не merge-ить при любом красном auth/security/migration step.

## 3. Production email configuration

### 3.1 Current Render Free staging profile — Gmail API over HTTPS

Render Environment values are secrets and must remain outside GitHub/chat:

```text
AUTH_EMAIL_BACKEND=gmail_api
AUTH_EMAIL_FROM=<authorized Gmail sender>
AUTH_EMAIL_FROM_NAME=AI Career Agent
AUTH_GMAIL_CLIENT_ID=<OAuth client id>
AUTH_GMAIL_CLIENT_SECRET=<OAuth client secret>
AUTH_GMAIL_REFRESH_TOKEN=<OAuth refresh token>
AUTH_GMAIL_TIMEOUT_SECONDS=8
```

Do not configure a permanent access token: the adapter obtains a short-lived access token from the refresh token for each delivery attempt. The OAuth grant must use only the `gmail.send` scope. While Google Auth Platform remains in Testing, the staging refresh token can expire and may require re-authorization; `invalid_grant`/HTTP 400 is handled as fail-closed delivery failure. `/health/ready` validates presence of config, while real delivery is proven only by `auth_email_delivered` plus receipt of the message.

### 3.2 SMTP compatibility

The SMTP backend remains supported for VPS/paid infrastructure:

```text
AUTH_EMAIL_BACKEND=smtp
AUTH_EMAIL_FROM=<verified sender>
AUTH_EMAIL_FROM_NAME=AI Career Agent
AUTH_SMTP_HOST=<provider host>
AUTH_SMTP_PORT=<provider port>
AUTH_SMTP_USERNAME=<secret if required>
AUTH_SMTP_PASSWORD=<secret if required>
AUTH_SMTP_USE_TLS=<1 for STARTTLS, otherwise 0>
AUTH_SMTP_USE_SSL=<1 for implicit SSL/TLS, otherwise 0>
AUTH_SMTP_TIMEOUT_SECONDS=8
```

`memory` is forbidden in production; `disabled` is fail-closed.

### 3.3 Mandatory pre-release domain migration

Gmail API is staging-only. Before beta/commercial release switch email delivery to a project-owned domain sender, target example `noreply@ai-career-agent.ru`, through a production-grade transactional provider or owned mail infrastructure. Configure SPF, DKIM and DMARC, verify sender/domain reputation and keep the provider-neutral AUTH business logic unchanged. This gate is mandatory and is not satisfied by personal Gmail.

## 4. Deploy

Start Command не менять:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

После `Live` проверить `/health/ready` и revision `20260810_0008`.

## 5. Registration/verification E2E

1. Открыть `/auth/register` в private browser.
2. Зарегистрировать уникальный test email и сильный пароль.
3. Убедиться, что публичный ответ generic и письмо приходит.
4. Открыть verification link; GET только показывает confirmation form.
5. POST confirmation; account становится active.
6. Повторное использование link возвращает neutral invalid/expired response.
7. Войти через `/auth/login`; destination `/dashboard`.
8. Проверить, что dashboard показывает email и текущую server session.

## 6. Sessions/logout E2E

1. Войти на втором браузере/телефоне.
2. На dashboard увидеть две active sessions.
3. Завершить вторую session и убедиться, что она больше не авторизует.
4. `Завершить другие` сохраняет current session.
5. POST logout завершает current first-party session.
6. HH/SuperJob browser identity остаётся отдельной до AUTH-002.

## 7. Password reset E2E

1. Запросить `/auth/forgot-password` для существующего и несуществующего email; public copy одинаковая.
2. Открыть real reset link.
3. Установить новый пароль.
4. Старый reset token повторно не работает.
5. Старый пароль не работает; новый работает.
6. Все ранее активные first-party sessions закрыты.

## 8. Security/log checks

- auth pages: `Cache-Control: no-store`, `Referrer-Policy: strict-origin`; token path/query are stripped from Referer, but HTTPS form POST retains origin for strict CSRF validation;
- POST без CSRF: neutral 400;
- repeated login/register/reset достигают controlled 429;
- external/backslash `next` не выполняет open redirect;
- logs не содержат email, password, raw action/session token, SMTP credentials/response or Gmail OAuth tokens; Gmail failures may expose only safe `delivery_stage`, HTTP status code and exception type;
- `/health/ready` содержит только backend/configured boolean.

## 9. Rollback

При application regression revert commit и redeploy. Не downgrade-ить `0008` после real account creation. При email-provider outage переключить `AUTH_EMAIL_BACKEND=disabled`: existing verified users смогут login, но new registration/reset будет честно недоступен.

## 10. Закрытие пакета

Production evidence зафиксирован без секретов; AUTH-001 присвоен статус `ВЫПОЛНЕНО`, AUTH-002 переведён в `ГОТОВО К СТАРТУ`. Этот runbook остаётся regression/incident reference.

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 10.08.2026 | Создан deployment/config/E2E/security/rollback runbook AUTH-001. |
| 1.1 | 11.08.2026 | Добавлена настройка mutually-exclusive STARTTLS/implicit SSL и Mail.ru `smtp.mail.ru:465` staging recipe. |
| 1.2 | 11.08.2026 | Current Render Free recipe переведён на Gmail API HTTPS; добавлен обязательный pre-release переход на доменный sender с SPF/DKIM/DMARC. |
| 1.3 | 11.08.2026 | Runbook closure: Gmail API delivery и полный AUTH production E2E подтверждены; AUTH-001 complete, AUTH-002 ready. |
