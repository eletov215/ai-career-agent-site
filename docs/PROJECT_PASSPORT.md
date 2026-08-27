# AI Career Agent — паспорт проекта




<!-- ACA-CANONICAL-STATUS:START -->
## Канонический срез проекта

**Документ:** AI Career Agent PROJECT_PASSPORT `v2.56`  
**Дата:** 2026-08-27  
**Production revision:** `20260819_0014`

| Контур | Состояние |
|---|---|
| Web | Flask + Gunicorn, WSGI `app:app`; Alice Final v2 package production code не меняет |
| Data | PostgreSQL production, SQLite local/test fallback, Alembic `20260819_0014` |
| Identity/career/search/privacy | ранее завершённые пакеты остаются ВЫПОЛНЕНО; regression matrix локально без confirmed failures |
| AI benchmark | `evals 1.5.0`, benchmark `1.4`, dataset `1.3.2`, `grounded-v2.3`; Alice Final run #1 reviewed; fresh Alice-only verification pending |
| Alice Final run #1 | artifact `33061758538`: 8/8 calls, 0 errors/retries, source 6/8; failures isolated to interview scenario provenance plus one response-count numeric false positive |
| Regression replay | same raw responses under grounded-v2.3: 8/8 PASS, 6 audited unique scenario repairs, 0 unresolved provenance, 0 unsupported numbers |
| Candidate | Alice AI LLM remains primary candidate; no production provider is connected |
| Safety boundary | synthetic dataset; exact evidence; deterministic match; impact/language/metadata gates; unique one-to-one scenario repair only; ambiguous/unsupported facts remain hard failures |
| Final verification | manual-only `run_ai_bench_alice_final`; benchmark 1.4/dataset 1.3.2; 8/8 machine gate before named human rubric |
| Production AI | отсутствует; final provider decision ещё не принят |

### Decision boundary

The comparative provider ranking is complete enough to keep Alice AI LLM as the final candidate. Alice Final run #1 did not reveal a transport or new semantic-safety regression; it exposed structured scenario provenance omissions and an overly broad response-count numeric classifier. Grounded-v2.3 addresses only those deterministic layers and still requires a fresh Alice-only 8/8 live artifact plus a named human writing-quality rubric. Only then may `AI-PROVIDER-001` record the production-provider decision.
<!-- ACA-CANONICAL-STATUS:END -->

| Поле | Значение |
|---|---|
| Документ        | PROJECT_PASSPORT                                                                              |
| Версия паспорта | 2.56 |
| Дата            | 27 августа 2026                                                                               |
| Статус          | ДЕЙСТВУЮЩИЙ                                                                                   |
| Связанный план | `AI_Career_Agent_PLAN_CURRENT v1.4.42` |
| Основа кода | GitHub `main` archive `ai-career-agent-site-main (26).zip` after Alice Final run #1 |

> Контрольные статусы: FND/DATA/SEC/OPS/INFRA-PREP/SYNC/SEARCH-001..005/AUTH/PROF/PRIV - ВЫПОЛНЕНО; AI-BENCH-001 - НУЖНА ПРОВЕРКА; AI-PROVIDER-001 - ЗАБЛОКИРОВАНО; DOC-001 - В РАБОТЕ; INFRA-001 - ОТЛОЖЕНО.

## 1. Назначение

AI Career Agent — коммерческий веб-сервис карьерного сопровождения:

>     аккаунт -> резюме -> подтверждённый профиль -> AI-анализ
>     -> реальные вакансии -> объяснимый match -> письмо -> tracker

Пользователь принимает окончательные решения самостоятельно.

## 2. Источник истины

1.  GitHub — главный источник актуального кода.
2.  Более новый ZIP в текущем чате — рабочая основа задачи.
3.  Канонический PLAN_CURRENT определяется наибольшей версией и датой.
4.  Старые план/паспорт удаляются после замены.
5.  Главный файл — `app.py`; WSGI — `app:app`; `app_fixed.py` не
    используется.

## 3. Технологии и структура

- Python 3.11, Flask 3.1.3, Gunicorn;
- SQLAlchemy 2, Alembic, PostgreSQL 17/Psycopg 3;
- SQLite local/test fallback;
- Flask-WTF, Flask-Limiter, Cryptography/Fernet/AES-GCM;
- GitHub Actions;
- Docker multi-target images, Docker Compose, Caddy test TLS и VPS probe
  tooling;
- Render временно как staging/резервная площадка;
- production VPS арендуется и тестируется только в предрелизном
  `INFRA-001`;
- основной AI-кандидат — Yandex AI Studio/Alice AI после `AI-BENCH-001`.

>     app.py                     Flask routes, app:app
>     config.py                  production/development/test/ops settings
>     database.py                SQLAlchemy runtime and DB health
>     security.py                CSRF/rate limits/headers/request limits
>     observability.py           structured logs/request IDs/metrics/alerts
>     operations/backup.py       encrypted backup/verified restore
>     Dockerfile / compose.yaml  runtime, ops, DB, migrations, restore-test
>     infra/                     Gunicorn, Caddy, VPS environment and probes
>     scripts/                   migrations, backup, restore, alert, infra probes, sync CLI/worker/supervisor
>     domain/ models/ repositories/ services/
>     services/source_status.py    safe public source-state contract
>     migrations/                Alembic 0001..0014; production currently 0014
>     tests/                     unit/integration/security/ops/infra/sync/search/auth/AI benchmark tests
>     docs/                      architecture, security and runbooks
>     render.yaml
>     .github/workflows/ci.yml

