# AI Career Agent — паспорт проекта

| Поле | Значение |
|---|---|
| Документ | PROJECT_PASSPORT |
| Версия паспорта | 2.19 |
| Дата | 08 августа 2026 |
| Статус | ДЕЙСТВУЮЩИЙ |
| Связанный план | `AI_Career_Agent_PLAN_CURRENT v1.4.5` |
| Основа кода | `ai-career-agent-site-main (11).zip`; поверх актуального `main` реализован candidate SEARCH-001 с revision `20260808_0005` |

> Контрольные статусы: FND-001/FND-002/DATA-001/DATA-002/SEC-001/OPS-001/INFRA-PREP-001/SYNC-001/SYNC-002 — **ВЫПОЛНЕНО**; SEARCH-001 — **НУЖНА ПРОВЕРКА**; SEARCH-002 — **ЗАПЛАНИРОВАНО**; DOC-001 — **В РАБОТЕ**; INFRA-001 — **ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА**.

## 1. Назначение

AI Career Agent — коммерческий веб-сервис карьерного сопровождения:

```text
аккаунт -> резюме -> подтверждённый профиль -> AI-анализ
-> реальные вакансии -> объяснимый match -> письмо -> tracker
```

Пользователь принимает окончательные решения самостоятельно.

## 2. Источник истины

1. GitHub — главный источник актуального кода.
2. Более новый ZIP в текущем чате — рабочая основа задачи.
3. Канонический PLAN_CURRENT определяется наибольшей версией и датой.
4. Старые план/паспорт удаляются после замены.
5. Главный файл — `app.py`; WSGI — `app:app`; `app_fixed.py` не используется.

## 3. Технологии и структура

- Python 3.11, Flask 3.1.3, Gunicorn;
- SQLAlchemy 2, Alembic, PostgreSQL 17/Psycopg 3;
- SQLite local/test fallback;
- Flask-WTF, Flask-Limiter, Cryptography/Fernet/AES-GCM;
- GitHub Actions;
- Docker multi-target images, Docker Compose, Caddy test TLS и VPS probe tooling;
- Render временно как staging/резервная площадка;
- production VPS арендуется и тестируется только в предрелизном `INFRA-001`;
- основной AI-кандидат — Yandex AI Studio/Alice AI после `AI-BENCH-001`.

```text
app.py                     Flask routes, app:app
config.py                  production/development/test/ops settings
database.py                SQLAlchemy runtime and DB health
security.py                CSRF/rate limits/headers/request limits
observability.py           structured logs/request IDs/metrics/alerts
operations/backup.py       encrypted backup/verified restore
Dockerfile / compose.yaml  runtime, ops, DB, migrations, restore-test
infra/                     Gunicorn, Caddy, VPS environment and probes
scripts/                   migrations, backup, restore, alert, infra probes, sync CLI/worker/supervisor
domain/ models/ repositories/ services/
migrations/                Alembic 0001 + 0002 + 0003 + 0004 + 0005 (vacancy normalization contract)
tests/                     unit/integration/security/ops/infra/sync tests
docs/                      architecture, security and runbooks
render.yaml
.github/workflows/ci.yml
```

## 4. Подтверждённые базовые пакеты

### FND-001 — ВЫПОЛНЕНО

Базовые tests/CI и Render smoke подтверждены.

### FND-002 — ВЫПОЛНЕНО

Central config/APP_ENV, CI и Render подтверждены; `HH_CURRENCY_SCAN_PAGES=20`.

### DATA-001 — ВЫПОЛНЕНО

PostgreSQL 17, `DATABASE_URL`, Alembic `20260804_0001`, restart persistence подтверждены.

### DATA-002 — ВЫПОЛНЕНО

User/OAuthConnection/canonical Vacancy/VacancySourceRecord/SyncRun, repositories, StorageServices и migration `20260804_0002` подтверждены в CI и Render; cache/persisted run пережили restart.

### SEC-001 — ВЫПОЛНЕНО

Production подтвердил secure `aca_session`, CSRF `400`, CSP/HSTS/browser headers, закрытые diagnostics, безопасный Trudvsem status, secret-free logs и стабильный rate-limit bucket: первые 20 запросов к diagnostic route дали `404`, 21-й — `429` с `Retry-After`.

## 5. OPS-001 — ВЫПОЛНЕНО

Подтверждены production JSON logs, `X-Request-ID` correlation, health/live/readiness, protected `/ops/status`, provider metrics, sanitised alert webhook, encrypted PostgreSQL backup/restore toolchain и отдельные GitHub OPS/backup steps.

**Важно:** ранее незакрытый encrypted backup реальной production PostgreSQL + restore в отдельную test database не объявлен пройденным. В PLAN_CURRENT 1.4.5 он перенесён целиком в `OPS-002` и повторно проверяется в `REL-001`. Это release gate, а не текущий blocker функциональной разработки.

