# AI Career Agent — аудит источников v1.4.18

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.18 |
| Дата | 11 августа 2026 |
| Проверяемый пакет | AUTH-002 first-party OAuth identity ownership candidate |
| Рабочий источник кода | `ai-career-agent-site-main (12).zip` из актуального GitHub `main`, развернутый на Render |
| Канонический план до обновления | PLAN_CURRENT 1.4.17 |
| Канонический паспорт до обновления | PROJECT_PASSPORT 2.31 |
| Результат | AUTH-002 candidate реализован; local tests green; migration `20260811_0009`; GitHub/Render/real provider E2E pending |

## 1. Контрольный статус

AUTH-001 остаётся ВЫПОЛНЕНО. AUTH-002 получает статус НУЖНА ПРОВЕРКА. GitHub ZIP является фактической кодовой основой, а canonical v1.4.17 — основой статусов. Candidate не расширяет scope телефоном/social login и не объявляется complete до external evidence. DOC-STD-001 v1.1 обязателен.

## 2. Проверка актуального источника кода

| Область | Результат |
|---|---|
| WSGI | `app.py`, `app:app` сохранены; `app_fixed.py` отсутствует |
| Database | production baseline `20260810_0008`; candidate `20260811_0009` |
| Identity root | existing first-party `users`; parallel user table не создаётся |
| OAuth ownership | unique external identity + one provider slot per User |
| Legacy rows | nullable/unbound сохраняются; auto-link по email запрещён |
| OAuth state | one-time/TTL; bound to `user_id` and server-side `auth_session_id` |
| Tokens | Fernet-encrypted persistence; plaintext absent from DB/logs |
| Dashboard | first-party login required; owner-scoped HH/SJ status/actions |
| Disconnect | POST + CSRF; owner-scoped local credential deletion + legacy mirror cleanup |
| Browser compatibility | legacy `hh_user_id`/`superjob_user_id` keys не авторизуют |
| External APIs | mocked in CI candidate; real HH/SJ verification pending |
| Prohibited artifacts | `.env`, secrets, DB/dump/backup/venv/cache/bytecode excluded |

## 3. Реализованный scope AUTH-002

- authenticated HeadHunter/SuperJob connect flows;
- state bound to first-party user and auth session;
- atomic create/claim/refresh ownership service;
- cross-user and same-provider-slot conflicts;
- migration `0009` with fail-closed duplicate precheck;
- owner-scoped read/refresh/reconnect/disconnect;
- legacy provider browser identity removal;
- dashboard/navigation/CSS updates;
- dedicated migration/service/route/PostgreSQL tests and CI step.

Phone/OTP, Google/Yandex social identities, admin merge/transfer, profile import and remote revoke contract are excluded.

## 4. Локальные доказательства

```text
full available pytest: 236 passed, 8 skipped
focused AUTH-002 migration/service tests: 7 passed
compileall: passed
Jinja parsing: passed
migration round-trip: covered by focused tests
```

Flask route runtime, Psycopg and PostgreSQL service scenarios execute in GitHub Actions and are not claimed locally.

## 5. Ожидаемые внешние доказательства

1. Green `Verify AUTH-002 first-party OAuth identity ownership controls` and full workflow.
2. Render `/health/ready`: current/expected `20260811_0009`, migrations ok, persistent PostgreSQL.
3. Real HH bind/reconnect/disconnect persists across first-party relogin/restart.
4. Real SuperJob bind/reconnect/disconnect persists across first-party relogin/restart.
5. Second first-party User cannot claim an already-owned external identity.
6. Different provider identity for occupied User/provider slot is rejected.
7. Logs/public responses contain no OAuth code/state/token/provider secret/profile body.

## 6. Ограничения и риски

- External OAuth availability and application callback configuration remain external dependencies.
- Existing unbound rows are not migrated to owners automatically.
- Remote provider token revoke is not unified; candidate guarantees local encrypted credential deletion.
- Legacy encrypted mirror tables remain temporarily for rollback.
- Provider profile snapshots are not first-party career profile facts.

## 7. Rollback

Application revert without touching first-party/search/sync data. Revision `0009` is additive and may remain. Controlled downgrade removes only the new unique `(user_id, provider)` constraint; OAuth rows remain. Never restore legacy provider IDs as browser authentication.

## 8. Следующее действие

```text
AUTH-002 candidate
-> GitHub green
-> Render 0009
-> real HH E2E
-> real SuperJob E2E
-> ownership negative smoke
-> AUTH-002 COMPLETE
-> PROF-001 START
```

## 9. Новые канонические версии

```text
PLAN_CURRENT 1.4.18
PROJECT_PASSPORT 2.32
SOURCE_AUDIT 1.4.18
AUTH002_IMPLEMENTATION 1.0
AUTH002_VERIFICATION_STATUS 1.0
AUTH002_RUNBOOK 1.0
AUTH002_SECURITY_REFERENCE 1.0
DOCUMENT_STANDARD 1.1 (без изменений)
```

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.17 | 11.08.2026 | AUTH-001 final; AUTH-002 ready. |
| 1.4.18 | 11.08.2026 | AUTH-002 candidate: owner-bound HH/SJ identities, migration 0009, state/session binding, owner-scoped disconnect and dedicated tests; external verification pending. |