## 4. Подтверждённые базовые пакеты

### FND-001 — ВЫПОЛНЕНО

Базовые tests/CI и Render smoke подтверждены.

### FND-002 — ВЫПОЛНЕНО

Central config/APP_ENV, CI и Render подтверждены;
`HH_CURRENCY_SCAN_PAGES=20`.

### DATA-001 — ВЫПОЛНЕНО

PostgreSQL 17, `DATABASE_URL`, Alembic `20260804_0001`, restart
persistence подтверждены.

### DATA-002 — ВЫПОЛНЕНО

User/OAuthConnection/canonical Vacancy/VacancySourceRecord/SyncRun,
repositories, StorageServices и migration `20260804_0002` подтверждены в
CI и Render; cache/persisted run пережили restart.

### SEC-001 — ВЫПОЛНЕНО

Production подтвердил secure `aca_session`, CSRF `400`, CSP/HSTS/browser
headers, закрытые diagnostics, безопасный Trudvsem status, secret-free
logs и стабильный rate-limit bucket: первые 20 запросов к diagnostic
route дали `404`, 21-й — `429` с `Retry-After`.

## 5. OPS-001 — ВЫПОЛНЕНО

Подтверждены production JSON logs, `X-Request-ID` correlation,
health/live/readiness, protected `/ops/status`, provider metrics,
sanitised alert webhook, encrypted PostgreSQL backup/restore toolchain и
отдельные GitHub OPS/backup steps.

**Важно:** ранее незакрытый encrypted backup реальной production
PostgreSQL + restore в отдельную test database не объявлен пройденным. В
PLAN_CURRENT 1.4.4 он перенесён целиком в `OPS-002` и повторно
проверяется в `REL-001`. Это release gate, а не текущий blocker
функциональной разработки.

OPS-001 database migration отсутствовала. Production schema после
SYNC-002 подтверждена на revision `20260807_0004`.

## 6. INFRA-PREP-001 — ВЫПОЛНЕНО

Кодовая часть прежнего INFRA-001 выделена в самостоятельный
подготовительный пакет без изменения кода:

- non-root runtime/ops Docker images;
- Compose stack с private PostgreSQL, one-shot migrations, web, optional
  Caddy TLS и isolated restore DB;
- secret-free environment template;
- DNS/TCP/TLS/HTTP probes для app/Yandex AI/Reed и optional providers;
- manifest validation, Docker build и runtime smoke в GitHub Actions;
- VPS runbook и provider shortlist.

Это делает приложение переносимым на VPS без необходимости оплачивать ВМ
во время разработки.

## 7. SYNC-001 — ВЫПОЛНЕНО

Внешний контур Trudvsem sync реализован и подтверждён в production:

- Gunicorn/Flask не создаёт daemon thread и не выполняет provider HTTP;
- web routes читают PostgreSQL cache и идемпотентно ставят durable job в
  `sync_runs`;
- `scripts/trudvsem_sync_worker.py` выполняет jobs отдельным OS process;
- `scripts/sync_trudvsem.py` поддерживает one-shot/queue CLI;
- PostgreSQL advisory lock и SQLite lockfile блокируют параллельный
  sync;
- `sync_workers` хранит heartbeat/liveness;
- migration `20260807_0003` добавляет one-active-run constraint и
  закрывает legacy abandoned runs;
- Render использует `scripts/start_runtime.py`, Docker Compose -
  отдельный `sync-worker` profile;
- provider timeout сохраняет старый cache и переводит run в
  контролируемое terminal state.

**Production verification 07.08.2026:** GitHub Actions полностью
зелёный; `/health/ready` подтвердил PostgreSQL, `persistent=true`,
current/expected revision `20260807_0003`; Render supervisor запустил
внешний worker; после исправления import path worker выполняет реальные
batches (`normalized items=10`, `result_count=10`). Public Trudvsem
status показал активный run (`running=true`, progress 43%,
`cached_total=102`) и корректное завершение (`running=false`,
`queued=false`, `cached_total=102`). После реального restart
`uptime_seconds` сбросился до 89 и затем вырос до 112, а cache остался
`102`.

Отдельно зафиксировано: `cache_age_seconds` после restart не
сбрасывается, потому что отражает возраст сохранённого PostgreSQL cache,
а не uptime web-процесса.

## 8. SYNC-002 — ВЫПОЛНЕНО

Поверх подтверждённого external worker внедрена и принята incremental
freshness/cleanup policy:

- migration `20260807_0004` создаёт `sync_checkpoints` и lifecycle-поля
  source records;
- committed watermark, bounded pending window, cursor/offset/total и
  retry state живут в PostgreSQL, а не в process memory;
- overlap 300 секунд + idempotent upsert защищают границу окна;
- explicit closed/expired lifecycle, TTL closure и retention purge
  реализованы и покрыты tests;
- upstream failure не продвигает watermark/cleanup и не удаляет
  последний cache;
- scheduled worker соблюдает persistent bounded exponential backoff.

**GitHub verification 08.08.2026:** весь workflow зелёный, включая
SYNC-001/SYNC-002 gates, PostgreSQL migrations/integration, encrypted
backup/restore, Docker/Compose, runtime smoke и full tests.

**Render verification 08.08.2026:** `/health/ready` и `/health` вернули
`200`, `database.backend=postgresql`, `persistent=true`,
current/expected revision `20260807_0004`. Diagnostics подтвердили
window `pending=true`, `pending_offset=3`, `pending_total=92287`,
watermark `1785926683`, from `1785926383`, to `1786195111` и 300-second
overlap. На реальных `Read timed out` внешнего Trudvsem API
cursor/watermark/cache сохранялись; worker оставался жив; backoff
увеличивался; после redeploy checkpoint и
`cached_total=102`/`active_total=552` сохранились.

