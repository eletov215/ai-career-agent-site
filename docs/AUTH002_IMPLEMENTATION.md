# AI Career Agent — реализация AUTH-002

| Поле | Значение |
|---|---|
| Документ | AUTH002_IMPLEMENTATION |
| Пакет | AUTH-002 |
| Версия | 1.0 |
| Дата | 11 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Основа кода | `ai-career-agent-site-main (12).zip` из актуального GitHub `main` |
| Candidate revision | `20260811_0009` |

## 1. Контрольный статус

AUTH-002 реализован как локально проверенный candidate. Пакет связывает HeadHunter и SuperJob с уже подтверждённым first-party `User`, но не объявляется ВЫПОЛНЕНО до green GitHub Actions, Render migration `20260811_0009` и реального OAuth E2E обеих площадок.

## 2. Цель и границы

Цель пакета — сделать внешний OAuth не самостоятельной browser identity, а управляемым подключением конкретного аккаунта AI Career Agent.

В пакет входят:

- явное подключение HeadHunter и SuperJob только из authenticated dashboard;
- один внешний аккаунт площадки не более чем у одного first-party `User`;
- не более одного подключения каждого provider на одного `User`;
- claim существующей legacy/unbound row только после нового успешного OAuth callback;
- owner-scoped чтение, refresh/reconnect и disconnect;
- сохранение токенов в зашифрованном виде;
- migration текущих rows без автоматической привязки по email;
- отдельный GitHub CI gate и позитивные/негативные tests.

Не входят телефон/OTP, Google/Yandex social login, account merge UI, admin override, карьерный профиль, новые provider scopes и удалённая деавторизация у всех providers.

## 3. Identity model и инварианты

`users` остаётся единственным first-party identity root. Browser authentication определяется только валидной `auth_sessions` row AUTH-001. Legacy session keys `hh_user_id` и `superjob_user_id` больше не дают доступ к dashboard и удаляются из browser session.

Ключевые инварианты:

```text
User 1 --- 0..1 OAuthConnection(provider=headhunter)
User 1 --- 0..1 OAuthConnection(provider=superjob)
OAuthConnection(provider, external_user_id) --- unique owner
```

Привязка по совпадению email запрещена. Доказательством владения external identity служит только свежий provider OAuth flow, начатый authenticated пользователем.

## 4. OAuth flow

### 4.1 Начало подключения

`/oauth/hh/login` и `/oauth/superjob/login` требуют first-party login. OAuth state хранит:

```text
random state
issued_at
first-party user_id
auth_session_id
```

State одноразовый, TTL-bound и проверяется вместе с текущей server-side session. Это блокирует login-CSRF, state swap и завершение callback после смены first-party session.

### 4.2 Callback

После обмена authorization code приложение получает provider profile и выполняет атомарный ownership check:

- row отсутствует — создаётся owned connection;
- row существует без owner — claim после свежего OAuth proof;
- row уже принадлежит текущему User — encrypted credentials обновляются;
- row принадлежит другому User — safe `409`, ownership не раскрывается;
- у User уже есть другая identity того же provider — safe `409`, требуется сначала disconnect.

OAuth code/state не переносятся в generic `next` URL. Если first-party session потеряна, callback возвращает query-safe `401` и требует начать подключение заново.

## 5. Persistence и migration

Alembic revision `20260811_0009` добавляет unique constraint:

```text
uq_oauth_connections_user_provider(user_id, provider)
```

Существующий unique `(provider, external_user_id)` сохраняется. Nullable legacy rows допустимы и не получают owner автоматически. Перед созданием constraint migration fail-closed проверяет неоднозначные duplicate owned rows.

Downgrade удаляет только новый unique constraint и не удаляет OAuth rows или токены.

## 6. Token storage, refresh и disconnect

Provider access/refresh tokens продолжают шифроваться Fernet-ключом приложения до записи в `oauth_connections` и rollback mirror tables. Refresh работает только через owner-scoped connection текущего User.

Disconnect:

- доступен только POST + CSRF + first-party login;
- удаляет owner-scoped unified connection;
- очищает provider-specific rollback mirror row;
- не затрагивает connection другого User;
- не удаляет first-party account и его sessions.

Candidate гарантирует локальное удаление credentials. Remote revoke provider-side не является единым контрактом пакета: SuperJob документирует DELETE access token, а стабильный подтверждённый revoke contract HeadHunter не зафиксирован. Поэтому автоматическая remote revoke не выполняется, чтобы disconnect оставался предсказуемым и одинаковым для обоих providers.

## 7. Влияние на код и сайт

Изменены `app.py`, auth session rotation, OAuth repository/model/service, dashboard/navigation, styles, migration, CI и tests. Добавлен `services/oauth_identity.py`.

Dashboard теперь:

- доступен только first-party пользователю;
- показывает только его HH/SuperJob connections;
- предлагает connect/reconnect и owner-only disconnect;
- объясняет, что токены зашифрованы и connection принадлежит текущему аккаунту.

Поиск вакансий и app-level SuperJob credential не зависят от user OAuth и не изменяются.

## 8. Проверки и доказательства

Локально:

```text
python -m pytest -q                         236 passed, 8 skipped
focused AUTH-002 service/migration tests   7 passed
python -m compileall -q .                  passed
Jinja parse all templates                  passed
SQLite 0009 migration round-trip           passed by tests
```

Локальные skips относятся к Flask runtime, Psycopg и PostgreSQL service, которые выполняются в GitHub Actions.

## 9. Ограничения и риски

- Реальные HH/SuperJob authorization code exchanges не выполняются в CI и должны быть подтверждены на Render.
- Existing unbound rows не отображаются пользователю и claim-ятся только после свежего provider OAuth proof.
- Один User пока может иметь только одну identity каждого provider; multi-account provider switching требует disconnect.
- Remote token revoke не унифицирован и исключён из candidate; local encrypted credentials удаляются.
- Provider profile fields остаются snapshot metadata, а не first-party profile facts; PROF-001/002 выполнят отдельную review/consent модель.
- Admin merge/transfer identity отсутствует; ownership conflict fail-closed.

## 10. Rollback

1. Остановить новые connect/disconnect действия и вернуть application commit.
2. Оставить additive revision `0009`: старый код игнорирует новый unique constraint.
3. При необходимости выполнить downgrade `0009 -> 0008`; OAuth rows не удаляются.
4. Не восстанавливать legacy browser identities как authentication mechanism.
5. Не очищать first-party users, auth sessions, search/sync data.

## 11. Следующее действие

```text
AUTH-002 candidate
-> GitHub Actions green
-> Render upgrade to 20260811_0009
-> HH real bind/reconnect/disconnect E2E
-> SuperJob real bind/reconnect/disconnect E2E
-> cross-user ownership conflict negative smoke
-> AUTH-002 COMPLETE
-> PROF-001 START
```

## 12. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 11.08.2026 | Реализован first-party ownership contract HH/SuperJob, migration 0009, state/session binding, owner-scoped refresh/disconnect, UI и tests; требуется внешняя verification. |
