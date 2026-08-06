# AI Career Agent — паспорт проекта

**Версия паспорта:** 2.10  
**Дата:** 06 августа 2026  
**Статус:** ДЕЙСТВУЮЩИЙ  
**Связанный план:** `AI_Career_Agent_PLAN_CURRENT v1.3.2`  
**Основа кода:** `ai-career-agent-site-main-17-sec-001-rate-limit-fix-ops-001-v1.3.2.zip`

> Контрольные статусы: FND-001/FND-002/DATA-001/DATA-002 — ВЫПОЛНЕНО; SEC-001 — НУЖНА ПОВТОРНАЯ ПРОВЕРКА НА RENDER; OPS-001 — НУЖНА ПРОВЕРКА; INFRA-001, AI-BENCH-001, REED-COMPAT-001, AI-PROVIDER-001, HOST-001, DOMAIN-001 и MIG-001 — ЗАПЛАНИРОВАНО.

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

## 5. SEC-001 — НУЖНА ПОВТОРНАЯ ПРОВЕРКА НА RENDER

Реализованы secure `aca_session`, one-time OAuth state, global CSRF, route limits, trusted hosts, CSP/HSTS/browser headers, bounded uploads/PDF, POST-only logout, diagnostics gate, neutral errors и university-logo SSRF baseline. Production уже подтвердил headers, cookie, CSRF 400, health/revision, страницы, поиск, PDF, закрытые diagnostics и secret-free logs.

Обнаружено, что исходный `get_remote_address` формировал разные limiter buckets из меняющихся Render proxy addresses. В версии 1.3.2 добавлены валидируемый Cloudflare/Render client address, HMAC bucket key, отказ `ProxyFix` от переписывания `REMOTE_ADDR` и `/api/security/rate-limit-probe` (`5/minute`). Для завершения нужны зелёный CI и production `429` + `Retry-After`. Database revision не менялась: `20260804_0002`.

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

### Для завершения требуется

1. Зелёный GitHub Actions с OPS tests и PostgreSQL restore drill.
2. Render `/health/live` и `/health/ready` = 200.
3. Structured log с корреляцией и без секретов.
4. Доставленный sanitised test alert.
5. Encrypted backup во внешнем хранилище.
6. Restore в отдельную test database с совпадающими revision/table counts.

## 7. Текущее функциональное состояние

- Главная/AI Career/resume builder работают.
- Search: Trudvsem, HH, Reed, conditional SuperJob.
- OAuth HH/SJ: текущий pre-MVP, tokens encrypted.
- Trudvsem cache и daemon пока внутри web process.
- PDF parser эвристический, не LLM.
- Saved jobs пока localStorage.
- Own account/profile/real AI/match/letters/tracker впереди.

## 8. Критические риски и обязательная очередь

1. Подтвердить SEC-001 rate-limit fix: зелёный CI и `429` на `/api/security/rate-limit-probe`.
2. Подтвердить OPS-001: CI, alert, encrypted backup и restore drill.
3. `INFRA-001` — выбрать и протестировать российский VPS из сетей РФ/РБ.
4. `AI-BENCH-001` — проверить Yandex AI Studio/Alice AI.
5. `REED-COMPAT-001` — проверить Reed с точного source IP и условия использования.
6. `AI-PROVIDER-001` — зафиксировать AI-контур, privacy, стоимость и fallback.
7. `HOST-001` — подготовить production VPS.
8. `DOMAIN-001` — домен, TLS, PUBLIC_BASE_URL и OAuth callback URL.
9. `MIG-001` — перенос PostgreSQL/production с rollback.

## 9. Зафиксированная инфраструктурная стратегия

Render остаётся staging/резервной площадкой: из части сетей РФ DNS работает, но TCP 443 до edge IP не устанавливается и запросы не доходят до Render Logs; сайт доступен из Республики Беларусь и мобильных сетей.

```text
OPS-001 verification
-> INFRA-001 test VPS
-> AI-BENCH-001
-> REED-COMPAT-001
-> AI-PROVIDER-001
-> HOST-001
-> DOMAIN-001
-> MIG-001
```

Production-кандидат должен иметь постоянный IPv4, доступность из РФ/РБ, исходящий HTTPS к Yandex AI Studio и Reed, Docker/Compose, PostgreSQL, worker, firewall, offsite backup, monitoring и rollback.

## 10. AI и Reed

- Основной AI-кандидат: Yandex AI Studio/Alice AI после benchmark на нашем golden dataset.
- Бизнес-логика должна использовать независимый `AIProvider`; OpenAI не является обязательным baseline для РФ/РБ.
- API keys хранятся только на сервере.
- Reed требует real API smoke с выбранного VPS и письменного подтверждения условий.
- Reed обязан иметь feature flag и graceful degradation.

## 11. Правила рабочего чата

- Перед изменениями читать паспорт, PLAN_CURRENT и актуальный ZIP; работать по одному package ID и не смешивать unrelated design/business changes.
- Не ставить ВЫПОЛНЕНО без критериев; после пакета возвращать ZIP, PLAN_CURRENT DOCX/PDF/MD, паспорт и source audit без `.env`, secrets, databases, dumps, backups, virtualenv, caches и bytecode.