**Принятое ограничение:** из-за длительных timeout
`opendata.trudvsem.ru` на Render не дождались успешного продвижения
`pending_offset > 3` и production cleanup полного окна. Эти success-path
сценарии покрыты automated tests/CI. По решению владельца они не
блокируют SEARCH-001 и повторяются на реальном российском VPS в
`INFRA-001/OPS-002`, где ожидается более стабильный маршрут к Trudvsem.

После verification временные `DEBUG_DIAGNOSTICS`/`DIAGNOSTICS_SECRET`
должны быть удалены из production Environment.

## 9. SEARCH-001 — ВЫПОЛНЕНО

Реализован единый vacancy contract без cross-source dedup:

- immutable `NormalizedVacancy` и `CONTRACT_VERSION`;
- canonical `work_format`, `employment_code`, `experience_code`,
  `source_status`;
- common text/salary/currency/date/status normalizer;
- единая contract boundary для HH, Reed, SuperJob и Trudvsem;
- persistence revalidation в `VacancyStore`;
- migration `20260808_0005` для canonical columns/indexes в
  canonical/source tables;
- canonical repository filters с legacy fallback только для rows, где canonical columns ещё `NULL`;
- presenter использует canonical labels, raw provider labels
  сохраняются;
- отдельный GitHub gate и migration/contract/compatibility tests.

Canonical work format:

>     unknown | onsite | remote | hybrid

Canonical employment:

>     unknown | full | part | project | probation | volunteer | temporary | shift

Canonical experience:

>     unknown | no_experience | between_1_and_3 | between_3_and_6 | more_than_6

Консервативность: `remote=false` не превращается в onsite без
положительного provider signal; malformed salary/date становится
unknown/`None`; display labels не теряются.

Локально пройдены compile, full pytest (139 passed, 6 skipped),
migration 0004 -\> 0005 -\> 0004 -\> 0005, Alembic check и focused
SEARCH-001 suite. После исправления устаревшего test fixture GitHub
Actions полностью зелёный. Render /health/ready подтвердил persistent
PostgreSQL и current/expected revision 20260808_0005. Пользовательский
smoke подтвердил штатную выдачу и canonical filters remote/onsite, опыт
1–3 года и полную занятость. SEARCH-001 = ВЫПОЛНЕНО.

Cross-source fuzzy dedup не входит в SEARCH-001 и остаётся SEARCH-002.

## 10. SEARCH-002 — ВЫПОЛНЕНО

Консервативная cross-source deduplication подтверждена в production:

- fingerprint/similarity service с hard gates и complete-link grouping;
- сохранение всех source IDs/URLs и несколько `VacancySourceRecord` под одной canonical vacancy только для доказанного merge;
- deterministic primary card и bounded explainability metadata;
- reversible persisted grouping при изменении source publication;
- migration `20260809_0006` с nullable dedup metadata без historical backfill;
- multi-source UI со stacked logos и `Все площадки`;
- SuperJob vacancy search доступен по app-level credential без обязательного user OAuth; OAuth сохранён для персональных операций;
- aggregate verification endpoint `/health/search-dedup` не инициирует provider I/O и не хранит keyword/region/salary/credentials.

GitHub Actions полностью зелёный, включая отдельный SEARCH-002 gate, PostgreSQL migration/integration, SEC/OPS/SYNC/SEARCH-001 regressions, backup/restore и container smoke. Render `/health/ready` подтвердил `current_revision=expected_revision=20260809_0006`, `persistent=true`, `status=ok`.

Production negative-smoke: контрольный multi-source поиск обработал 164 candidate records (`hh=20`, `reed=60`, `superjob=24`, `trudvsem=60`) и вернул `input_count=output_count=164`, `cross_source_duplicate_count=0`, `cross_source_groups=0`. Дополнительные поиски также не выявили безопасной real duplicate-pair; ложных merge не обнаружено. Positive merge и multi-source persistence подтверждены CI fixtures. Такое отсутствие реального duplicate в ограниченном fetched window не считается blocker.

Ограничение после закрытия SEARCH-002: dedup выполняется внутри фактически загруженного candidate set. Stable cross-page pagination/global sort/честная total semantics — SEARCH-003.

## 11. SEARCH-003 — ВЫПОЛНЕНО

Реализован bounded persistent pagination candidate:

- `SearchAggregationService` оркестрирует providers вне Flask route;
- SHA-256 query fingerprint не хранит raw keyword/region/salary в snapshot metadata;
- migration `20260809_0007` добавляет четыре ephemeral TTL tables для snapshot/source cursor/candidate/item state;
- SEARCH-001 canonical filters и SEARCH-002 dedup выполняются до stable ordinal;
- deterministic sort имеет явные tie-breakers и не зависит от порядка provider futures;
- уже показанные pages фиксируются committed prefix; late arrivals не переставляют page 0;
- per-provider cursor/error/exhausted state и snapshot items переживают restart;
- per-provider coverage invariant не фиксирует global page boundary, пока каждый non-terminal source не покрывает required depth accepted identities либо не становится exhausted/bounded;
- provider-reported/known unique/exact totals разделены;
- `/health/search-pagination?snapshot=<uuid>` отдаёт только secret-free aggregate state;
- TTL cleanup изолирован от canonical vacancy cache.

