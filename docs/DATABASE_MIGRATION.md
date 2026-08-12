# AI Career Agent — database migration reference

## Revision chain

```text
20260804_0001 legacy PostgreSQL baseline
-> 20260804_0002 domain model
-> 20260807_0003 external sync worker
-> 20260807_0004 incremental checkpoint/lifecycle
-> 20260808_0005 canonical vacancy contract
-> 20260809_0006 dedup metadata
-> 20260809_0007 search snapshots
-> 20260810_0008 first-party auth
-> 20260811_0009 OAuth identity ownership
-> 20260811_0010 structured career profile
-> 20260812_0011 profile import provenance candidate
```

Production before PROF-002 deploy: `20260811_0010`. Candidate expected: `20260812_0011`.

## Revision 0011

Adds to `career_profile_versions`:

```text
source_kind      VARCHAR(32) NOT NULL DEFAULT 'manual'
provenance_json  TEXT NOT NULL DEFAULT '{}'
CHECK source_kind IN ('manual', 'resume_import')
```

Existing rows become `manual` with empty provenance. No profile snapshot/current row/User/AuthSession/OAuth/Search/Sync data is rewritten. Canonical profile schema version stays 1.

## Upgrade verification

```text
python scripts/manage_db.py upgrade
python scripts/manage_db.py current
python -m alembic check
```

Render readiness must show:

```text
database.revision=20260812_0011
migrations.current_revision=20260812_0011
migrations.expected_revision=20260812_0011
migrations.ok=true
```

## Data compatibility

Previous application code ignores the new columns, so application rollback may keep `0011`. New code strictly validates bounded provenance before persistence.

## Downgrade

`0011 -> 0010` drops the source-kind check and both audit columns. Current confirmed profile and immutable snapshot contents remain, but source attribution/import provenance is lost. Downgrade therefore requires an explicit audit-data decision, though it is not destructive to canonical profile facts.

## Tests

- legacy version defaults after upgrade;
- `resume_import` row insert;
- SQLite upgrade/downgrade/re-upgrade;
- PostgreSQL integration and backup/restore in CI;
- Alembic no-drift check.
