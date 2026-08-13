# AI Career Agent — backup and restore

**Production schema:** `20260811_0010`  
**Candidate schema:** `20260812_0011`

Encrypted backup/verified restore tooling remains OPS-001. Existing profile tables remain in the secret-free table inventory:

```text
career_profiles
career_profile_versions
```

Revision `0011` extends version rows with `source_kind` and bounded aggregate `provenance_json`; normal table backup preserves both automatically. Manifest records only row counts, revision, size and SHA-256. It must not contain profile facts, resume filename/text/excerpts, contacts, credentials or `DATABASE_URL`.

## Candidate verification

CI backup/restore must preserve:

- current/profile-version row counts;
- source kind values;
- provenance JSON content;
- current Alembic revision `0011`.

Upload bytes and unconfirmed proposals are intentionally absent from DB and therefore from backup.

## Rollback note

Application rollback keeps `0011`. Downgrade removes source/provenance audit metadata but retains canonical profile snapshots. Production restore drill remains OPS-002/REL-001.

## PROF-003 inventory

Encrypted backup inventory includes `resume_drafts`, `resume_versions`, `resume_assets`, `resume_exports`. A restore drill for PROF-003 must verify current state, version history, asset bytes and export metadata counts; PDF binaries are not expected because they are not stored.