GitHub Actions полностью зелёный, включая отдельный SEARCH-003 gate, PostgreSQL migration/integration, SEC/OPS/SYNC/SEARCH-001/002 regressions, encrypted backup/restore и container smoke. Render `/health/ready` подтвердил `current_revision=expected_revision=20260809_0007`, `persistent=true`, `status=ok`.

Первая production-версия выявила latency regression: поиск визуально зависал из-за слишком большого UI page size, нескольких extension rounds и избыточных DB round-trips. Hotfix ввёл `SEARCH_PAGE_SIZE=20`, `SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST=1` и batch persistence candidates/items. Повторный CI зелёный, поиск после deploy работает штатно.

Production snapshot `9368cb00-e7fd-4b67-9276-ea3afcf428ff` подтвердил `page_size=20`, `committed_count=40`, `known_unique_total=69`, `candidate_count=69`, `provider_reported_total=64027`, `late_arrival_count=19`, `total_is_exact=false`, `bounded=false`. После перехода между страницами page 0 сохранил состав/порядок. После Render restart тот же snapshot и provider cursor state сохранились. SEARCH-003 = ВЫПОЛНЕНО.

## 12. SEARCH-004 — ВЫПОЛНЕНО

Реализован candidate canonical vacancy route и безопасные пользовательские состояния источников без изменения database schema:

- `/vacancies` обслуживает текущий unified search UI и является единственным generated canonical route;
- `/vacancies/internal` возвращает permanent `308` на `/vacancies`, сохраняя raw query string, repeated `source`, filters, SEARCH-003 `snapshot` и `page`;
- canonical meta, navbar/footer/home CTA, main/compact forms и pagination используют `/vacancies`;
- `services/source_status.py` вводит `available`, `cached`, `degraded`, `auth_required`, `temporarily_unavailable`;
- HH, SuperJob и Reed показываются как live providers только при фактической настройке/ответе; failure одного provider не ломает общую страницу;
- Trudvsem явно отображается как PostgreSQL-backed cache, включая running/queued/stale/failed refresh состояния;
- public contract не содержит response bodies, exception text, API keys, OAuth tokens или имена environment variables;
- dedicated CI step и route/source-state regression tests подготовлены.

Локально подтверждены compile, Jinja parse, focused source-state suite `6 passed` и полный доступный pytest `193 passed, 6 skipped`. GitHub Actions полностью зелёный, включая отдельный `Verify SEARCH-004 canonical route and source-state controls` и все regression/infrastructure gates. Production `/health/ready` на Render подтвердил PostgreSQL `persistent=true`, `current_revision=expected_revision=20260809_0007`, `migrations.ok=true`, `status=ok`. Мобильный production-smoke подтвердил штатный поиск на canonical `/vacancies` с SEARCH-003 snapshot и page=0. Старый `/vacancies/internal?search=1&keyword=Бухгалтер&source=hh&source=superjob` корректно перенаправился на `/vacancies` с сохранением `keyword` и обоих repeated `source`; новый snapshot/page были сформированы уже canonical route. Database migration не добавлялась. SEARCH-004 закрыт как ВЫПОЛНЕНО.

## 13. AUTH-001 — ВЫПОЛНЕНО

Реализован first-party account candidate:

- существующий `User` используется как identity root;
- migration `20260810_0008` добавляет password fields, `auth_sessions`, `auth_tokens`;
- application-owned scrypt хранит только salted versioned hash;
- verification/reset/session tokens сохраняются только как SHA-256, имеют TTL/single-use/revoke policy;
- `/auth/register`, `/auth/verify`, `/auth/login`, `/auth/logout`, forgot/reset и session revoke работают через service/repository boundary;
- registration/reset/login public copy защищена от email enumeration;
- provider-neutral email delivery: `disabled`, test-only `memory`, SMTP STARTTLS/implicit SSL/TLS и Gmail API HTTPS staging backend;
- dashboard показывает first-party account и active sessions, а HH/SuperJob остаются независимыми до AUTH-002;
- dedicated GitHub Actions gate и PostgreSQL integration подготовлены.

AUTH-001 полностью подтверждён в production staging. GitHub Actions green, включая dedicated AUTH-001 gate и PostgreSQL/infrastructure regressions. Render применяет revision `20260810_0008`; `/health/ready` подтверждает PostgreSQL `persistent=true`, `current_revision=expected_revision=20260810_0008`, `migrations.ok=true`, `auth.email_backend=gmail_api`, `auth.email_delivery_configured=true`, `status=ok`. Реальная verification delivery через Gmail API получена. E2E подтверждает registration, supersede/одноразовость verification links, email verification, email/password login, независимые server-side sessions, individual revoke, revoke-others, logout, forgot/reset, отказ старого пароля, отзыв pre-reset sessions, вход новым паролем и одноразовость reset link. Gmail API остаётся staging-only и не заменяет обязательный pre-release переход на sender собственного домена с SPF/DKIM/DMARC.

Ограничение: при `AUTH_EMAIL_BACKEND=disabled` deploy healthy, но new registration/reset fail-closed; AUTH-001 не закрывается.

## 14. AUTH-002 — ВЫПОЛНЕНО

First-party OAuth ownership завершён и подтверждён production verification:

