# AI Career Agent — паспорт проекта

| Поле | Значение |
|---|---|
| Документ | PROJECT_PASSPORT |
| Версия паспорта | 2.13 |
| Дата | 06 августа 2026 |
| Статус | ДЕЙСТВУЮЩИЙ |
| Связанный план | `AI_Career_Agent_PLAN_CURRENT v1.3.5` |
| Основа кода | `ai-career-agent-site-main (3).zip` -> INFRA-001 candidate build v1.3.5 |

> Контрольные статусы: FND-001/FND-002/DATA-001/DATA-002/SEC-001 — ВЫПОЛНЕНО; OPS-001 — НУЖНА ПРОВЕРКА, остался только production backup/restore drill; INFRA-001 — НУЖНА ПРОВЕРКА НА VPS; AI-BENCH-001, REED-COMPAT-001, AI-PROVIDER-001, HOST-001, DOMAIN-001 и MIG-001 — ЗАПЛАНИРОВАНО.

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
- production VPS выбирается в `INFRA-001`;
- основной AI-кандидат — Yandex AI Studio/Alice AI после `AI-BENCH-001`.

```text
app.py                     Flask routes, app:app
config.py                  production/development/test/ops settings
database.py                SQLAlchemy runtime and DB health
security.py                CSRF/rate limits/headers/request limits
observability.py           structured logs/request IDs/metrics/alerts
operations/backup.py       encrypted backup/verified restore
Dockerfile / compose.yaml  runtime, ops, DB, migrations, restore-test
infra/                     Gunicorn, Caddy, VPS environment and runbooks
scripts/                    migrations, backup, restore, alert test
domain/ models/ repositories/ services/
migrations/                Alembic 0001 + 0002
tests/                     unit/integration/security/ops tests
docs/                      architecture, security and runbooks
render.yaml
.github/workflows/ci.yml
```

## 4. Подтверждённые пакеты

### FND-001 — ВЫПОЛНЕНО

Базовые tests/CI и Render smoke подтверждены.

### FND-002 — ВЫПОЛНЕНО

Central config/APP_ENV, CI и Render подтверждены; `HH_CURRENCY_SCAN_PAGES=20`.

### DATA-001 — ВЫПОЛНЕНО

PostgreSQL 17, `DATABASE_URL`, Alembic `20260804_0001`, restart persistence подтверждены.

### DATA-002 — ВЫПОЛНЕНО

User/OAuthConnection/canonical Vacancy/VacancySourceRecord/SyncRun, repositories, StorageServices и migration `20260804_0002` подтверждены в CI и Render; cache/persisted run пережили restart.

## 5. SEC-001 — ВЫПОЛНЕНО

Реализованы secure `aca_session`, one-time OAuth state, global CSRF, route limits, trusted hosts, CSP/HSTS/browser headers, bounded uploads/PDF, POST-only logout, diagnostics gate, neutral errors и university-logo SSRF baseline. Production уже подтвердил headers, cookie, CSRF 400, health/revision, страницы, поиск, PDF, закрытые diagnostics и secret-free logs.

Обнаруженная нестабильность limiter buckets за Cloudflare/Render исправлена валидируемым client address и HMAC bucket key. Production-тест подтвердил ожидаемое поведение: первые 20 запросов к закрытому diagnostic route вернули `404`, двадцать первый — `429` с `Retry-After=295`. Также подтверждены headers, secure cookie, CSRF `400`, health/revision, страницы, поиск, PDF, закрытые diagnostics, безопасный Trudvsem status и secret-free application logs. Database revision не менялась: `20260804_0002`.

## 6. OPS-001 — НУЖНА ПРОВЕРКА

### Реализовано

- production JSON logs в stdout и text logs локально;
- `X-Request-ID` на каждом запросе и в logs/alerts;
- redaction configured secrets, Authorization/Cookie, tokens, passwords, URL credentials и query strings;
- bounded HTTP/provider metrics с p50/p95;
- `/health/live`, `/health/ready` и совместимый `/health`;
- diagnostics-only `/ops/status` и `POST /ops/alerts/test`;
- optional HTTPS alert webhook, не блокирующий приложение;
- PostgreSQL custom-format `pg_dump`/`pg_restore`;
- SQLite online backup для local/test;
- AES-256-GCM backup encryption независимым `BACKUP_ENCRYPTION_KEY`;
- secret-free manifest с revision, table counts, size и SHA-256;
- checksum/decrypt/revision/count verification и production restore guard;
- runbooks `OPERATIONS`, `BACKUP_RESTORE`, `INCIDENT_RESPONSE`;
- отдельные CI steps для observability и реального encrypted PostgreSQL backup/restore.

### Влияние

Интерфейс не меняется. Ответы получают `X-Request-ID`; liveness отделён от readiness. Логи не должны содержать query/body/cookies/tokens/resume text. Backup хранится вне web filesystem. Database migration отсутствует; revision остаётся `20260804_0002`.

### Подтверждено 06 августа 2026

- `/health/live`, `/health/ready` и `/health` возвращают `200`; PostgreSQL `ok=true`, current/expected revision `20260804_0002`.
- Переданный `X-Request-ID` совпадает в заголовке ответа и JSON.
- Тот же `X-Request-ID` найден в structured application JSON log: `route=/api/sources/trudvsem/status`, `method=GET`, `status_code=200`, присутствует `duration_ms`; query/body/cookies/tokens в записи отсутствуют.
- `/ops/status` без секрета возвращает `404`, с diagnostics secret — `200`.
- Telemetry показывает HTTP endpoints, provider `trudvsem`, recent errors `0`.
- Webhook alert подтверждён end-to-end: endpoint вернул `202 queued`, Webhook.site получил `POST application/json` от `AI-Career-Agent-Ops/1.0` с sanitised event `ops_test_alert`, `service`, `environment`, `version`, `level`, `message` и `request_id`; секреты отсутствуют.
- GitHub Actions после merge полностью зелёный, включая `Verify OPS-001 observability controls`, `Verify PostgreSQL encrypted backup and restore` и `Run tests`.
- После redeploy uptime сбросился, а `cached_total=77` сохранился; health/readiness остались зелёными.

