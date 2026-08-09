# AI Career Agent — миграции базы данных

## 1. Текущая цепочка

```text
20260804_0001 initial legacy schema
→ 20260804_0002 domain model
→ 20260807_0003 external sync worker
→ 20260807_0004 incremental sync/checkpoint lifecycle
→ 20260808_0005 canonical vacancy normalization
→ 20260809_0006 reversible cross-source dedup metadata
→ 20260809_0007 stable search snapshots (candidate)
```

Production до SEARCH-003 работает на `20260809_0006`; после candidate deploy ожидается `20260809_0007`.

## 2. Revision 20260809_0007

Создаёт четыре additive ephemeral tables:

- `search_snapshots`;
- `search_snapshot_sources`;
- `search_snapshot_candidates`;
- `search_snapshot_items`.

Миграция не переписывает `vacancies`, `vacancy_source_records`, OAuth, sync runs/checkpoints или encrypted tokens. Foreign keys используют cascade только внутри snapshot aggregate.

## 3. Upgrade/check

```bash
python scripts/manage_db.py upgrade
python scripts/manage_db.py current
python scripts/manage_db.py check
python -m alembic check
```

Readiness после deploy:

```text
current_revision  = 20260809_0007
expected_revision = 20260809_0007
database.ok       = true
persistent        = true
```

## 4. Compatibility

- application rollback может оставить additive tables `0007`; старый код их не читает;
- snapshot rows TTL/ephemeral и не являются источником вакансий;
- backup inventory включает новые tables для проверки полноты schema;
- existing cache и dedup metadata `0006` не изменяются.

## 5. Controlled downgrade

```bash
# только после verified backup и deployment совместимого старого кода
python -m alembic downgrade 20260809_0006
```

Downgrade удаляет только четыре snapshot tables/indexes. Он не должен удалять canonical vacancy data.

## 6. Проверки candidate

- clean upgrade до `0007`;
- `0007 → 0006 → 0007`;
- `alembic check`;
- PostgreSQL integration и cascade isolation в GitHub CI;
- `/health/ready` на Render.
