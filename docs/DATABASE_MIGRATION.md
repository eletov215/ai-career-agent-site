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
→ 20260810_0008 first-party auth candidate
```

Production до AUTH-001 deploy остаётся `20260809_0007`; expected candidate = `20260810_0008`.

## 2. Revision 20260810_0008

Добавляет nullable `password_hash`, `password_changed_at`, `last_login_at` в `users`; создаёт `auth_sessions` и `auth_tokens` с FK cascade, unique hash constraints и lookup/expiry indexes.

Миграция не переписывает existing User/OAuth rows, vacancies, snapshots, sync runs/checkpoints или encrypted tokens.

## 3. Upgrade/check

```bash
python scripts/manage_db.py upgrade
python scripts/manage_db.py current
python scripts/manage_db.py check
python -m alembic check
```

Readiness после deploy:

```text
current_revision  = 20260810_0008
expected_revision = 20260810_0008
database.ok       = true
persistent        = true
```

## 4. Compatibility

Legacy users remain valid with null password fields. Old code can ignore additive tables/columns. AUTH-001 app must not auto-bind OAuth rows.

## 5. Controlled downgrade

```bash
python -m alembic downgrade 20260809_0007
```

Downgrade deletes auth tables and password fields. It is allowed only before real accounts exist or after verified backup/explicit data decision.

## 6. Verification

- clean upgrade to `0008`;
- `0008 -> 0007 -> 0008`;
- Alembic check;
- PostgreSQL auth persistence/reconnect;
- backup/restore inventory includes auth tables;
- Render readiness `0008`.
