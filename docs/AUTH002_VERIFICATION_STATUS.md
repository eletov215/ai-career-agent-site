# AI Career Agent — статус проверки AUTH-002

| Поле | Значение |
|---|---|
| Документ | AUTH002_VERIFICATION_STATUS |
| Пакет | AUTH-002 |
| Версия | 1.0 |
| Дата | 11 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Candidate revision | `20260811_0009` |

## 1. Контрольный статус

Код, migration, UI и local tests подготовлены. Статус ВЫПОЛНЕНО запрещён до green GitHub CI, Render `0009` и реального E2E HeadHunter/SuperJob.

## 2. Локальные доказательства

```text
full available pytest                           236 passed, 8 skipped
AUTH-002 migration/service focused tests        7 passed
compileall                                      passed
Jinja template parsing                          passed
repository/document/manifest checks             required after final packaging
```

Skipped route/PostgreSQL scenarios не объявляются пройденными локально.

## 3. Positive verification matrix

| Проверка | Local | GitHub | Render/real provider |
|---|---:|---:|---:|
| migration `0008 -> 0009` | passed | pending | pending |
| one provider slot per User | passed | pending | pending |
| one external identity owner | passed | pending | pending |
| claim unbound row after OAuth proof | passed | pending | pending |
| same-owner reconnect refresh | passed | pending | pending |
| owner-scoped dashboard | route test pending CI | pending | pending |
| owner-scoped disconnect | passed/service; route pending CI | pending | pending |
| encrypted token persistence | unit/route assertions | pending | pending |
| HH real callback | mocked | mocked | pending |
| SuperJob real callback | mocked | mocked | pending |

## 4. Negative verification matrix

- unauthenticated connect returns first-party login;
- lost first-party session during callback does not leak `code`/`state` through `next`;
- mismatched user/session-bound state is rejected;
- external identity owned by another User returns safe conflict and is not overwritten;
- second identity of same provider for one User is rejected;
- foreign disconnect cannot delete another User connection;
- POST without CSRF is rejected;
- provider/token payloads are absent from public copy and structured logs;
- email equality never auto-links legacy rows.

## 5. External gate

1. GitHub Actions fully green, including `Verify AUTH-002 first-party OAuth identity ownership controls`.
2. Render `/health/ready`: `current_revision=expected_revision=20260811_0009`, PostgreSQL persistent, migrations ok.
3. First-party verified User connects HH; dashboard persists ownership after restart/relogin.
4. Reconnect updates same row, does not create duplicate.
5. Disconnect removes local credentials and dashboard status.
6. Repeat for SuperJob.
7. Second AI Career Agent User cannot claim the same external provider identity.
8. Logs contain no access token, refresh token, authorization code, profile payload or provider secret.

## 6. Ограничения

CI mocks external APIs. Provider availability, account permissions and OAuth application settings remain external dependencies. Remote token revoke is excluded from candidate; disconnect proves local credential deletion.

## 7. Rollback

Application revert is sufficient. Revision `0009` may remain. Downgrade removes only the unique owner/provider constraint and must not delete connection rows.

## 8. Решение о статусе

```text
Current: AUTH-002 — НУЖНА ПРОВЕРКА
Complete only after: CI green + Render 0009 + real HH/SJ E2E
```

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 11.08.2026 | Зафиксированы local evidence, positive/negative matrix и обязательный external gate AUTH-002. |
