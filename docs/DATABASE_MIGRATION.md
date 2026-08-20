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
-> 20260812_0011 profile import provenance
-> 20260812_0012 server resume drafts/versions/assets/exports
-> 20260813_0013 privacy audit controls candidate
```

Production before PRIV-001 deploy: `20260812_0012`. Candidate expected: `20260813_0013`.

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

## Revision `20260812_0012`

Creates `resume_drafts`, `resume_versions`, `resume_assets`, `resume_exports`. Upgrade is additive. Downgrade to `20260812_0011` drops all four tables and is data-destructive after users create drafts; it requires verified backup and explicit approval.


## Revision `20260813_0013`

Creates `privacy_audit_events` with only:

```text
id UUID/string primary key
event_type data_exported | account_deleted | retention_cleanup
counts_json bounded aggregate counters
created_at epoch seconds
```

There is deliberately no FK to `users` and no user ID/email/content column, so deletion evidence does not retain a direct identifier after the account is removed. Upgrade is additive. Controlled downgrade `0013 -> 0012` removes only this audit table and leaves AUTH/PROF/resume/search/sync data unchanged.

After deploy Render readiness must show `database.revision=current_revision=expected_revision=20260813_0013` and `migrations.ok=true`.

## 20260819_0014_source_health_admin
Adds `source_health_states` and indexes. Additive; downgrade drops only operational provider health state.