### Для завершения требуется

1. Создать encrypted backup реальной production PostgreSQL вне web filesystem и проверить manifest/SHA-256.
2. Restore выполнить в отдельную test database с совпадающими revision/table counts.
3. После проверки удалить временный Webhook.site URL, отключить `DEBUG_DIAGNOSTICS` и удалить временный diagnostics secret; `/ops/status` снова должен возвращать `404`.

## 7. INFRA-001 — НУЖНА ПРОВЕРКА НА VPS

### Реализовано

- non-root Docker runtime image с healthcheck;
- отдельный OPS image с PostgreSQL 17 `pg_dump`/`pg_restore`;
- Compose stack: private PostgreSQL, one-shot migrations, web, optional Caddy TLS, isolated restore-test database;
- единый Gunicorn config с одним worker до Redis/SYNC-001;
- secret-free `.env.example` и private backend network;
- DNS/TCP/TLS/HTTP probe приложения, Yandex AI, Reed, HH, Trudvsem и SuperJob;
- JSON/Markdown probe reports без query strings и credentials;
- manifest validator, unit tests, Docker build и runtime smoke в CI;
- provider shortlist: Timeweb Cloud first test, Yandex Cloud/Beget/Selectel alternatives;
- VPS runbook, который одновременно завершает production backup/restore OPS-001.

### Не меняется

- UI и business routes;
- PostgreSQL schema и Alembic revision `20260804_0002`;
- Render остаётся production/staging до MIG-001;
- DNS и OAuth callback URL не переключаются.

### Для завершения требуется

1. Реальный VPS 2 vCPU / 4 GB / 40 GB с public IPv4.
2. Test deploy и TLS hostname.
3. Доступность без VPN из контрольных сетей РФ/РБ.
4. Yandex AI и Reed transport probes.
5. Search/PDF/security smoke.
6. Encrypted Render production backup и restore в isolated database.
7. Фактический provider decision record.

## 8. Текущее функциональное состояние

- Главная/AI Career/resume builder работают.
- Search: Trudvsem, HH, Reed, conditional SuperJob.
- OAuth HH/SJ: текущий pre-MVP, tokens encrypted.
- Trudvsem cache и daemon пока внутри web process.
- PDF parser эвристический, не LLM.
- Saved jobs пока localStorage.
- Own account/profile/real AI/match/letters/tracker впереди.

## 9. Критические риски и обязательная очередь

1. Создать реальный VPS и подтвердить INFRA-001 из сетей РФ/РБ.
2. На этом VPS завершить OPS-001: encrypted backup реальной Render PostgreSQL и restore drill в isolated test database.
3. `AI-BENCH-001` — проверить Yandex AI Studio/Alice AI.
4. `REED-COMPAT-001` — проверить Reed с точного source IP и условия использования.
5. `AI-PROVIDER-001` — зафиксировать AI-контур, privacy, стоимость и fallback.
6. `HOST-001` — подготовить production VPS.
7. `DOMAIN-001` — домен, TLS, PUBLIC_BASE_URL и OAuth callback URL.
8. `MIG-001` — перенос PostgreSQL/production с rollback.

## 10. Зафиксированная инфраструктурная стратегия

Render остаётся staging/резервной площадкой: из части сетей РФ DNS работает, но TCP 443 до edge IP не устанавливается и запросы не доходят до Render Logs; сайт доступен из Республики Беларусь и мобильных сетей.

```text
OPS-001 production restore + INFRA-001 real VPS verification
-> AI-BENCH-001
-> REED-COMPAT-001
-> AI-PROVIDER-001
-> HOST-001
-> DOMAIN-001
-> MIG-001
```

Production-кандидат должен иметь постоянный IPv4, доступность из РФ/РБ, исходящий HTTPS к Yandex AI Studio и Reed, Docker/Compose, PostgreSQL, worker, firewall, offsite backup, monitoring и rollback.

## 11. AI и Reed

- Основной AI-кандидат: Yandex AI Studio/Alice AI после benchmark на нашем golden dataset.
- Бизнес-логика должна использовать независимый `AIProvider`; OpenAI не является обязательным baseline для РФ/РБ.
- API keys хранятся только на сервере.
- Reed требует real API smoke с выбранного VPS и письменного подтверждения условий.
- Reed обязан иметь feature flag и graceful degradation.

## 12. Правила рабочего чата

- Перед изменениями читать паспорт, PLAN_CURRENT и актуальный ZIP; работать по одному package ID и не смешивать unrelated design/business changes.
- Не ставить ВЫПОЛНЕНО без критериев; после пакета возвращать ZIP, PLAN_CURRENT DOCX/PDF/MD, паспорт и source audit без `.env`, secrets, databases, dumps, backups, virtualenv, caches и bytecode.
- Для OPS-001 считать подтверждёнными GitHub OPS/backup steps, request ID correlation, webhook delivery и redeploy persistence; production backup/restore выполняется внутри INFRA-001 VPS test. Для новых документов применять `docs/DOCUMENT_STANDARD.md`.
