# AI Career Agent — паспорт проекта

| Поле | Значение |
|---|---|
| Документ        | PROJECT_PASSPORT                                                                              |
| Версия паспорта | 2.27 |
| Дата            | 10 августа 2026                                                                               |
| Статус          | ДЕЙСТВУЮЩИЙ                                                                                   |
| Связанный план | `AI_Career_Agent_PLAN_CURRENT v1.4.13` |
| Основа кода | `ai-career-agent-site-main (6).zip` из актуального GitHub `main`; AUTH-001 candidate реализован поверх SEARCH-004; production до deploy остаётся `20260809_0007` |

> Контрольные статусы: FND-001/FND-002/DATA-001/DATA-002/SEC-001/OPS-001/INFRA-PREP-001/SYNC-001/SYNC-002/SEARCH-001/SEARCH-002/SEARCH-003 — ВЫПОЛНЕНО; SEARCH-004 — ВЫПОЛНЕНО; AUTH-001 — НУЖНА ПРОВЕРКА; DOC-001 — В РАБОТЕ как постоянный процесс; INFRA-001 — ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА.

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
>     migrations/                Alembic 0001 + 0002 + 0003 + 0004 + 0005 + 0006 + 0007 + 0008 candidate
>     tests/                     unit/integration/security/ops/infra/sync/search/auth tests
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

## 13. AUTH-001 — НУЖНА ПРОВЕРКА

Реализован first-party account candidate:

- существующий `User` используется как identity root;
- migration `20260810_0008` добавляет password fields, `auth_sessions`, `auth_tokens`;
- application-owned scrypt хранит только salted versioned hash;
- verification/reset/session tokens сохраняются только как SHA-256, имеют TTL/single-use/revoke policy;
- `/auth/register`, `/auth/verify`, `/auth/login`, `/auth/logout`, forgot/reset и session revoke работают через service/repository boundary;
- registration/reset/login public copy защищена от email enumeration;
- provider-neutral email delivery: `disabled`, test-only `memory`, production SMTP STARTTLS;
- dashboard показывает first-party account и active sessions, а HH/SuperJob остаются независимыми до AUTH-002;
- dedicated GitHub Actions gate и PostgreSQL integration подготовлены.

Локально compile, migration round-trip, config/password/auth service tests и полный доступный pytest пройдены. Пакет остаётся НУЖНА ПРОВЕРКА до green CI, Render revision `0008`, SMTP configuration и real register/verify/login/logout/reset/session-revoke E2E.

Ограничение: при `AUTH_EMAIL_BACKEND=disabled` deploy healthy, но new registration/reset fail-closed; AUTH-001 не закрывается.

## 14. INFRA-001 — ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА

`INFRA-001` теперь означает только реальную аренду и полевой тест VPS:

1.  public IPv4 и временный TLS hostname;
2.  доступность минимум из двух сетей РФ и одной сети РБ без VPN;
3.  health/search/resume/security smoke;
4.  outbound transport к Yandex AI и Reed;
5.  latency/cost/SLA/backup assessment;
6.  provider decision record.

До начала этого пакета Render остаётся staging/резервной площадкой,
DNS/OAuth callback URL не переключаются.

## 15. Текущее функциональное состояние

- Главная/AI Career/resume builder работают.
- Search: canonical `/vacancies`; Trudvsem, HH, Reed и public SuperJob; SEARCH-001/002/003/004 подтверждены GitHub CI и production smoke.
- OAuth HH/SJ: текущий pre-MVP, tokens encrypted.
- Trudvsem cache остаётся PostgreSQL-backed; внешний worker и SYNC-002 checkpoint/retry/lifecycle подтверждены.
- SEARCH-001 canonical contract и SEARCH-002 conservative dedup подтверждены; multi-source grouping сохраняет все исходные публикации.
- PDF parser эвристический, не LLM.
- Saved jobs пока localStorage.
- First-party account candidate реализован; production verification ожидается. Profile/real AI/match/letters/tracker впереди.

## 16. Новая обязательная очередь разработки

### Сейчас — функциональный MVP без аренды VPS

>     AUTH-001 verification -> AUTH-002
>     -> PROF-001 -> PROF-002 -> PROF-003 -> PRIV-001
>     -> SEARCH-005
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

## 17. Зафиксированная hosting-independent стратегия

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

## 18. AI и Reed

- `AI-BENCH-001` можно выполнять без реального VPS: качество Yandex AI
  Studio/Alice AI проверяется на golden dataset, а transport с будущего
  source IP повторяется в `INFRA-001`.
- Бизнес-логика должна использовать независимый `AIProvider`; OpenAI не
  является обязательным baseline для РФ/РБ.
- API keys хранятся только на сервере.
- `REED-COMPAT-001` требует точного IP выбранного VPS и выполняется
  сразу после `INFRA-001`.
- Reed должен иметь feature flag и graceful degradation.

## 19. Следующий пакет

AUTH-001 — НУЖНА ПРОВЕРКА. Candidate использует existing User, migration `20260810_0008`, versioned scrypt, hashed verification/reset tokens, revocable PostgreSQL sessions, auth blueprint/UI и SMTP adapter. Production до deploy остаётся `20260809_0007`; email delivery default `disabled`.

Verification gate:

```text
GitHub Actions green, включая AUTH-001 gate
-> Render current/expected revision 20260810_0008
-> SMTP STARTTLS configured, auth email configured=true
-> register/verify/login/two sessions/revoke/logout
-> forgot/reset single-use, old sessions invalid
-> no auth secrets or raw tokens in logs
-> AUTH-001 complete
```

Следующий обязательный пакет после подтверждения — AUTH-002. SEARCH-005 остаётся после account/profile/privacy foundation.

## 20. Правила рабочего чата

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

## 21. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 2.20 | 08.08.2026 | SEARCH-001 закрыт после CI, Render revision `0005` и production filter smoke. |
| 2.21 | 09.08.2026 | SEARCH-002 реализован как conservative reversible cross-source dedup candidate с additive migration `20260809_0006`; требуется GitHub/Render verification. |
| 2.22 | 09.08.2026 | SEARCH-002 complete; SEARCH-003 ready. |
| 2.23 | 09.08.2026 | SEARCH-003 persistent stable pagination/honest totals candidate с migration `20260809_0007`; требуется GitHub/Render verification. |
| 2.24 | 09.08.2026 | SEARCH-003 complete: green CI, Render `0007`, latency hotfix, stable committed pages, honest totals и restart persistence; SEARCH-004 ready. |
| 2.25 | 10.08.2026 | SEARCH-004 candidate: canonical `/vacancies`, permanent method-preserving legacy redirect, safe public source-state contract и dedicated CI gate; требуется GitHub/Render verification. |
| 2.26 | 10.08.2026 | SEARCH-004 complete: green CI, Render `0007`, canonical `/vacancies` mobile search and legacy redirect; AUTH-001 ready. |
| 2.27 | 10.08.2026 | AUTH-001 candidate: migration `20260810_0008`, first-party identity, versioned scrypt, one-time tokens, revocable sessions, SMTP adapter, UI/tests/CI; требуется GitHub/Render/SMTP E2E. |
