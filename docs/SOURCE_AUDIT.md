# AI Career Agent — аудит источников v1.4.20

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.20 |
| Дата | 11 августа 2026 |
| Проверяемый пакет | PROF-001 structured owner-scoped career profile candidate |
| Рабочий источник кода | `ai-career-agent-site-main (14).zip` из актуального GitHub `main`, развернутого на Render |
| Канонический план до обновления | PLAN_CURRENT 1.4.19 |
| Канонический паспорт до обновления | PROJECT_PASSPORT 2.33 |
| Результат | PROF-001 candidate реализован; migration `20260811_0010`; local focused evidence green; GitHub/Render/production E2E pending |

## 1. Контрольный статус

AUTH-001 и AUTH-002 остаются ВЫПОЛНЕНО. PROF-001 переводится из ГОТОВО К СТАРТУ в НУЖНА ПРОВЕРКА. Статус ВЫПОЛНЕНО запрещён до green Pull Request CI, Render migration/readiness и owner/versioning production E2E. DOC-STD-001 v1.1 обязателен.

## 2. Проверка актуального источника кода

| Область | Результат |
|---|---|
| WSGI | `app.py`, `app:app` сохранены; `app_fixed.py` отсутствует |
| Database baseline | production `20260811_0009`; candidate head `20260811_0010` |
| Identity root | existing first-party `users`; profile ownership — strict `user_id` FK + unique one-per-User |
| Current state | `career_profiles` stores validated current structured snapshot |
| Version history | `career_profile_versions` stores immutable full snapshot per material save |
| Confirmation boundary | only explicit owner POST save persists facts; provider/PDF/AI data is not auto-copied |
| Incomplete data | permitted; completion is informational, not a save gate |
| Concurrency | optimistic `expected_version`, PostgreSQL row lock, unique constraints and safe conflict |
| HTTP security | first-party login, owner-scoped queries, POST + CSRF, rate limit, no-store |
| UI | `/profile`, `/profile/edit`, `/profile/history`, read-only version view, dashboard/nav integration |
| Backups | inventory includes current and version tables |
| Prohibited artifacts | `.env`, secrets, DB/dump/backup/venv/cache/bytecode excluded |

## 3. Подтверждённый candidate scope

- positioning/headline and summary;
- contacts with bounded email/phone/Telegram/http(s) URLs;
- target roles, industries, employment types and work formats;
- current/preferred geography and relocation intent;
- salary range/currency/period/tax mode;
- deduplicated skills and languages with controlled levels;
- employment, achievements and education with bounded dates/years/text;
- deterministic completion percent;
- current profile + immutable material-change versions;
- owner-only view/edit/history/version routes;
- stale-editor and unchanged-save semantics;
- migration `0010`, backup inventory, tests and dedicated CI gate.

PROF-002 import/review, PROF-003 drafts/autosave, version restore, public sharing, export/delete/retention and AI-generated facts are excluded.

## 4. Локальные доказательства

```text
full available pytest: 240 passed, 9 skipped
extended focused PROF-001 checks: 26 passed, 3 skipped
profile migration/service core: 4 passed
SQLite 0010 -> 0009 -> 0010 round-trip: passed
Alembic check: passed
compileall: passed
Jinja parse: 21 templates passed
architecture/template/document/infra/hygiene: passed
Flask route tests: prepared; Flask runtime unavailable in isolated local environment
PostgreSQL integration: prepared; POSTGRES_TEST_URL/Psycopg required in GitHub Actions
```

Skipped scenarios are Flask/Psycopg/PostgreSQL runtime checks unavailable in the isolated local environment; they remain mandatory in GitHub Actions. External provider HTTP remains mocked by existing CI policy; PROF-001 itself performs no provider HTTP.

## 5. Обязательные внешние доказательства

1. Branch/Pull Request workflow green, включая `Verify PROF-001 structured career profile controls` и full regressions.
2. Render `/health/ready`: `current_revision=expected_revision=20260811_0010`, `migrations.ok=true`, persistent PostgreSQL, `status=ok`.
3. Owner creates an incomplete profile, relogs and sees the same facts/version.
4. Material update creates version 2; history/version 1 remains read-only and unchanged.
5. Unchanged save creates no extra version.
6. Second User cannot read/edit/history/version facts of the first User.
7. Stale editor returns safe conflict without overwriting the newer version.
8. Render restart preserves current profile and history.
9. AUTH-001/002, `/dashboard`, `/vacancies`, ordinary search and logs remain healthy.

## 6. Ограничения и риски

- Profile sections are validated canonical JSON within owner/version tables; future normalization may use additive migrations when query requirements become concrete.
- Completion percent is product guidance, not a quality score or AI confidence.
- Historical restore is intentionally absent; versions are read-only evidence in PROF-001.
- Contact/profile facts are personal data; export/delete/retention remains PRIV-001 and must not be claimed here.
- Provider snapshots and resume extraction remain separate until explicit PROF-002 review/consent.
- Shared rate-limit storage remains required before multiple replicas.

## 7. Rollback

Application revert may leave additive revision `0010`; previous code ignores profile tables. Controlled downgrade `0010 -> 0009` drops `career_profile_versions` and `career_profiles`, so it is permitted only before real profile data or after verified backup and explicit data-retention decision. AUTH/OAuth/Search/Sync rows are not modified.

## 8. Следующее действие

```text
PROF-001 CANDIDATE
-> branch / Pull Request
-> GitHub CI green
-> merge main
-> Render 0010 readiness
-> owner/version/concurrency/restart E2E
-> regression smoke
-> PROF-001 COMPLETE
-> PROF-002 START
```

## 9. Новые канонические версии

```text
PLAN_CURRENT 1.4.20
PROJECT_PASSPORT 2.34
SOURCE_AUDIT 1.4.20
PROF001_IMPLEMENTATION 1.0
PROF001_VERIFICATION_STATUS 1.0
PROF001_RUNBOOK 1.0
PROF001_PROFILE_REFERENCE 1.0
DOCUMENT_STANDARD 1.1 (без изменений)
```

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.4.19 | 11.08.2026 | AUTH-002 complete after green CI, Render 0009, full HH/SJ ownership E2E and regression smoke; PROF-001 next. |
| 1.4.20 | 11.08.2026 | PROF-001 candidate: structured owner profile, immutable versions, migration 0010, UI/validation/tests/backup updates; external verification pending. |
