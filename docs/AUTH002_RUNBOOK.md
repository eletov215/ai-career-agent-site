# AI Career Agent — runbook AUTH-002

| Поле | Значение |
|---|---|
| Документ | AUTH002_RUNBOOK |
| Пакет | AUTH-002 |
| Версия | 1.0 |
| Дата | 11 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |

## 1. Назначение

Runbook описывает deploy и реальную проверку owner-bound HeadHunter/SuperJob OAuth connections. Не публиковать authorization codes, access/refresh tokens, provider secrets, cookies или database credentials.

## 2. Pre-deploy

1. Подтвердить baseline GitHub `main` и отсутствие `.env`, DB, dumps, backups, caches, bytecode.
2. Проверить `app.py`, WSGI `app:app`, `database.CURRENT_REVISION=20260811_0009`.
3. Убедиться, что HH/SuperJob callback URLs в provider console соответствуют текущему Render domain.
4. Не менять Gmail API AUTH-001 transport: он не связан с OAuth provider identities.

## 3. GitHub gate

Обязательные steps:

```text
Verify AUTH-002 first-party OAuth identity ownership controls
Verify PostgreSQL migrations
Run PostgreSQL integration test
Verify SEC-001 / AUTH-001 regressions
Run tests
Docker/Compose runtime smoke
```

External provider HTTP в CI должен быть mocked.

## 4. Deploy

Start Command не меняется:

```text
python scripts/manage_db.py upgrade && python scripts/start_runtime.py
```

После `Live` проверить `/health/ready`:

```text
status=ok
database.backend=postgresql
database.persistent=true
migrations.current_revision=20260811_0009
migrations.expected_revision=20260811_0009
migrations.ok=true
```

## 5. HeadHunter E2E

1. Войти в verified first-party account.
2. Dashboard → `Подключить HeadHunter`.
3. Авторизовать test HH identity.
4. Callback должен вернуть dashboard без OAuth query в login/flash.
5. Проверить status `Подключён`, provider display metadata и encrypted row persistence.
6. Logout/login first-party account: connection остаётся owner-scoped.
7. Повторить connect той же HH identity: обновляется та же row.
8. Нажать disconnect POST: dashboard показывает отсутствие connection; unified и legacy mirror credentials удалены.

## 6. SuperJob E2E

Повторить шаги HeadHunter для SuperJob. Дополнительно проверить refresh path при истекающем token, если provider test account/TTL позволяет.

## 7. Ownership negative E2E

1. Создать/использовать второй verified AI Career Agent account.
2. Попытаться подключить external identity, уже связанную с первым User.
3. Ожидается safe conflict без раскрытия owner/email и без изменения row.
4. У первого User connection остаётся рабочей.
5. У одного User попытка подключить другой account того же provider отклоняется до disconnect текущего.

## 8. Security checks

- connect требует first-party session;
- callback state привязан к `user_id` и `auth_session_id`;
- callback после logout/session revoke возвращает query-safe 401;
- disconnect только POST + CSRF;
- dashboard не показывает foreign rows;
- logs не содержат `code`, raw state, tokens, provider secrets или profile JSON;
- legacy `hh_user_id`/`superjob_user_id` cookie/session keys не дают авторизацию.

## 9. Observability

Безопасные events:

```text
oauth_connection_bound
oauth_connection_conflict
oauth_connection_disconnected
```

Допустимы только provider, outcome/conflict code и boolean existence. External IDs, emails и credentials не логируются.

## 10. Rollback

1. При application regression вернуть предыдущий commit.
2. Revision `0009` оставить; constraint backward-compatible.
3. При необходимости downgrade `0009 -> 0008` в maintenance window; rows сохраняются.
4. Не восстанавливать provider IDs как browser login.
5. При credential exposure удалить local connection, rotate provider secret/token и применить SEC/OPS incident procedure.

## 11. Exclusions

Remote revoke не считается обязательным E2E candidate. Account merge/transfer, phone identities, social login, profile import и admin override выполняются отдельными пакетами.

## 12. Закрытие

После всех external checks обновить AUTH002_VERIFICATION_STATUS, PLAN_CURRENT, PROJECT_PASSPORT, SOURCE_AUDIT и CHANGELOG. Только затем AUTH-002 получает статус ВЫПОЛНЕНО и PROF-001 становится следующим пакетом.

## 13. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 11.08.2026 | Создан deploy/HH/SJ/ownership/security/rollback runbook AUTH-002. |