OPS-001 database migration отсутствовала. Production schema остаётся `20260807_0004`; SEARCH-001 candidate ожидает проверку additive revision `20260808_0005`.

## 6. INFRA-PREP-001 — ВЫПОЛНЕНО

Кодовая часть прежнего INFRA-001 выделена в самостоятельный подготовительный пакет без изменения кода:

- non-root runtime/ops Docker images;
- Compose stack с private PostgreSQL, one-shot migrations, web, optional Caddy TLS и isolated restore DB;
- secret-free environment template;
- DNS/TCP/TLS/HTTP probes для app/Yandex AI/Reed и optional providers;
- manifest validation, Docker build и runtime smoke в GitHub Actions;
- VPS runbook и provider shortlist.

Это делает приложение переносимым на VPS без необходимости оплачивать ВМ во время разработки.

## 7. SYNC-001 — ВЫПОЛНЕНО

Внешний контур Trudvsem sync реализован и подтверждён в production:

- Gunicorn/Flask не создаёт daemon thread и не выполняет provider HTTP;
- web routes читают PostgreSQL cache и идемпотентно ставят durable job в `sync_runs`;
- `scripts/trudvsem_sync_worker.py` выполняет jobs отдельным OS process;
- `scripts/sync_trudvsem.py` поддерживает one-shot/queue CLI;
- PostgreSQL advisory lock и SQLite lockfile блокируют параллельный sync;
- `sync_workers` хранит heartbeat/liveness;
- migration `20260807_0003` добавляет one-active-run constraint и закрывает legacy abandoned runs;
- Render использует `scripts/start_runtime.py`, Docker Compose - отдельный `sync-worker` profile;
- provider timeout сохраняет старый cache и переводит run в контролируемое terminal state.

**Production verification 07.08.2026:** GitHub Actions полностью зелёный; `/health/ready` подтвердил PostgreSQL, `persistent=true`, current/expected revision `20260807_0003`; Render supervisor запустил внешний worker; после исправления import path worker выполняет реальные batches (`normalized items=10`, `result_count=10`). Public Trudvsem status показал активный run (`running=true`, progress 43%, `cached_total=102`) и корректное завершение (`running=false`, `queued=false`, `cached_total=102`). После реального restart `uptime_seconds` сбросился до 89 и затем вырос до 112, а cache остался `102`.

Отдельно зафиксировано: `cache_age_seconds` после restart не сбрасывается, потому что отражает возраст сохранённого PostgreSQL cache, а не uptime web-процесса.

## 8. SYNC-002 — ВЫПОЛНЕНО

Поверх подтверждённого external worker внедрена и принята incremental freshness/cleanup policy:

- migration `20260807_0004` создаёт `sync_checkpoints` и lifecycle-поля source records;
- committed watermark, bounded pending window, cursor/offset/total и retry state живут в PostgreSQL, а не в process memory;
- overlap 300 секунд + idempotent upsert защищают границу окна;
- explicit closed/expired lifecycle, TTL closure и retention purge реализованы и покрыты tests;
- upstream failure не продвигает watermark/cleanup и не удаляет последний cache;
- scheduled worker соблюдает persistent bounded exponential backoff.

**GitHub verification 08.08.2026:** весь workflow зелёный, включая SYNC-001/SYNC-002 gates, PostgreSQL migrations/integration, encrypted backup/restore, Docker/Compose, runtime smoke и full tests.

**Render verification 08.08.2026:** `/health/ready` и `/health` вернули `200`, `database.backend=postgresql`, `persistent=true`, current/expected revision `20260807_0004`. Diagnostics подтвердили window `pending=true`, `pending_offset=3`, `pending_total=92287`, watermark `1785926683`, from `1785926383`, to `1786195111` и 300-second overlap. На реальных `Read timed out` внешнего Trudvsem API cursor/watermark/cache сохранялись; worker оставался жив; backoff увеличивался; после redeploy checkpoint и `cached_total=102`/`active_total=552` сохранились.

**Принятое ограничение:** из-за длительных timeout `opendata.trudvsem.ru` на Render не дождались успешного продвижения `pending_offset > 3` и production cleanup полного окна. Эти success-path сценарии покрыты automated tests/CI. По решению владельца они не блокируют SEARCH-001 и повторяются на реальном российском VPS в `INFRA-001/OPS-002`, где ожидается более стабильный маршрут к Trudvsem.

После verification временные `DEBUG_DIAGNOSTICS`/`DIAGNOSTICS_SECRET` должны быть удалены из production Environment.

## 9. SEARCH-001 — НУЖНА ПРОВЕРКА

Реализован единый provider-to-application contract вакансии:

- `NormalizedVacancy` и documented enums для формата работы, занятости и опыта;
- central normalizer для текста, валюты, зарплаты и UTC timestamps;
- adapters HH, Reed, SuperJob и Trudvsem возвращают одинаковые keys/types;
- migration `20260808_0005` добавляет nullable canonical code columns и индексы;
- store/repository сохраняют codes; legacy rows не блокируют выдачу благодаря fallback только при `NULL`;
- exact canonical filters применяются после provider aggregation;
- unknown provider values не маскируются ложным onsite/full/experience;
- cross-source dedup не входит и остаётся SEARCH-002.

