# AI Career Agent — реализация AUTH-001

| Поле | Значение |
|---|---|
| Документ | AUTH001_IMPLEMENTATION |
| Пакет | AUTH-001 |
| Версия | 1.2 |
| Дата | 11 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Основа кода | `ai-career-agent-site-main (11).zip` из актуального GitHub `main` |
| Candidate revision | `20260810_0008` |

## 1. Контрольный статус

AUTH-001 реализован как candidate и не объявляется выполненным до зелёного GitHub Actions, применения migration `20260810_0008`, настройки production email delivery и полного Render E2E: registration, verification, login, logout, password reset и session revoke.

## 2. Цель и границы

Пакет создаёт собственную first-party identity AI Career Agent. HeadHunter и SuperJob сохраняются как независимые внешние подключения и не присваиваются новому пользователю автоматически.

В AUTH-001 входят:

- регистрация по email и паролю;
- подтверждение email;
- вход и выход;
- восстановление пароля;
- отзывные server-side browser sessions;
- завершение одной или всех других сессий;
- безопасная provider-neutral отправка transactional email;
- rate limiting, CSRF и enumeration-safe public responses.

Не входят AUTH-002 OAuth binding, карьерный профиль, импорт/версии резюме, admin center, AI, billing и account deletion/export policy.

## 3. Реализация

### 3.1 First-party identity

Используется существующая таблица `users` из DATA-002. Добавлены nullable поля:

```text
password_hash
password_changed_at
last_login_at
```

Legacy users/OAuth rows остаются совместимыми: отсутствие `password_hash` означает, что first-party password login ещё не настроен.

### 3.2 Пароли

`services/passwords.py` реализует application-owned versioned scrypt:

```text
aca_scrypt$1$32768$8$1$<salt>$<digest>
```

Соль случайная, сравнение constant-time, plaintext не сохраняется и не логируется. Parser ограничивает cost и размер компонентов, поэтому attacker-controlled hash не может бесконтрольно увеличить память/CPU. Неизвестный email проходит dummy verification для более близкого timing profile.

Password policy: минимум 12 символов по умолчанию, максимум 128, запрет коротких/common значений, email local-part и слишком низкого разнообразия.

### 3.3 Sessions

Таблица `auth_sessions` хранит только SHA-256 hash opaque 256-bit token, `user_id`, timestamps, expiry, revoke state/reason и hash user-agent. Raw token находится только в защищённой Flask cookie-сессии. Login вращает browser session; logout/revoke инвалидирует row на сервере. Password reset отзывает все активные сессии атомарно.

### 3.4 Verification/reset tokens

Таблица `auth_tokens` хранит только one-way token hash, purpose, TTL и single-use state. Новый token того же purpose supersede-ит старый. Email verification активирует только pending user; старый token не может реактивировать disabled/уже активный account. Password reset обновляет hash, отзывает sessions и инвалидирует остальные tokens одной transaction.

### 3.5 Email delivery

`services/email_delivery.py` отделяет auth-domain от поставщика:

```text
disabled  production-safe default; UI блокирует registration/reset
memory    deterministic no-network backend только test
auth SMTP adapter: STARTTLS or implicit SSL/TLS
```

Production `smtp` требует sender, host и TLS. Username/password являются Render/VPS secrets и не попадают в GitHub, ZIP или logs. Public `/health/ready` показывает только backend и boolean configured.

### 3.6 Routes и UI

Добавлен blueprint `/auth`:

```text
GET/POST /auth/register
GET/POST /auth/login
POST     /auth/logout
GET/POST /auth/resend-verification
GET/POST /auth/verify
GET/POST /auth/forgot-password
GET/POST /auth/reset-password
POST     /auth/sessions/revoke-others
POST     /auth/sessions/<id>/revoke
```

Authentication pages имеют `no-store`, `Pragma: no-cache`, `Referrer-Policy: strict-origin` и `noindex`. Это скрывает path/query с verification/reset token из Referer, но сохраняет origin для production `WTF_CSRF_SSL_STRICT`. Dashboard показывает first-party identity и active server sessions; HH/SuperJob остаются отдельным блоком до AUTH-002.

## 4. Влияние на код и сайт

Добавлены auth domain/model/repository/service/blueprint/templates/tests. Изменены `app.py`, `config.py`, `database.py`, `StorageServices`, dashboard/navigation, backup inventory, Compose/Render/VPS templates и CI.

Пользователь получает регистрацию, вход, recovery и управление устройствами. Если email backend disabled, UI честно возвращает 503 и не создаёт account, который невозможно подтвердить.

## 5. Database migration

Alembic revision `20260810_0008`:

