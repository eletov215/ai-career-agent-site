# AI Career Agent — аудит источников v1.4.30

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.30 |
| Дата | 19 августа 2026 |
| Проверяемый пакет | SEARCH-005 admin source status center candidate |
| Исходный код | `ai-career-agent-site-main (18).zip`, GitHub main после PRIV-001 COMPLETE |
| Production revision | `20260813_0013` |
| Candidate revision | `20260819_0014` |
| Результат | SEARCH-005 НУЖНА ПРОВЕРКА |

## 1. Контрольный статус

PRIV-001 подтверждён production E2E и закрыт. Загруженный ZIP принят как актуальная GitHub-основа. SEARCH-005 реализован как candidate; статус ВЫПОЛНЕНО не выставляется до GitHub/Render/E2E.

## 2. Аудит входного ZIP

- ZIP integrity проверена;
- `database.CURRENT_REVISION=20260813_0013` до изменений;
- repository docs отражают PRIV-001 COMPLETE v1.4.29;
- `app.py` и WSGI `app:app` сохранены;
- `infra/vps/.env.example` присутствует;
- `.env`, databases, dumps, backups, caches, bytecode, virtualenv, `app_fixed.py` и секретные credential-файлы отсутствуют;
- функциональные файлы не содержат вложенного лишнего ZIP или runtime output.

## 3. Реализованный scope

- explicit verified first-party admin allowlist `SEARCH_ADMIN_EMAILS`;
- owner-independent persistent `source_health_states` for HH/SuperJob/Reed/Trudvsem;
- last attempt/success/failure, latency, failure streak, configured status, safe error category/code;
- cache count/timestamp aggregation using database metadata;
- Trudvsem persistent SyncRun/worker freshness aggregation;
- non-gating instrumentation of existing provider observability events;
- read-only `/admin/sources` and `/api/admin/sources`;
- neutral 404 ordinary user, login gate unauthenticated user;
- no-store, no ETag, rate limit, mobile UI;
- migration, backup inventory, tests and dedicated CI gate.

## 4. Privacy and security evidence

The model deliberately has no `user_id`. Stored `details_json` accepts only a fixed key allowlist and bounded scalar values. Exception messages, provider bodies, user search queries, tokens and credentials are never persisted. Error recording keeps only safe category and exception class/status code. The admin page performs no upstream request.

## 5. Migration and rollback

`20260819_0014_source_health_admin` creates one additive table and two indexes. Downgrade removes only SEARCH-005 state. Application revert may keep 0014. Removing `SEARCH_ADMIN_EMAILS` disables access immediately.

## 6. Local evidence

- Python compile/AST checks passed;
- full available pytest passed;
- focused migration/model/service/frontend/route-registration tests passed;
- SQLite migration upgrade/downgrade/re-upgrade passed;
- repository hygiene, infra manifest, document structure and archive checks passed;
- provider observability instrumentation test confirms at least one existing provider event hook;
- no environment-dependent PostgreSQL/Render scenario is claimed complete locally.

## 7. Required external gate

1. Separate branch and Pull Request.
2. Full CI plus `Verify SEARCH-005 admin source health controls` green.
3. Configure `SEARCH_ADMIN_EMAILS` for a verified test administrator.
4. Render deploy with current/expected `20260819_0014`.
5. Unauthenticated user -> login; ordinary verified user -> neutral 404.
6. Administrator -> safe HTML and JSON for all four providers.
7. Perform real vacancy search/provider attempt; timestamps/latency/status update without response body/query.
8. Restart Render; latest persisted state remains available; Trudvsem sync/worker freshness remains consistent.
9. Public source state and search behavior unchanged.
10. Render logs contain no tokens, provider bodies, user queries or PII.

## 8. Limitations

- Initial center is read-only; no manual retries or credential management.
- Current provider observability hook is per process; persisted writes survive restart, but future multi-replica deployment needs a shared event/metrics transport.
- Cache probing is metadata-based and intentionally fail-soft.
- No external status-page or provider probe runs on admin page load.
- Admin allowlist is deployment configuration, not a general RBAC system.

## 9. Next action

`SEARCH-005 candidate -> Pull Request CI -> Render 0014 -> production E2E -> SEARCH-005 COMPLETE -> AI-BENCH-001`.

## 10. Version log

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.29 | 19.08.2026 | PRIV-001 complete; SEARCH-005 next. |
| 1.4.30 | 19.08.2026 | SEARCH-005 admin authorization, persistent source health, safe UI/API, migration 0014, tests and docs implemented; external gate pending. |
