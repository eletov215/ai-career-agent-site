# AI Career Agent — реализация PROF-001

| Поле | Значение |
|---|---|
| Документ | PROF001_IMPLEMENTATION |
| Пакет | PROF-001 |
| Версия | 1.0 |
| Дата | 11 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Основа кода | `ai-career-agent-site-main (14).zip` из актуального GitHub `main`/Render |
| Candidate revision | `20260811_0010` |

## 1. Контрольный статус

PROF-001 реализован как candidate. Пакет создаёт структурированный карьерный профиль, принадлежащий first-party `User`, и неизменяемую историю подтверждённых пользователем версий. Статус ВЫПОЛНЕНО запрещён до green Pull Request CI, Render migration/readiness и production owner/versioning E2E.

## 2. Цель и границы

Цель — дать search, будущему AI и документам единый подтверждённый набор фактов, который не смешивается с OAuth provider snapshots или неподтверждённым PDF extraction.

В пакет входят:

- позиционирование: headline и summary;
- контакты: contact email, phone, Telegram, portfolio/profile URLs;
- карьерные цели: target roles, industries, employment types, work formats;
- geography и relocation;
- salary range/currency/period/tax mode;
- skills и languages с controlled level codes;
- employment, achievements и education;
- incomplete profile support и deterministic completion indicator;
- current profile + immutable material-change versions;
- owner-only view/edit/history/version UI;
- optimistic concurrency, migration, backup inventory, tests и CI gate.

Не входят resume import/review, AI enrichment, public profile, historical restore, drafts/autosave, export/delete/retention и обязательность заполнения.

## 3. Data model и инварианты

```text
User 1 --- 0..1 CareerProfile
CareerProfile 1 --- 1..N CareerProfileVersion
```

`career_profiles` хранит текущий validated snapshot и содержит unique `user_id`. `career_profile_versions` хранит immutable full snapshot и unique `(profile_id, version)`.

Инварианты:

- профиль доступен только по текущему first-party `user_id`;
- один User имеет не более одного current profile;
- material save увеличивает version ровно на один;
- unchanged save не создаёт новую version;
- stale `expected_version` не перезаписывает более новую запись;
- version snapshot после создания не редактируется;
- неполные данные допустимы;
- сохранение формы — явная confirmation boundary;
- provider/PDF/AI facts не копируются автоматически.

## 4. Structured sections

Current snapshot канонизируется как JSON с `schema_version=1`:

```text
headline
summary
contacts
  contact_email, phone, telegram, portfolio_url, linkedin_url
goals
  target_roles[], industries[], employment_types[], work_formats[]
geography
  current_location, preferred_locations[], relocation
salary
  minimum, maximum, currency, period, tax_mode
skills[]
employment[]
achievements[]
education[]
languages[]
```

Current table сохраняет sections отдельными canonical JSON columns для bounded evolution. Version table содержит full `snapshot_json`, `content_hash` и `changed_sections_json`.

## 5. Validation и canonicalization

Service boundary выполняет:

- trim/control-character cleanup и length limits;
- bounded list/row counts;
- case-insensitive duplicate detection skills/languages/string lists;
- controlled enum validation;
- contact email normalization;
- phone/Telegram format validation;
- only `http`/`https` URLs без embedded credentials;
- salary integer/range/currency semantics;
- `YYYY-MM` employment dates и ordering;
- education/achievement year bounds;
- deterministic canonical JSON + SHA-256 content hash.

Ошибки возвращаются как безопасный field-neutral `400`; stale editor — `409`.

## 6. Versioning и concurrency

Editor отправляет hidden `expected_version`. Repository:

1. owner-scoped читает current row;
2. на PostgreSQL использует `SELECT ... FOR UPDATE`;
3. сравнивает stored и expected version;
4. сравнивает content hash;
5. при material change обновляет current row и вставляет immutable version в одной transaction;
6. unique constraints закрывают concurrent create/version races;
7. `IntegrityError` преобразуется в safe profile conflict.

История — read-only. Restore не входит в PROF-001.

## 7. Влияние на код и сайт

Добавлены:

- `domain/profile.py`;
- `models/profile.py`;
- `repositories/profiles.py`;
- `services/profile.py`;
- `routes/profile.py`;
- `templates/profile/*`;
- migration `20260811_0010_structured_career_profile.py`;
- profile migration/service/route tests и dedicated CI step.

Изменены `User` relationship, model/repository/storage exports, `app.py`, dashboard/navigation, `static/styles.css`, backup inventory, PostgreSQL integration and documentation.

Пользователь получает:

- `/profile` — current profile;
- `/profile/edit` — owner form;
- `/profile/history` — version list;
- `/profile/history/<version>` — read-only snapshot;
- dashboard completion card и navigation link.

## 8. Migration

Alembic `20260811_0010` создаёт:

```text
career_profiles
career_profile_versions
```

Migration additive: AUTH/OAuth/Search/Sync rows не меняются. Foreign keys use `ON DELETE CASCADE`; current profile unique per User; version unique per profile/version; completion/schema/version checks and lookup indexes are included.

Downgrade removes only both profile tables. Therefore it is data-destructive for real profile facts and must not run after production acceptance without verified backup and explicit data decision.

## 9. Проверки и доказательства

Подтверждено локально:

```text
full available pytest                       240 passed, 9 skipped
extended focused PROF-001 checks            26 passed, 3 skipped
profile migration/service core              4 passed
SQLite migration 0010 -> 0009 -> 0010      passed
Alembic check                               passed
compileall                                  passed
Jinja parse                                 21 templates passed
architecture/document/infra/hygiene checks  passed
```

Flask package is unavailable in the isolated local environment, so new route tests are prepared but execute in GitHub Actions. PostgreSQL ownership/persistence assertions are added to `test_postgresql_integration.py` and require `POSTGRES_TEST_URL` in CI.

External providers are not invoked by PROF-001.

## 10. Security and privacy

- first-party session is mandatory;
- repository reads/writes/history always include owner `user_id`;
- POST uses CSRF and rate limiting;
- responses are `no-store`;
- templates escape facts; user URLs are prevalidated and opened with safe `rel`;
- logs contain only change/version/completion metadata, not profile content or User ID;
- profile tables are included in encrypted backup inventory;
- completion is informational, not AI confidence or employability score.

PRIV-001 remains responsible for export/delete/retention. PROF-001 does not claim those controls.

## 11. Ограничения и риски

- Structured sections are canonical JSON rather than many child tables; future query-specific normalization must be additive and evidence-driven.
- History is immutable/read-only; restore is excluded.
- No autosave: explicit save is the confirmation boundary.
- No source/provenance per field beyond “manual owner save”; PROF-002 will add import review context.
- Concurrent editing is fail-closed rather than auto-merge.
- Multi-replica deployment still requires shared rate-limit storage.

## 12. Rollback

1. Stop profile editing if a production regression appears.
2. Revert application commit; keep additive revision `0010` so stored facts remain intact.
3. Do not downgrade after real profile data unless a verified backup and explicit data-loss decision exist.
4. Controlled downgrade `0010 -> 0009` removes only profile current/version tables.
5. Do not modify first-party users, auth sessions, OAuth connections, search or sync state.

## 13. Следующее действие

```text
branch / Pull Request
-> dedicated + full GitHub CI green
-> merge main
-> Render upgrade to 20260811_0010
-> owner/version/concurrency/restart E2E
-> regression smoke
-> PROF-001 COMPLETE
-> PROF-002 START
```

## 14. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 11.08.2026 | PROF-001 candidate реализован; external verification pending. |