- добавляет три nullable поля в `users`;
- создаёт `auth_sessions` и `auth_tokens`;
- добавляет unique token-hash constraints и lookup/expiry indexes;
- использует `ON DELETE CASCADE` только от auth rows к `users`;
- не изменяет vacancies, SEARCH-003 snapshots, sync state или OAuth rows.

Downgrade до `20260809_0007` удаляет auth tables/columns и допустим только до появления реальных accounts либо после verified backup и explicit data decision.

## 6. Security controls

- SEC-001 CSRF, secure cookie, trusted hosts, request limits и security headers сохранены.
- POST limits: registration/resend/reset request — 5/hour; login — 10/10 minutes; reset/verify/session actions имеют отдельные limits.
- Register/reset public responses не подтверждают существование email.
- Unknown, wrong-password, pending, disabled и unverified login используют одну public failure формулировку.
- `next` принимает только local absolute path и отклоняет scheme/netloc, `//`, backslash и control chars.
- Auth/action tokens не выводятся в logs; SMTP error body/recipient не логируются.
- Existing provider identities сохраняются отдельно при first-party session rotation/logout до AUTH-002.

## 7. Проверки и доказательства

Локально в candidate environment:

```text
python -m compileall -q .                                passed
pytest -q                                                229 passed, 7 skipped
focused AUTH-001 gate                                   95 passed, 2 skipped
SQLite 0008 upgrade -> 0007 downgrade -> 0008 upgrade   passed
alembic check                                             passed
Jinja template parsing                                    passed
```

Локальные skips относятся к Flask route runtime, Psycopg и реальному PostgreSQL service; они выполняются GitHub Actions и не объявляются пройденными локально.

## 7.1 Gmail API staging transport

`services/email_delivery.py` сохраняет provider-neutral contract и добавляет `GmailApiAuthEmailSender`. Backend `gmail_api` не использует SMTP: он по HTTPS обменивает refresh token на short-lived access token и отправляет RFC 2822 MIME как base64url через Gmail API `users.messages.send`. Постоянный access token не хранится. Configuration требует `AUTH_EMAIL_FROM`, `AUTH_GMAIL_CLIENT_ID`, `AUTH_GMAIL_CLIENT_SECRET`, `AUTH_GMAIL_REFRESH_TOKEN`; secrets остаются только в environment. CI mock-ит token/send HTTP calls. Safe failure telemetry records only `delivery_stage`, HTTP status code and exception type; provider response body and OAuth tokens are never logged.

Это временный staging transport для Render Free. Он не меняет auth business logic и не является целевым коммерческим delivery provider.

## 8. Ограничения и риски

- Yandex staging sender получил внешнюю anti-spam блокировку; Mail.ru adapter работает в коде, но Render Free блокирует SMTP egress. Gmail API HTTPS выбран как временный staging fallback для E2E. До beta/commercial release обязателен доменный sender (целевой пример `noreply@ai-career-agent.ru`) и production-grade transactional delivery с SPF/DKIM/DMARC.
- Email backend disabled по умолчанию; это fail-closed, а не готовая коммерческая delivery.
- HH/SuperJob rows не привязаны к User до AUTH-002.
- Pending users, expired tokens и revoked sessions требуют будущей retention policy/periodic cleanup в PRIV-001/OPS.
- MFA, social login, passwordless, account export/deletion и admin roles не входят в пакет.
- In-memory rate limit backend рассчитан на текущий single-instance staging; shared backend нужен перед horizontal scale.

## 9. Rollback

1. Отключить новые auth entry points или вернуть application commit.
2. Оставить additive revision `0008`, если accounts уже могли быть созданы.
3. Не удалять users/auth rows без verified backup и owner decision.
4. Downgrade `0008 -> 0007` разрешён только до production account creation либо в контролируемом maintenance window.
5. SEARCH/OAuth/sync data не очищать.

## 10. Следующее действие

```text
push AUTH-001 candidate
-> green Verify AUTH-001 first-party account controls
-> Render migration 20260810_0008
-> configure Gmail API OAuth secrets -> verify real HTTPS delivery
-> register -> verify -> login -> session revoke -> logout
-> forgot/reset -> old sessions invalid
-> secret-free logs/readiness
-> AUTH-001 COMPLETE
-> AUTH-002 START
```

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 10.08.2026 | Реализован first-party account candidate: scrypt, tokens, revocable sessions, SMTP adapter, routes/UI, migration 0008 и dedicated CI gate. |
| 1.1 | 11.08.2026 | Добавлен implicit SSL/TLS SMTP mode для Mail.ru; STARTTLS сохранён, plaintext production запрещён, migration отсутствует. |
| 1.2 | 11.08.2026 | Добавлен Gmail API HTTPS staging backend с OAuth refresh-token flow и mocked CI; обязательный переход на доменный sender зафиксирован до beta/commercial release. |
