# AI Career Agent — backup and restore

**Production schema before PRIV-001 deploy:** `20260812_0012`  
**Candidate schema:** `20260813_0013`

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
- current Alembic revision `0013` after candidate deploy.

Upload bytes and unconfirmed proposals are intentionally absent from DB and therefore from backup.

## Rollback note

Application rollback may keep additive `0013`. Controlled `0013 -> 0012` removes only the identifier-free privacy audit table. Account deletion itself is irreversible from the live application; recovery requires a verified backup and an explicit operational/legal decision. Production restore drill remains OPS-002/REL-001.

## PROF-003 inventory

Encrypted backup inventory includes `resume_drafts`, `resume_versions`, `resume_assets`, `resume_exports`. A restore drill for PROF-003 must verify current state, version history, asset bytes and export metadata counts; PDF binaries are not expected because they are not stored.


## PRIV-001 inventory

Encrypted backup inventory includes `privacy_audit_events` in addition to the existing auth/profile/resume/search/sync tables. The table contains only event type, bounded aggregate counts and timestamp; it intentionally cannot reconstruct the deleted account identity.

A privacy export ZIP is generated in memory and is not stored as a server artifact. A successful account deletion removes the owner-scoped database subtree and local legacy provider credential mirrors before the identifier-free deletion audit row is written. Restoring a deleted account therefore requires restoring a verified database backup; it is not an application undo operation.


## AI-001 delta / 1.5.0 / 2026-09-14

Backup inventory includes the seven AI tables introduced by0015. No production/staging restore drill was performed in this task. Do not claim CI recovery equals a real deployment backup. Preserve AI accounting data before controlled downgrade.


## JOB-001 r1.1 REBUILT / candidate0019

Backup inventory now includes saved_vacancies and saved_vacancy_sources, including saved snapshots, notes and alias ownership. They have no deletion dependency on the live vacancy/search cache. A real Neon backup/snapshot was not proved during the earlier AI-004 acceptance; obtain a confirmed recovery point before deployment0019. An account privacy ZIP is not a whole-database backup.

Use an isolated disposable database for backup/restore tests, including non-empty saved rows and notes. Do not restore into the live database during routine verification. A controlled0019->0018 downgrade deletes both saved tables and their notes; it is destructive and must follow preserved/verified data and coordinated compatible application rollback. No downgrade or production restore has been run in this reconstruction.
