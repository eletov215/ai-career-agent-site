# AI Career Agent — аудит источников v1.4.25

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.25 |
| Дата | 13 августа 2026 |
| Проверяемый пакет | PROF-003 server resume drafts and versions candidate |
| Рабочий источник кода | Загруженный GitHub ZIP `ai-career-agent-site-main (16).zip` + синхронизация repository docs с canonical PROF-002 COMPLETE |
| Production baseline | `20260812_0011` |
| Candidate revision | `20260812_0012` |
| Результат | PROF-003 НУЖНА ПРОВЕРКА; внешний CI/Render/E2E pending |

## 1. Контрольный статус

PROF-001/002 остаются ВЫПОЛНЕНО. PROF-003 переводится из ГОТОВО К СТАРТУ в НУЖНА ПРОВЕРКА после локальной реализации server drafts/versions/assets/export metadata и migration `0012`. DOC-STD-001 v1.1 обязателен.

## 2. Аудит рабочей основы

| Проверка | Доказательство | Результат |
|---|---|---|
| ZIP integrity | `ZipFile.testzip()` | ПОДТВЕРЖДЕНО |
| ZIP comment | `427b2726edd078993a3c26985e17713cf2e76c9e` | ПОДТВЕРЖДЕНО |
| SHA-256 ZIP | `ddd4d61f0afbf3351c0623506fc9e35aca757e0536716b4015349abc96e40864` | ПОДТВЕРЖДЕНО |
| Functional comparison | совпадает с PROF-002 complete full snapshot | ПОДТВЕРЖДЕНО |
| Repository docs | 11 файлов отставали от canonical v1.4.24; синхронизированы до PROF-003 edits | ИСПРАВЛЕНО |
| Canonical queue | PLAN_CURRENT 1.4.24 / PASSPORT 2.38: PROF-003 next | ПОДТВЕРЖДЕНО |
| Production baseline | PROF-002 complete; PostgreSQL `20260812_0011` | ПОДТВЕРЖДЕНО ИСТОЧНИКАМИ |

## 3. Подтверждённый candidate scope

- owner-scoped multiple `ResumeDraft` rows;
- bounded mutable state, canonical hash, completion and optimistic revision;
- immutable `ResumeVersion` for checkpoint/export/restore;
- owner-only history, read-only version and restore-as-new-version;
- durable owner/draft-scoped `ResumeAsset` photo/logo objects;
- PDF `ResumeExport` metadata tied to immutable version; no server PDF binary;
- one-time legacy localStorage migration; server authoritative afterwards;
- optional seed from current confirmed PROF-001 with profile version metadata;
- migration `20260812_0012`, backup inventory, route/service/repository/migration tests and dedicated CI gate.

AI interview/rewrite, public sharing, collaborative editing, external object storage, stored PDF binary, templates marketplace and PRIV-001 controls are excluded.

## 4. Architecture and data evidence

```text
PROF-001 confirmed facts --one-way seed--> ResumeDraft
ResumeDraft --material autosave--> revision + 1
ResumeDraft --checkpoint/export/restore--> immutable ResumeVersion
ResumeDraft -> ResumeAsset (photo/logo)
ResumeVersion -> ResumeExport metadata
```

No reverse auto-write to PROF-001 exists. Current draft and document versions are generated-document data, not confirmed facts.

## 5. Migration evidence

Revision `20260812_0012_resume_drafts_versions` creates:

```text
resume_drafts
resume_versions
resume_assets
resume_exports
```

Foreign keys use `ON DELETE CASCADE`; unique/index/check constraints cover owner history, version number, asset identity and bounds. Downgrade removes only the four PROF-003 tables and is data-destructive after use.

## 6. Automated evidence

```text
split full available pytest:                 252 passed, 11 skipped
focused PROF-003 migration/service/routes:  15 passed, 1 skipped
Python compileall:                          passed
Jinja parse:                               25 templates passed
JavaScript syntax check:                   passed
SQLite clean upgrade to 0012:              passed
SQLite 0011 -> 0012 -> 0011 -> 0012:       passed
Alembic check:                              passed
architecture/template checks:              passed
repository hygiene:                         passed
infra manifest:                             passed
```

Flask route tests and Psycopg/PostgreSQL integration are delegated to GitHub Actions because those runtime dependencies/services are unavailable in the isolated local environment.

## 7. Required external verification

1. Separate branch and Pull Request.
2. Full CI + `Verify PROF-003 server resume draft and version controls` green.
3. Render current/expected `20260812_0012`, persistent PostgreSQL, status ok.
4. Other-device/browser-cleanup/relogin/restart persistence.
5. Multiple drafts and owner isolation.
6. Autosave no-op and stale `409` without lost update.
7. Checkpoint history, read-only version, restore as new version, no duplicate checkpoint.
8. Durable photo/logo and foreign asset rejection.
9. Preview/PDF parity and export metadata tied to exact version.
10. Delete cascade, mobile, PROF-001/002/AUTH/OAuth/search regressions and secret-free logs.

## 8. Risks

- PostgreSQL BLOB assets increase database/backup size.
- Current builder remains deterministic, not AI.
- No collaborative merge; stale browser must reload.
- Legacy localStorage exists only until one-time migration/removal.
- Server does not retain PDF binary.
- Shared rate-limit storage remains required before multi-replica production.

## 9. Rollback

Application revert may retain additive `0012`. Controlled downgrade `0012 -> 0011` removes all draft/version/asset/export data; requires verified backup and explicit decision. PROF-001 confirmed snapshots, accounts, OAuth, search and sync data remain untouched.

## 10. Следующее действие

```text
PROF-003 CANDIDATE
-> green CI
-> Render 0012
-> production E2E
-> PROF-003 COMPLETE
-> PRIV-001 START
```

## 11. Новые канонические версии

```text
PLAN_CURRENT 1.4.25
PROJECT_PASSPORT 2.39
SOURCE_AUDIT 1.4.25
PROF003_IMPLEMENTATION 1.0
PROF003_VERIFICATION_STATUS 1.0
PROF003_RUNBOOK 1.0
PROF003_RESUME_REFERENCE 1.0
PROF003_SECURITY_REFERENCE 1.0
DOCUMENT_STANDARD 1.1 (без изменений)
```

## 12. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.24 | 12.08.2026 | PROF-002 complete; PROF-003 next. |
| 1.4.25 | 13.08.2026 | GitHub ZIP verified; stale repository docs synchronized; PROF-003 drafts/autosave/versions/assets/export migration `0012` candidate implemented; external gate pending. |
