# AI Career Agent — миграции базы данных

## 1. Текущая цепочка

```text
20260804_0001 initial legacy schema
→ 20260804_0002 domain model
→ 20260807_0003 external sync worker
→ 20260807_0004 incremental sync/checkpoint lifecycle
→ 20260808_0005 canonical vacancy normalization
→ 20260809_0006 reversible cross-source dedup metadata
→ 20260809_0007 stable search snapshots
→ 20260810_0008 first-party auth
→ 20260811_0009 OAuth identity ownership candidate
```

Production до AUTH-002 deploy остаётся `20260810_0008`; expected candidate = `20260811_0009`.

## 2. Revision 20260810_0008

Добавляет nullable `password_hash`, `password_changed_at`, `last_login_at` в `users`; создаёт `auth_sessions` и `auth_tokens` с FK cascade, unique hash constraints и lookup/expiry indexes.

Миграция не переписывает existing User/OAuth rows, vacancies, snapshots, sync runs/checkpoints или encrypted tokens.

## 3. Revision 20260811_0009

AUTH-002 добавляет database-level unique constraint:

```text
uq_oauth_connections_user_provider (user_id, provider)
```

Существующий unique `(provider, external_user_id)` сохраняется. Nullable legacy rows остаются unbound: PostgreSQL допускает несколько `NULL` в unique constraint, а приложение разрешает claim только после свежего OAuth proof. Перед созданием constraint migration fail-closed проверяет duplicate owned `(user_id, provider)` rows и останавливается без автоматического merge.

Revision не добавляет таблиц и не переписывает токены/profile payloads. Она не выполняет email auto-link и не удаляет legacy provider mirror rows.

## 4. Upgrade/check

```bash
python scripts/manage_db.py upgrade
python scripts/manage_db.py current
python scripts/manage_db.py check
python -m alembic check
```

Readiness после candidate deploy:

```text
current_revision  = 20260811_0009
expected_revision = 20260811_0009
database.ok       = true
persistent        = true
```

## 5. Compatibility

- AUTH-001 users/sessions/tokens сохраняются без изменения.
- Legacy OAuth rows с `user_id IS NULL` остаются валидными, но не дают browser authentication.
- Old application code может игнорировать additive ownership constraint.
- Search/snapshot/sync data и provider application credentials не меняются.
- Existing rollback mirror tables временно сохраняются до отдельного cleanup package после production acceptance.

## 6. Controlled downgrade

```bash
python -m alembic downgrade 20260810_0008
```

Downgrade удаляет только `uq_oauth_connections_user_provider`. OAuth rows, encrypted tokens, first-party auth tables and all search/sync data сохраняются. Перед production downgrade всё равно требуется verified backup и application rollback plan.

Downgrade ниже `20260810_0008` удаляет auth tables/password fields и допустим только до реальных accounts либо после verified backup и explicit data decision.

## 7. Verification

- clean upgrade through `0009`;
- `0009 -> 0008 -> 0009` round-trip;
- fail-closed duplicate-owned-row precheck;
- Alembic check with no pending operations;
- PostgreSQL uniqueness for `(provider, external_user_id)` and `(user_id, provider)`;
- nullable legacy row compatibility;
- owner-bound OAuth persistence after reconnect/restart;
- backup/restore inventory preserves `oauth_connections`, `auth_sessions` and `auth_tokens`;
- Render readiness `current=expected=20260811_0009`.
