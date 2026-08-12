# AI Career Agent — аудит источников v1.4.21

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.21 |
| Дата | 12 августа 2026 |
| Проверяемый пакет | PROF-001 partial-profile validation hotfix |
| Рабочий источник кода | GitHub `main` после merge PROF-001 candidate; Render/PostgreSQL revision `20260811_0010`; hotfix built from same merged candidate |
| Канонический план до обновления | PLAN_CURRENT 1.4.20 |
| Канонический паспорт до обновления | PROJECT_PASSPORT 2.34 |
| Результат | Initial PROF-001 Pull Request CI green and Render `0010` ready; production E2E found false-required validation for blank repeatable rows; hotfix prepared, no migration; re-verification pending |

## 1. Контрольный статус

AUTH-001 и AUTH-002 остаются ВЫПОЛНЕНО. PROF-001 остаётся НУЖНА ПРОВЕРКА. Initial PR CI и Render migration/readiness `0010` подтверждены, но production E2E выявил дефект partial-save validation. Статус ВЫПОЛНЕНО запрещён до green hotfix CI, redeploy и полного owner/versioning production E2E. DOC-STD-001 v1.1 обязателен.

## 2. Проверка актуального источника кода

| Область | Результат |
|---|---|
| WSGI | `app.py`, `app:app` сохранены; `app_fixed.py` отсутствует |
| Database baseline | production `20260811_0010`; hotfix schema unchanged |
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

## 2.1 Production defect и hotfix v1.4.21

Production partial-profile smoke 12.08.2026 показал сообщение «Для опыта работы укажите компанию и должность» при заполнении только необязательного минимума. Root cause: initial blank repeatable rows формы отправляют default select values (`employment_current=0`, `skill_level=unspecified`, `language_level=unspecified`), а generic row detector считал любое непустое значение признаком введённой записи.

Hotfix:
- default-only row теперь считается пустым и игнорируется;
- если пользователь реально вводит часть записи или меняет default на meaningful value, строгая field validation сохраняется;
- добавлены service regression и route regression, имитирующий фактический browser POST пустых rows;
- migration не меняется, production revision остаётся `20260811_0010`.

Local hotfix evidence: `tests/test_profile_service.py + tests/test_prof001_migration.py = 5 passed`; `compileall` passed. Route regression добавлен, но локальная среда без Flask его skip-ает; authoritative proof — GitHub CI.

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
PLAN_CURRENT 1.4.21
PROJECT_PASSPORT 2.35
SOURCE_AUDIT 1.4.21
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
| 1.4.21 | 12.08.2026 | Initial CI/Render `0010` passed; production partial-save exposed default-only repeatable-row validation defect. Hotfix fixes row detection and adds regression tests; CI/redeploy/E2E pending. |
