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
-> 20260811_0010 structured career profile candidate
```

Production before PROF-001 deploy: `20260811_0009`. Candidate expected: `20260811_0010`.

## Revision 0010

Creates:

```text
career_profiles
career_profile_versions
```

No backfill and no provider/resume auto-import. Existing User/Auth/OAuth/Search/Sync rows are unchanged.

## Upgrade verification

```text
python scripts/manage_db.py upgrade
python scripts/manage_db.py current
python -m alembic check
```

Render readiness must show:

```text
current_revision  = 20260811_0010
expected_revision = 20260811_0010
migrations.ok     = true
```

## Downgrade

`0010 -> 0009` drops both profile tables. It is safe only before real profile use or after verified backup and explicit data-loss/retention decision. Application rollback should normally keep `0010`.
