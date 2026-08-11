# AI Career Agent — security reference AUTH-002

| Поле | Значение |
|---|---|
| Документ | AUTH002_SECURITY_REFERENCE |
| Пакет | AUTH-002 |
| Версия | 1.0 |
| Дата | 11 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |

## 1. Security boundary

First-party `User` + revocable `AuthSession` — единственная browser authentication boundary. HH/SuperJob являются external identities/credentials, а не самостоятельным способом открыть dashboard.

## 2. Ownership constraints

| Constraint | Назначение |
|---|---|
| unique `(provider, external_user_id)` | одна external identity не может принадлежать двум Users |
| unique `(user_id, provider)` | у User не более одной identity provider |
| nullable `user_id` for legacy rows | безопасная совместимость без автоматического owner assignment |

Unbound row может быть claimed только после свежего OAuth callback, который доказал control того же external ID. Email/profile similarity не используется.

## 3. OAuth state contract

State содержит cryptographically random value и session metadata:

```text
state
issued_at
user_id
auth_session_id
```

Проверка одноразовая и constant-time для сравниваемых strings. State истекает по TTL, удаляется при disconnect/lost auth и отклоняется при смене User/AuthSession.

## 4. Callback safety

OAuth code/state являются bearer-like secrets и не копируются в `next`, logs или public error copy. Callback без действующей first-party session возвращает safe 401 и требует restart. Provider errors обрабатываются только после state/owner validation.

## 5. Credential storage

Access/refresh tokens шифруются Fernet до persistence. Encryption key хранится только в environment. Public dashboard показывает provider status/metadata, но не token, expiry internals или raw profile JSON.

Refresh получает connection owner-scoped и записывает новые encrypted credentials в ту же row. Foreign rows не доступны через service/repository API application flow.

## 6. Disconnect contract

Disconnect требует POST + CSRF + active first-party session. Delete predicate включает `user_id` и provider. Unified row и rollback mirror удаляются transactionally; foreign row не изменяется.

Remote provider revoke не унифицирован: SuperJob документирует token deletion, но общий подтверждённый контракт обоих providers отсутствует. Candidate поэтому гарантирует local credential erasure и явно не заявляет remote revoke.

## 7. Threats and controls

| Threat | Control |
|---|---|
| login CSRF / account linking attack | first-party login + state bound to User/AuthSession |
| callback replay | one-time state + provider code semantics |
| cross-user claim | unique external identity + ownership check + row lock |
| provider slot replacement | unique User/provider + explicit disconnect requirement |
| email-based misbinding | no email auto-link |
| session fixation | AUTH-001 session rotation; provider callback preserves only current first-party bearer |
| foreign disconnect | owner-scoped DELETE predicate |
| token leakage | Fernet encryption; secret-free logs/public responses |
| race condition | transaction, row locks, database unique constraints |

## 8. Logging and privacy

Allowed telemetry:

```text
provider
created/claimed/refreshed outcome
safe conflict code
connection existed boolean
```

Forbidden:

```text
authorization code
raw OAuth state
access/refresh token
provider client secret
external user id
email/profile JSON
owner user id in public logs
```

## 9. Residual risks

- Provider-side revocation is not guaranteed by local disconnect.
- In-memory rate-limit backend remains single-instance staging limitation.
- Provider OAuth app configuration/callback ownership is an operational dependency.
- Admin transfer/merge is absent; recovery from wrongly linked identity requires controlled DB/incident procedure.
- Legacy mirror tables temporarily duplicate encrypted credentials for rollback and should be removed only by a future cleanup migration after AUTH-002 production acceptance.

## 10. Rollback and incident response

Application rollback must not restore legacy provider browser login. Keep `0009` unless a controlled downgrade is required. For suspected compromise: revoke first-party sessions, locally disconnect provider, rotate provider credentials/client secret as applicable, inspect secret-free events, preserve DB backup and follow SEC/OPS incident procedure.

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 11.08.2026 | Зафиксированы AUTH-002 ownership/state/encryption/disconnect/logging/rollback security contracts. |
