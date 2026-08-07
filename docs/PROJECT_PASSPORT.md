# AI Career Agent — паспорт проекта

| Поле | Значение |
|---|---|
| Документ | PROJECT_PASSPORT |
| Версия паспорта | 2.15 |
| Дата | 07 августа 2026 |
| Статус | ДЕЙСТВУЮЩИЙ |
| Связанный план | `AI_Career_Agent_PLAN_CURRENT v1.4.1` |
| Основа кода | `ai-career-agent-site-main (4).zip` + SYNC-001 candidate; GitHub main после INFRA-PREP-001 merge |

> Контрольные статусы: FND-001/FND-002/DATA-001/DATA-002/SEC-001/OPS-001/INFRA-PREP-001 — **ВЫПОЛНЕНО**; DOC-001 — **В РАБОТЕ как постоянный процесс**; SYNC-001 — **НУЖНА ПРОВЕРКА НА GITHUB/RENDER**; SYNC-002 — следующий пакет после подтверждения; INFRA-001 — **ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА**.

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
migrations/                Alembic 0001 + 0002 + 0003 (external sync worker)
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

**Важно:** ранее незакрытый encrypted backup реальной production PostgreSQL + restore в отдельную test database не объявлен пройденным. В PLAN_CURRENT 1.4.0 он перенесён целиком в `OPS-002` и повторно проверяется в `REL-001`. Это release gate, а не текущий blocker функциональной разработки.

OPS-001 database migration отсутствовала. После SYNC-001 ожидаемая revision проекта — `20260807_0003`.

## 6. INFRA-PREP-001 — ВЫПОЛНЕНО

Кодовая часть прежнего INFRA-001 выделена в самостоятельный подготовительный пакет без изменения кода:

- non-root runtime/ops Docker images;
- Compose stack с private PostgreSQL, one-shot migrations, web, optional Caddy TLS и isolated restore DB;
- secret-free environment template;
- DNS/TCP/TLS/HTTP probes для app/Yandex AI/Reed и optional providers;
- manifest validation, Docker build и runtime smoke в GitHub Actions;
- VPS runbook и provider shortlist.

Это делает приложение переносимым на VPS без необходимости оплачивать ВМ во время разработки.

## 7. SYNC-001 — НУЖНА ПРОВЕРКА НА GITHUB/RENDER

Реализован hosting-independent внешний контур Trudvsem sync:

- Gunicorn/Flask больше не создаёт daemon thread и не выполняет provider HTTP;
- web routes только читают PostgreSQL cache и идемпотентно ставят durable job в `sync_runs`;
- `scripts/trudvsem_sync_worker.py` выполняет queue jobs отдельным OS process;
- `scripts/sync_trudvsem.py` поддерживает one-shot/queue CLI;
- PostgreSQL advisory lock и SQLite lockfile блокируют параллельный sync;
- `sync_workers` хранит heartbeat/liveness;
- migration `20260807_0003` закрывает legacy abandoned runs и добавляет one-active-run constraint;
- Render free staging использует `scripts/start_runtime.py`, а Docker Compose — отдельный `sync-worker` profile;
- provider timeout сохраняет старый cache и записывает контролируемый failed `SyncRun`.

До статуса ВЫПОЛНЕНО нужны зелёный GitHub CI и Render smoke: revision `20260807_0003`, worker heartbeat, queue `202` и переход persisted run до terminal status.

## 8. INFRA-001 — ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА

`INFRA-001` теперь означает только реальную аренду и полевой тест VPS:

1. public IPv4 и временный TLS hostname;
2. доступность минимум из двух сетей РФ и одной сети РБ без VPN;
3. health/search/resume/security smoke;
4. outbound transport к Yandex AI и Reed;
5. latency/cost/SLA/backup assessment;
6. provider decision record.

До начала этого пакета Render остаётся staging/резервной площадкой, DNS/OAuth callback URL не переключаются.

## 9. Текущее функциональное состояние

- Главная/AI Career/resume builder работают.
- Search: Trudvsem, HH, Reed, conditional SuperJob.
- OAuth HH/SJ: текущий pre-MVP, tokens encrypted.
- Trudvsem cache остаётся PostgreSQL-backed; daemon thread удалён, external worker candidate ожидает GitHub/Render verification.
- PDF parser эвристический, не LLM.
- Saved jobs пока localStorage.
- Own account/profile/real AI/match/letters/tracker впереди.

## 10. Новая обязательная очередь разработки

### Сейчас — функциональный MVP без аренды VPS

```text
SYNC-001 verification -> SYNC-002
-> SEARCH-001 -> SEARCH-002 -> SEARCH-003 -> SEARCH-004
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

## 11. Зафиксированная hosting-independent стратегия

До предрелизного окна новый код не должен зависеть от конкретного hosting provider:

- configuration через `config.py` и environment variables;
- PostgreSQL через `DATABASE_URL`, schema только Alembic;
- WSGI `app:app`;
- публичные абсолютные URL через будущий `PUBLIC_BASE_URL`;
- provider/AI integrations через service/adapters и feature flags;
- worker/scheduler отделяется от web process в `SYNC-001`;
- health/readiness, Docker/Compose и probes остаются в CI.

Render не считается гарантированным production для РФ/РБ из-за подтверждённой сетевой недоступности из части сетей РФ, но остаётся пригодным staging/резервным контуром до `MIG-001`.

## 12. AI и Reed

- `AI-BENCH-001` можно выполнять без реального VPS: качество Yandex AI Studio/Alice AI проверяется на golden dataset, а transport с будущего source IP повторяется в `INFRA-001`.
- Бизнес-логика должна использовать независимый `AIProvider`; OpenAI не является обязательным baseline для РФ/РБ.
- API keys хранятся только на сервере.
- `REED-COMPAT-001` требует точного IP выбранного VPS и выполняется сразу после `INFRA-001`.
- Reed должен иметь feature flag и graceful degradation.

## 13. Следующий пакет

Сначала завершается verification `SYNC-001`: GitHub Actions, Render migration `20260807_0003`, external worker heartbeat и queue-to-terminal-run smoke. После подтверждения следующий кодовый пакет — `SYNC-002`, который добавит полную incremental freshness/cleanup policy поверх созданного worker contract.

## 14. Правила рабочего чата

- Перед изменениями читать паспорт, PLAN_CURRENT и актуальный ZIP; работать по одному package ID.
- Не смешивать unrelated design/business changes.
- Не ставить ВЫПОЛНЕНО без критериев и доказательств.
- После пакета возвращать ZIP, PLAN_CURRENT DOCX/PDF/MD, паспорт и source audit без `.env`, secrets, databases, dumps, backups, virtualenv, caches и bytecode.
- Канонические и repository docs синхронизируются вместе с каждым code package.
- Для новых документов применять единый документный стандарт проекта.