- connect routes HeadHunter/SuperJob требуют verified first-party session;
- OAuth state связан с first-party `user_id` и `auth_session_id`;
- callback атомарно create/claim/refresh owner-bound `OAuthConnection`;
- email auto-link и provider browser identity запрещены;
- migration `20260811_0009` добавляет unique `(user_id, provider)`, сохраняя unique external identity и nullable legacy rows;
- owner-scoped dashboard, token refresh/reconnect and disconnect;
- disconnect удаляет unified и provider mirror credentials;
- dedicated CI gate и ownership/state/migration/route tests полностью green.

Evidence: GitHub Actions `Success`, включая dedicated AUTH-002 gate; Render `/health/ready` — PostgreSQL `persistent=true`, `current_revision=expected_revision=20260811_0009`, `migrations.ok=true`, `status=ok`, `oauth_configured=true`. Реальный E2E HeadHunter и SuperJob подтвердил connect, persistence после first-party relogin, reconnect без дубля, запрет cross-user claim, сохранение ownership первого User и disconnect с устойчивым отключённым состоянием после refresh/relogin. Итоговая regression-проверка и Render logs подтверждены пользователем как штатные.

Remote provider revoke, admin identity transfer, phone/social identities и profile import не входят.

## 15. PROF-001 — ВЫПОЛНЕНО

Structured career profile candidate реализован поверх first-party `User`:

- одна current `career_profiles` row на User;
- immutable `career_profile_versions` для каждого material save;
- manual confirmation boundary: неподтверждённый import/AI/provider snapshot не записывается;
- sections: positioning, contacts, goals, geography, salary, skills, employment, achievements, education, languages;
- incomplete profile allowed; deterministic completion indicator;
- bounded validation, canonical JSON/hash, optimistic version conflict and PostgreSQL row lock;
- owner-only `/profile`, edit and read-only history/version views;
- migration `20260811_0010`, backup inventory and dedicated CI gate.

Local evidence: full available pytest `240 passed, 9 skipped`; extended focused PROF-001 checks `26 passed, 3 skipped`; migration round-trip/Alembic check/compile/Jinja/document/infra/hygiene passed. Flask/PostgreSQL route/integration proof remains GitHub CI gate. External completion requires PR CI, Render `0010`, relogin/restart persistence, owner isolation, stale conflict/versioning and AUTH/OAuth/search regression smoke. Initial Pull Request CI and Render migration/readiness `0010` passed. First production E2E exposed a form-validation defect: blank repeatable rows carried default select values and were treated as real records. Hotfix v1.4.21 ignored only default-only rows and added regression coverage; hotfix CI was green and Render redeploy remained on `0010`. Final production E2E confirmed partial save with 25% completion, relogin persistence, material versioning, immutable history, no-op save, owner isolation, stale-editor conflict, restart persistence, mobile operation and AUTH/OAuth/search regression. PROF-001 is ВЫПОЛНЕНО.

Excluded: resume import/review (PROF-002), drafts/autosave (PROF-003), restore historical snapshot, export/delete/retention (PRIV-001), AI-generated facts and public profile.

## 16. PROF-002 — ВЫПОЛНЕНО

Resume import реализован и подтверждён как confirmation-first extension PROF-001:

- authenticated bounded text-PDF upload;
- request-local `pypdf` extraction and deterministic proposals;
- editable review with confidence/warnings/conflicts/evidence;
- no persistence before explicit confirm;
- current confirmed scalar facts preserved by default on conflict;
- explicit confirm reuses PROF-001 validation/hash/version/row-lock rules;
- immutable history records `source_kind=resume_import` and aggregate provenance;
- metadata-only owner/version-bound timed review token;
- migration `20260812_0011`; canonical profile schema remains 1.

External evidence: initial Pull Request CI and dedicated PROF-002 gate green; Render readiness current/expected `0011`; production E2E confirmed no-save-before-confirm, user corrections, one import version/provenance, stale conflict, copied-URL cross-account isolation, non-PDF and scan-only safe failures, restart persistence, mobile review and final AUTH/OAuth/search/log regression.

Production verification found a generic 256 KiB upload-route defect for `/profile/import`; hotfix r2 classified the route as upload, retained the 8 MiB product limit, added loading/error UX and regression coverage with no schema change.

Quality observation: `deterministic-text-v1` can make low-confidence/incorrect suggestions on English/nonstandard CVs; mandatory review prevented canonical corruption. OCR/AI parser remains excluded.

## 17. PROF-003 — ВЫПОЛНЕНО

Server-side resume document layer подтверждён полностью: green CI, Render `20260812_0012`, owner-scoped drafts, autosave, immutable history/restore/no-op, stale `409`, cross-device/relogin/restart persistence, direct edit r2, iPhone asset r3, university logo, PDF parity r4, owner isolation, финальный `/profile`/PROF-002/`/dashboard`/AUTH/OAuth/`/vacancies` regression и Render log privacy/error review. Generated document state по-прежнему не становится PROF-001 confirmed facts автоматически.

## 17.1 PRIV-001 — ВЫПОЛНЕНО

PRIV-001 завершён и подтверждён в production:

- `/privacy-center` с re-authenticated export/delete controls;
- ZIP export с `manifest.json`, `data.json` и условным `assets/` только для owned referenced resume images;
- password/session/token/OAuth secrets не попадают в export; provider profile sanitizer и safe ZIP paths включены;
- delete guard: exact phrase + current password + password-hash recheck under User row lock;
- coordinated Auth/OAuth lock order и cascade delete User/Auth/OAuth/Profile/Resume data с explicit legacy HH/SJ local mirror cleanup;
- identifier-free `privacy_audit_events`;
- technical retention cleanup: pending unverified 30d, expired/revoked auth artifacts 30d, orphan resume assets 7d, audit 180d, worker interval 24h;
- migration `20260813_0013`, healthy privacy worker, backup inventory, Compose/Render/VPS knobs and dedicated CI gate.