Локально подтверждены `139 passed, 6 skipped`, migration upgrade/check/downgrade/re-upgrade и focused SEARCH-001 suite. Требуются GitHub PostgreSQL/CI и Render revision/search smoke, поэтому статус пока **НУЖНА ПРОВЕРКА**.

## 10. INFRA-001 — ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА

`INFRA-001` теперь означает только реальную аренду и полевой тест VPS:

1. public IPv4 и временный TLS hostname;
2. доступность минимум из двух сетей РФ и одной сети РБ без VPN;
3. health/search/resume/security smoke;
4. outbound transport к Yandex AI и Reed;
5. latency/cost/SLA/backup assessment;
6. provider decision record.

До начала этого пакета Render остаётся staging/резервной площадкой, DNS/OAuth callback URL не переключаются.

## 11. Текущее функциональное состояние

- Главная/AI Career/resume builder работают.
- Search: Trudvsem, HH, Reed, conditional SuperJob.
- OAuth HH/SJ: текущий pre-MVP, tokens encrypted.
- Trudvsem cache остаётся PostgreSQL-backed; внешний worker и SYNC-002 подтверждены. SEARCH-001 candidate добавляет единый typed contract/canonical fields для всех источников без изменения UI.
- PDF parser эвристический, не LLM.
- Saved jobs пока localStorage.
- Own account/profile/real AI/match/letters/tracker впереди.

## 12. Новая обязательная очередь разработки

### Сейчас — функциональный MVP без аренды VPS

```text
SEARCH-001 verification -> SEARCH-002 -> SEARCH-003 -> SEARCH-004
-> AUTH-001 -> AUTH-002
-> PROF-001 -> PROF-002 -> PROF-003 -> PRIV-001
-> SEARCH-005
-> AI-BENCH-001 -> AI-PROVIDER-001 -> LEGAL-001
-> AI-001 -> AI-002 -> AI-003 -> AI-004 -> AI-005 -> AI-006
-> JOB-001 -> JOB-002 -> JOB-003/JOB-004
-> PERF/A11Y/ANL по готовности
```

`DOC-001` выполняется постоянно вместе с каждым package и не является отдельным blocker.

### Перед beta / production — инфраструктурный блок

```text
INFRA-001 -> REED-COMPAT-001 -> HOST-001
-> OPS-002 + production backup/restore drill
-> DOMAIN-001 -> MIG-001
-> final SEC/OPS smoke -> REL-001 -> commercial release
```

## 13. Зафиксированная hosting-independent стратегия

До предрелизного окна новый код не должен зависеть от конкретного hosting provider:

- configuration через `config.py` и environment variables;
- PostgreSQL через `DATABASE_URL`, schema только Alembic;
- WSGI `app:app`;
- публичные абсолютные URL через будущий `PUBLIC_BASE_URL`;
- provider/AI integrations через service/adapters и feature flags;
- worker/scheduler отделяется от web process в `SYNC-001`;
- health/readiness, Docker/Compose и probes остаются в CI.

Render не считается гарантированным production для РФ/РБ из-за подтверждённой сетевой недоступности из части сетей РФ, но остаётся пригодным staging/резервным контуром до `MIG-001`.

## 14. AI и Reed

- `AI-BENCH-001` можно выполнять без реального VPS: качество Yandex AI Studio/Alice AI проверяется на golden dataset, а transport с будущего source IP повторяется в `INFRA-001`.
- Бизнес-логика должна использовать независимый `AIProvider`; OpenAI не является обязательным baseline для РФ/РБ.
- API keys хранятся только на сервере.
- `REED-COMPAT-001` требует точного IP выбранного VPS и выполняется сразу после `INFRA-001`.
- Reed должен иметь feature flag и graceful degradation.

## 15. Следующий пакет

Текущий gate — SEARCH-001: GitHub Actions, PostgreSQL migration `20260808_0005`, Render `/health/ready` и multi-source search smoke. После подтверждения следующий кодовый пакет — SEARCH-002, cross-source deduplication поверх нового contract.

## 16. Правила рабочего чата

- Перед изменениями читать паспорт, PLAN_CURRENT и актуальный ZIP; работать по одному package ID.
- Не смешивать unrelated design/business changes.
- Не ставить ВЫПОЛНЕНО без критериев и доказательств.
- После пакета возвращать ZIP, PLAN_CURRENT DOCX/PDF/MD, паспорт и source audit без `.env`, secrets, databases, dumps, backups, virtualenv, caches и bytecode.
- Канонические и repository docs синхронизируются вместе с каждым code package.
- Для новых документов применять единый документный стандарт проекта.
