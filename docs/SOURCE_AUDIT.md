# AI Career Agent — аудит источников v1.4.23

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.23 |
| Дата | 12 августа 2026 |
| Проверяемый пакет | PROF-002 resume import editable review candidate |
| Рабочий источник кода | `ai-career-agent-site-main (16).zip`; ZIP comment `f5e513f0f992b20305fbef36851ef97576013c86`; exact diff match с PROF-001 hotfix full snapshot |
| Канонический план до обновления | PLAN_CURRENT 1.4.22 |
| Канонический паспорт до обновления | PROJECT_PASSPORT 2.36 |
| Production revision | `20260811_0010` |
| Candidate revision | `20260812_0011` |
| Результат | PROF-002 НУЖНА ПРОВЕРКА; local implementation/tests ready; GitHub/Render/production gate pending |

## 1. Контрольный статус

PROF-001 остаётся ВЫПОЛНЕНО. PROF-002 переводится из ГОТОВО К СТАРТУ в НУЖНА ПРОВЕРКА: код, migration, UI, tests и candidate docs готовы, но Pull Request CI, Render `0011` и реальный import/review E2E ещё не выполнены. DOC-STD-001 v1.1 обязателен.

## 2. Аудит рабочей основы

| Проверка | Доказательство | Результат |
|---|---|---|
| Загруженный ZIP | ZIP comment `f5e513f0f992b20305fbef36851ef97576013c86` | ПОДТВЕРЖДЕНО |
| Сравнение с предыдущим full snapshot | `diff -qr` до PROF-002 edits не выявил различий | ПОДТВЕРЖДЕНО |
| Каноническая очередь | PLAN_CURRENT 1.4.22 / PASSPORT 2.36: PROF-002 следующий | ПОДТВЕРЖДЕНО |
| Production baseline | PROF-001 complete; PostgreSQL revision `20260811_0010` | ПОДТВЕРЖДЕНО источниками |

SHA-256 исходного ZIP: `5e411f3dabc024a4adbf6be05d9fa49ce11e5e36407ac2b068aada0dd3109d0d`.

## 3. Подтверждённый candidate scope

- authenticated upload одного bounded text PDF;
- existing PDF signature/page/text/encryption limits;
- request-local bytes/raw text and ephemeral proposal;
- deterministic `deterministic-text-v1` suggestions for core facts, contacts, geography, skills, employment, education, languages and achievements;
- confidence, static warnings, conflicts and bounded evidence excerpts;
- merge that preserves current confirmed scalar values by default and never deletes confirmed lists/rows;
- full editable PROF-001 review form;
- explicit owner confirm as the only persistence boundary;
- owner/version-bound 30-minute signed metadata token without filename/text/facts;
- ordinary PROF-001 validation/content hash/optimistic version/row lock;
- immutable version source + aggregate provenance through migration `20260812_0011`;
- owner-only history source/provenance UI;
- dedicated migration/service/route/parser/PostgreSQL tests and CI gate.

OCR, image-only recognition, DOC/DOCX, LLM/AI parsing, provider resume import, background jobs, persisted review drafts, autosave, auto-confirm and historical restore are excluded.

## 4. Data lifecycle and privacy evidence

```text
request PDF bytes
-> bounded pypdf text extraction
-> in-memory ResumeImportProposal
-> browser editable review
-> explicit confirm
-> canonical profile snapshot + aggregate provenance
```

Before confirm no profile/version write occurs. Review token contains only schema/extractor/counts/section confidence/static warnings/HMAC owner fingerprint/base version/timestamp. Filename, PDF bytes, raw text, contacts, excerpts and proposal payload are forbidden in token, provenance, logs and canonical docs.

Allowed telemetry: page/character/detected-section/conflict counts, changed, resulting version and completion. Full user facts are not logged.

## 5. Migration evidence

Revision `20260812_0011_profile_import_provenance` adds to `career_profile_versions`:

```text
source_kind      VARCHAR(32) NOT NULL DEFAULT 'manual'
provenance_json  TEXT NOT NULL DEFAULT '{}'
CHECK source_kind IN ('manual', 'resume_import')
```

Existing rows remain `manual`. Canonical profile schema stays version 1. Downgrade removes only source/provenance audit columns and constraint; confirmed snapshots/current profile remain.

## 6. Automated evidence

```text
full available pytest:                    246 passed, 10 skipped
focused PROF-002/PROF-001/parser:         15 passed
architecture/template/document subset:    23 passed
compileall:                                passed
Jinja parse:                               22 templates passed
SQLite clean upgrade to 0011:              passed
SQLite 0011 -> 0010 -> 0011:               passed
Alembic check:                             no new upgrade operations
```

Expected local skips are Flask runtime and Psycopg/PostgreSQL integration; GitHub Actions installs these dependencies and provides PostgreSQL 17. No external provider HTTP is needed by PROF-002.

## 7. Required external verification

1. Separate branch and Pull Request.
2. Full CI plus `Verify PROF-002 resume import review controls` green.
3. Render deploy with `current_revision=expected_revision=20260812_0011`, PostgreSQL persistent and status ok.
4. Upload text PDF; editable review appears; profile/history unchanged before confirm.
5. Edit and delete suggestions; confirm; history marks `Импорт резюме` and aggregate provenance only.
6. Existing confirmed scalar conflict is not silently overwritten.
7. Non-PDF, corrupt/image-only/over-limit inputs fail without profile changes.
8. Foreign/expired/tampered token, missing CSRF and stale base version fail safely.
9. Logout/login and restart preserve confirmed facts/history/provenance.
10. Mobile import/review/confirm, secret-free logs and AUTH/OAuth/search regression pass.

## 8. Ограничения и риски

- Deterministic parser is not AI and can mis-suggest non-standard/multi-column resumes.
- Image-only PDF requires future OCR package.
- Browser refresh loses review because unconfirmed draft persistence is intentionally absent.
- Review token TTL is 30 minutes; stale/expired review requires re-upload.
- Salary/work preferences are not invented from weak evidence.
- Shared rate-limit storage remains required before multi-replica production.

## 9. Rollback

Application revert may keep additive `0011`; previous code ignores new audit columns. Controlled downgrade `0011 -> 0010` removes provenance metadata only. Do not auto-import, delete confirmed snapshots, or persist raw resume content during rollback.

## 10. Следующее действие

```text
PROF-002 candidate
-> branch / Pull Request
-> green CI
-> Render 0011
-> production import/review/privacy/owner/stale/restart/mobile E2E
-> PROF-002 COMPLETE
-> PROF-003 next
```

## 11. Новые канонические версии

```text
PLAN_CURRENT 1.4.23
PROJECT_PASSPORT 2.37
SOURCE_AUDIT 1.4.23
PROF002_IMPLEMENTATION 1.0
PROF002_VERIFICATION_STATUS 1.0
PROF002_RUNBOOK 1.0
PROF002_EXTRACTION_REFERENCE 1.0
PROF002_SECURITY_REFERENCE 1.0
DOCUMENT_STANDARD 1.1 (без изменений)
```

## 12. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.22 | 12.08.2026 | PROF-001 complete; PROF-002 next. |
| 1.4.23 | 12.08.2026 | PROF-002 candidate: exact GitHub baseline verified; text-PDF proposal/review/confirmation, migration `0011`, provenance/privacy/token controls and dedicated tests implemented; external verification pending. |