Green GitHub Actions after CI hotfix r1, Render `0013`, export/asset/secret scan, destructive throwaway deletion, owner isolation, restart/regression and Render log review are confirmed. Technical retention defaults are not legal-policy claims; `LEGAL-001` can revise them. Remote provider-side OAuth grant revocation is not automated; current contract guarantees local credential erasure only.

## 18. INFRA-001 — ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА

`INFRA-001` теперь означает только реальную аренду и полевой тест VPS:

1.  public IPv4 и временный TLS hostname;
2.  доступность минимум из двух сетей РФ и одной сети РБ без VPN;
3.  health/search/resume/security smoke;
4.  outbound transport к Yandex AI и Reed;
5.  latency/cost/SLA/backup assessment;
6.  provider decision record.

До начала этого пакета Render остаётся staging/резервной площадкой,
DNS/OAuth callback URL не переключаются.

## 19. Текущее функциональное состояние

- Главная/AI Career/resume builder работают.
- Search: canonical `/vacancies`; Trudvsem, HH, Reed и public SuperJob; SEARCH-001/002/003/004 подтверждены GitHub CI и production smoke.
- OAuth HH/SJ: AUTH-002 owner-bound и подтверждён production E2E; tokens encrypted, cross-user claim блокируется.
- Trudvsem cache остаётся PostgreSQL-backed; внешний worker и SYNC-002 checkpoint/retry/lifecycle подтверждены.
- SEARCH-001 canonical contract и SEARCH-002 conservative dedup подтверждены; multi-source grouping сохраняет все исходные публикации.
- PDF parser эвристический, не LLM.
- Saved jobs пока localStorage.
- First-party account AUTH-001, OAuth ownership AUTH-002, structured profile PROF-001 и resume import PROF-002 подтверждены production E2E. PROF-002 сохраняет confirmation-first boundary; real AI/match/letters/tracker впереди.

## 20. Новая обязательная очередь разработки

### Сейчас — функциональный MVP без аренды VPS

>     PRIV-001 COMPLETE
>     -> SEARCH-005 READY
>     -> AI-BENCH-001 -> AI-PROVIDER-001 -> LEGAL-001
>     -> AI-001 -> AI-002 -> AI-003 -> AI-004 -> AI-005 -> AI-006
>     -> JOB-001 -> JOB-002 -> JOB-003/JOB-004
>     -> PERF/A11Y/ANL по готовности

`DOC-001` выполняется постоянно вместе с каждым package и не является
отдельным blocker.

### Перед beta / production — инфраструктурный блок

>     INFRA-001 -> REED-COMPAT-001 -> HOST-001
>     -> OPS-002 + production backup/restore drill
>     -> DOMAIN-001 -> MIG-001
>     -> final SEC/OPS smoke -> REL-001 -> commercial release

## 21. Зафиксированная hosting-independent стратегия

До предрелизного окна новый код не должен зависеть от конкретного
hosting provider:

- configuration через `config.py` и environment variables;
- PostgreSQL через `DATABASE_URL`, schema только Alembic;
- WSGI `app:app`;
- публичные абсолютные URL через будущий `PUBLIC_BASE_URL`;
- provider/AI integrations через service/adapters и feature flags;
- worker/scheduler отделяется от web process в `SYNC-001`;
- health/readiness, Docker/Compose и probes остаются в CI.

Render не считается гарантированным production для РФ/РБ из-за
подтверждённой сетевой недоступности из части сетей РФ, но остаётся
пригодным staging/резервным контуром до `MIG-001`.

## 22. AI и Reed

- `AI-BENCH-001` можно выполнять без реального VPS: качество Yandex AI
  Studio/Alice AI проверяется на golden dataset, а transport с будущего
  source IP повторяется в `INFRA-001`.
- Бизнес-логика должна использовать независимый `AIProvider`; OpenAI не
  является обязательным baseline для РФ/РБ.
- API keys хранятся только на сервере.
- `REED-COMPAT-001` требует точного IP выбранного VPS и выполняется
  сразу после `INFRA-001`.
- Reed должен иметь feature flag и graceful degradation.

## 23. Текущий gate

SEARCH-005 — ВЫПОЛНЕНО. Comparative AI-BENCH live run #4 was reviewed; Alice AI LLM is the primary candidate. Final gate is green ordinary CI, Alice-only 8/8 machine verification and named human rubric. Production PostgreSQL remains `20260819_0014`; no production AI provider is connected.

## 24. Правила рабочего чата

- Перед изменениями читать паспорт, PLAN_CURRENT и актуальный ZIP;
  работать по одному package ID.
- Не смешивать unrelated design/business changes.
- Не ставить ВЫПОЛНЕНО без критериев и доказательств.
- После пакета возвращать ZIP, PLAN_CURRENT DOCX/PDF/MD, паспорт и
  source audit без `.env`, secrets, databases, dumps, backups,
  virtualenv, caches и bytecode.
- Канонические и repository docs синхронизируются вместе с каждым code
  package.
- Для новых документов применять единый документный стандарт проекта.

## 25. Журнал версий

