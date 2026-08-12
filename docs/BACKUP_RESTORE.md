# AI Career Agent — backup and restore

**Production schema:** `20260811_0009`  
**Candidate schema:** `20260811_0010`

Encrypted backup/verified restore tooling remains OPS-001. PROF-001 extends secret-free table inventory with:

```text
career_profiles
career_profile_versions
```

Manifest records only row counts, revision, size and SHA-256. It must not contain profile facts, contacts, snapshot JSON, credentials or DATABASE_URL.

## Candidate verification

CI backup/restore must preserve current and version row counts on revision `0010`. Production restore drill remains OPS-002/REL-001.

## Rollback note

Application rollback keeps `0010`. Downgrade before backup would destroy profile facts and version history and is not the default rollback path.
