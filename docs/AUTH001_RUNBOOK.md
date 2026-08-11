# AI Career Agent — runbook AUTH-001

| Поле | Значение |
|---|---|
| Документ | AUTH001_RUNBOOK |
| Пакет | AUTH-001 |
| Версия | 1.1 |
| Дата | 11 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |

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

В Render Environment задать реальные значения вне GitHub/chat:

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

Production requires exactly one secure SMTP mode. For Mail.ru staging:

AUTH_SMTP_HOST=smtp.mail.ru
AUTH_SMTP_PORT=465
AUTH_SMTP_USE_TLS=0
AUTH_SMTP_USE_SSL=1
AUTH_SMTP_USERNAME=<full Mail.ru email>
AUTH_EMAIL_FROM=<same full Mail.ru email>
AUTH_SMTP_PASSWORD=<external app password>
```

Policy defaults можно не добавлять:

```text
AUTH_SESSION_TTL_SECONDS=43200
AUTH_VERIFICATION_TTL_SECONDS=86400
AUTH_RESET_TTL_SECONDS=3600
AUTH_PASSWORD_MIN_LENGTH=12
```

`AUTH_EMAIL_BACKEND=memory` запрещён в production. При `disabled` deploy остаётся healthy, но registration/reset UI fail-closed и AUTH-001 не закрывается.

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
- logs не содержат email, password, raw action/session token, SMTP credentials/response;
- `/health/ready` содержит только backend/configured boolean.

## 9. Rollback

При application regression revert commit и redeploy. Не downgrade-ить `0008` после real account creation. При SMTP outage переключить `AUTH_EMAIL_BACKEND=disabled`: existing verified users смогут login, но new registration/reset будет честно недоступен.

## 10. Закрытие пакета

Зафиксировать screenshots/JSON/log evidence без секретов, обновить canonical docs, присвоить AUTH-001 `ВЫПОЛНЕНО` и перевести AUTH-002 в `ГОТОВО К СТАРТУ`.

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 10.08.2026 | Создан deployment/config/E2E/security/rollback runbook AUTH-001. |
| 1.1 | 11.08.2026 | Добавлена настройка mutually-exclusive STARTTLS/implicit SSL и Mail.ru `smtp.mail.ru:465` staging recipe. |