- **2.20 — 08.08.2026:** SEARCH-001 закрыт после CI, Render revision `0005` и production filter smoke.
- **2.21 — 09.08.2026:** SEARCH-002 реализован как conservative reversible cross-source dedup candidate с additive migration `20260809_0006`; требуется GitHub/Render verification.
- **2.22 — 09.08.2026:** SEARCH-002 complete; SEARCH-003 ready.
- **2.23 — 09.08.2026:** SEARCH-003 persistent stable pagination/honest totals candidate с migration `20260809_0007`; требуется GitHub/Render verification.
- **2.24 — 09.08.2026:** SEARCH-003 complete: green CI, Render `0007`, latency hotfix, stable committed pages, honest totals и restart persistence; SEARCH-004 ready.
- **2.25 — 10.08.2026:** SEARCH-004 candidate: canonical `/vacancies`, permanent method-preserving legacy redirect, safe public source-state contract и dedicated CI gate; требуется GitHub/Render verification.
- **2.26 — 10.08.2026:** SEARCH-004 complete: green CI, Render `0007`, canonical `/vacancies` mobile search and legacy redirect; AUTH-001 ready.
- **2.27 — 10.08.2026:** AUTH-001 candidate: migration `20260810_0008`, first-party identity, versioned scrypt, one-time tokens, revocable sessions, SMTP adapter, UI/tests/CI; требуется GitHub/Render/SMTP E2E.
- **2.28 — 10.08.2026:** Render `0008` + SMTP readiness confirmed; Safari missing-Referer CSRF regression localized; `strict-origin` hotfix prepared without weakening strict CSRF.
- **2.29 — 11.08.2026:** Safari hotfix production-pass confirmed; Mail.ru implicit SSL/TLS fallback added; v1.4.15 CI/readiness green.
- **2.30 — 11.08.2026:** Render Free SMTP egress blocker documented; Gmail API HTTPS staging backend added with mandatory domain sender migration before beta/commercial release.
- **2.31 — 11.08.2026:** AUTH-001 закрыт после green GitHub Actions, Render Gmail API readiness/delivery и полного production E2E; AUTH-002 становится следующим пакетом. Domain sender + SPF/DKIM/DMARC остаются обязательным pre-release gate.
- **2.32 — 11.08.2026:** AUTH-002 candidate: owner-bound HH/SJ identities, migration 0009, state/session binding, encrypted owner-scoped reconnect/disconnect and dedicated tests; external verification pending.
- **2.33 — 11.08.2026:** AUTH-002 complete: green GitHub Actions, Render `0009`, полный HH/SJ ownership E2E и regression smoke подтверждены; PROF-001 становится следующим пакетом.
- **2.34 — 11.08.2026:** PROF-001 candidate: owner-scoped structured facts, immutable version history, migration `0010`, UI/service/repository/tests and dedicated CI gate; external verification pending.
- **2.35 — 12.08.2026:** PROF-001 hotfix candidate: initial CI/Render `0010` passed; production partial-save uncovered default-only repeatable-row validation bug. Hotfix keeps schema `0010`, fixes optional-row detection and adds regression tests; verification resumes after redeploy.
- **2.36 — 12.08.2026:** PROF-001 complete after green hotfix CI, Render `0010`, full owner/version/concurrency/restart/mobile/regression E2E; PROF-002 becomes next.
- **2.37 — 12.08.2026:** PROF-002 candidate: bounded text-PDF extraction proposal, editable review, explicit confirmation, metadata-only owner/version-bound review token, migration `0011` provenance audit fields and dedicated tests; external verification pending.
- **2.38 — 12.08.2026:** PROF-002 complete after green CI, Render `0011`, upload-limit hotfix and production confirmation/privacy/stale/restart/mobile/regression E2E; PROF-003 next.
- **2.39 — 13.08.2026:** PROF-003 candidate: server drafts, optimistic autosave, immutable versions/history/restore, durable assets, export metadata, migration `0012`, UI/tests/CI gate; external verification pending.
- **2.40 — 13.08.2026:** PROF-003 production evidence: CI/Render `0012`, drafts/autosave/cross-device, versions/restore/stale conflict, direct edit r2, iPhone photo r3, PDF/logo/education parity r4, owner isolation and restart persistence confirmed; final regression/log review remains.
- **2.41 — 13.08.2026:** PROF-003 closed after final regression/log review. PRIV-001 candidate adds readable export, confirmed deletion, local integration/token cleanup, technical retention worker, identifier-free audit and migration `0013`; external CI/Render/E2E pending.
- **2.42 — 19.08.2026:** PRIV-001 hardened candidate after second privacy/security audit: re-authenticated consistent export, bounds/safe paths/sanitizer, delete concurrency locks, orphan asset cleanup and worker lock/heartbeat; external gate pending.
- **2.46 — 19.08.2026:** PRIV-001 completed after green CI/hotfix r1, Render `0013`, healthy privacy worker, export/asset/secret scan, destructive throwaway deletion, owner isolation, restart/regression/log review. SEARCH-005 ready next.
- **2.47 — 24.08.2026:** AI-BENCH-001 candidate v1.4.32 rejected by CI because root containers were scanned by unsupported-number gate; hotfix r1 scans scalar leaves only, adds regression tests and awaits repeat GitHub Actions.
- **2.51 — 26.08.2026:** GitHub run #201 was rejected before runner allocation because `runner.temp` was referenced from `jobs.ai-bench-yandex-live.env`. Hotfix r4 uses `/tmp/ai-bench-yandex-live`, adds local job-env context validation/regression coverage, and keeps production revision `20260819_0014` unchanged.




## SEARCH-005 architecture addendum (historical)

- **Admin boundary:** active verified first-party account plus exact normalized email in deployment allowlist `SEARCH_ADMIN_EMAILS`. A diagnostics secret, hidden URL or OAuth provider account is not admin authorization.
- **Persistence:** `source_health_states` stores only current safe operational aggregates for `hh`, `superjob`, `reed`, `trudvsem`; no user relation exists.
- **Public/admin split:** public source state remains minimal. `/admin/sources` and `/api/admin/sources` are read-only, rate-limited, no-store and return neutral 404 to ordinary users.
- **Recorded fields:** availability, configured boolean/reason, last attempt/success/failure, bounded latency, failure streak, safe error class/code, cache timestamp/count and allowlisted sync/worker aggregates.
- **Forbidden fields:** tokens, credentials, provider bodies, URLs with query/fragment, user search terms, emails, user IDs, resume/profile content and external identity IDs.
- **Telemetry:** current process observability events are persisted through a non-gating adapter. Trudvsem additionally uses persistent SyncRun/worker/checkpoint data. No external network probe runs when the page is opened.
- **Schema:** candidate `20260819_0014`; production remains `20260813_0013` until external gate.
- **Deployment:** administrator email allowlist must be configured in Render/VPS environment before E2E. `SOURCE_HEALTH_RECORDING_ENABLED=1`; default stale threshold 900 seconds.


### PROJECT_PASSPORT v2.48 update

| Версия | Дата | Изменение |
|---|---|---|
| 2.48 | 25.08.2026 | Confirmed hotfix r1 green GitHub Actions and manual Alice Playground smoke; added isolated evals 1.1.0 Yandex live workflow candidate with GitHub-secret-only credentials. AI-PROVIDER-001 remains blocked pending live artifact/manual review. |

### PROJECT_PASSPORT v2.49 update

| Версия | Дата | Изменение |
|---|---|---|
| 2.49 | 25.08.2026 | Audited GitHub run #192. The SYNC failure was a calendar-sensitive test assertion after a successful worker run; the AI-BENCH failure was a browser-upload dotfile packaging dependency. Added stable persisted-cache assertions and visible eval artifact scaffold. Production revision/routes remain unchanged; repeat CI is required. |

### PROJECT_PASSPORT v2.50 update

| Версия | Дата | Изменение |
|---|---|---|
| 2.50 | 25.08.2026 | Audited GitHub run #196 and the exact uploaded ZIP. The separate live workflow lost its `.yml` suffix while all production files remained unchanged. The billable Yandex job is now integrated into `ci.yml`, manual-only, default-off, concurrent-run protected, and dependent on all ordinary CI gates. |
### PROJECT_PASSPORT v2.51 update

| Версия | Дата | Изменение |
|---|---|---|
| 2.51 | 26.08.2026 | GitHub run #201 was rejected before runner allocation because `runner.temp` was referenced from `jobs.ai-bench-yandex-live.env`. Hotfix r4 uses `/tmp/ai-bench-yandex-live`, adds local job-env context validation/regression coverage, and keeps production revision `20260819_0014` unchanged. |


### PROJECT_PASSPORT v2.52 update

| Версия | Дата | Изменение |
|---|---|---|
| 2.52 | 26.08.2026 | Ordinary CI after stability r4 confirmed green; first Yandex live run completed 24 requests without API errors. Artifact review drove grounded-v2: stronger evidence/safety contracts and deterministic vacancy match score. Production architecture/revision unchanged; provider decision remains pending live run #2/manual review. |


### PROJECT_PASSPORT v2.53 update

| Версия | Дата | Изменение |
|---|---|---|
| 2.53 | 26.08.2026 | Live run #2 reviewed. Grounded-v2.1 / evals 1.3.0 adds Unicode numeric normalization, scenario provenance, language gate, motivation semantics, safe provider diagnostics and one bounded retry. Production architecture/revision remains unchanged; provider decision awaits live run #3/manual rubric. |


### PROJECT_PASSPORT v2.54 update

| Версия | Дата | Изменение |
|---|---|---|
| 2.54 | 26.08.2026 | Live run #3 reviewed. Grounded-v2.2 / evals 1.4.0 adds source-matched cover-letter impact families, regressions for the machine-missed Alice outcome inference and a presentation-only sanitizer for simple decorated evidence markers. Production architecture/revision remains unchanged; provider decision awaits final live run #4 and named manual rubric. |

### PROJECT_PASSPORT v2.55 update

| Версия | Дата | Изменение |
|---|---|---|
| 2.55 | 27.08.2026 | Comparative grounded-v2.2 live run #4 reviewed: Alice 5/8, Flash 5/8, YandexGPT Pro 4/8 with 24/24 calls and no transport errors/retries. Alice nominated as final candidate. Evals 1.4.1 adds prompt-level literal fact discipline, independent causal-impact safety, run-4 regressions and dedicated Alice-only 8/8 machine verification before named human review. Production architecture/revision remains unchanged. |

### PROJECT_PASSPORT v2.56 update

| Версия | Дата | Изменение |
|---|---|---|
| 2.56 | 27.08.2026 | Alice Final run #1 artifact `33061758538` reviewed: 8/8 calls, 0 errors/retries, source machine 6/8. Both FAILs are interview structured-provenance/number-classification issues. Evals 1.5.0 / benchmark 1.4 / dataset 1.3.2 / grounded-v2.3 adds raw-vs-machine evidence separation, audited unique scenario-evidence repair, a narrow answer-cardinality exception and tighter scenario-use prompts. Offline replay of retained raw responses is 8/8, but a fresh Alice-only live verification and named human rubric remain mandatory. Production architecture/revision remains unchanged. |

