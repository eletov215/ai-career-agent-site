# AI Career Agent — паспорт проекта

**Версия паспорта:** 2.6  
**Дата:** 05 августа 2026  
**Статус:** ДЕЙСТВУЮЩИЙ  
**Связанный план:** `AI_Career_Agent_PLAN_CURRENT v1.2.8`  
**Актуальный рабочий пакет:** `SEC-001 — НУЖНА ПРОВЕРКА`

> Контрольные статусы: FND-001 — ВЫПОЛНЕНО; FND-002 — ВЫПОЛНЕНО; DATA-001 — ВЫПОЛНЕНО; DATA-002 — ВЫПОЛНЕНО; SEC-001 — НУЖНА ПРОВЕРКА; OPS-001 — ЗАПЛАНИРОВАНО; DOMAIN-001 — ЗАПЛАНИРОВАНО, ЭТАП 6, ОБЯЗАТЕЛЕН ДО BETA.

## 1. Назначение

AI Career Agent — коммерческий веб-сервис карьерного сопровождения:

```text
аккаунт -> резюме -> подтверждённый профиль -> AI-анализ
-> реальные вакансии -> объяснимый match -> письмо -> tracker
```

Пользователь принимает окончательные решения самостоятельно.

## 2. Источник истины

1. GitHub — главный источник кода.
2. Более новый ZIP в текущем чате — рабочая основа задачи.
3. Канонический PLAN_CURRENT определяется версией/датой.
4. Старые план/паспорт удаляются после замены.
5. Главный файл `app.py`; WSGI `app:app`; `app_fixed.py` не используется.

## 3. Технологии

- Python 3.11, Flask 3.1.3, Gunicorn;
- SQLAlchemy 2, Alembic;
- PostgreSQL 17/Psycopg 3;
- SQLite local/test fallback;
- GitHub Actions;
- Flask-WTF 1.3 и Flask-Limiter 4.1;
- Render сейчас;
- собственный домен в `DOMAIN-001`;
- optional VPS после `HOST-001`;
- OAuth HH/SuperJob;
- HH, Reed, Trudvsem APIs;
- pypdf, Cryptography/Fernet;
- HTML/CSS/JavaScript.

## 4. Структура

```text
app.py                     Flask routes, app:app
config.py                  production/development/test
database.py                SQLAlchemy runtime/health
security.py                CSRF/rate limits/headers/request limits
domain/                    detached records
models/                    ORM domain schema
repositories/              persistence queries
migrations/                Alembic 0001 + 0002
services/storage.py         app persistence boundary
services/                  providers/application services
scripts/manage_db.py       migrations/readiness
scripts/import_legacy_sqlite.py
tests/
templates/
static/
render.yaml
.github/workflows/ci.yml
```

## 5. Подтверждённые пакеты

### FND-001 — ВЫПОЛНЕНО

Tests/CI и Render smoke подтверждены.

### FND-002 — ВЫПОЛНЕНО

Central config/APP_ENV, CI и Render подтверждены; `HH_CURRENCY_SCAN_PAGES=20`.

### DATA-001 — ВЫПОЛНЕНО

- PostgreSQL 17 в Oregon;
- `DATABASE_URL` Internal URL;
- Alembic `20260804_0001`;
- `/health` persistent=true;
- cache/state пережили restart.

## 6. DATA-002 — ВЫПОЛНЕНО

### Добавлено

- `User`;
- unified `OAuthConnection`;
- canonical `Vacancy`;
- `VacancySourceRecord`;
- `SyncRun`;
- domain records;
- repositories и `StorageServices`;
- migration `20260804_0002`;
- legacy OAuth/vacancy backfill;
- persisted Trudvsem run lifecycle;
- architecture-boundary tests.

### Совместимость

- Existing OAuth templates/session IDs сохраняются.
- Legacy account tables пока остаются и получают mirrored HH/SJ writes для rollback.
- Search/UI payload не меняется.
- Canonical/source vacancy model готовит SEARCH-002.
- app.py больше не знает SQLAlchemy, ORM или concrete repositories.

### Подтверждение выполнения

- GitHub Actions полностью зелёный, включая PostgreSQL migration/integration test и полный pytest;
- Render `/health` показывает PostgreSQL и revision `20260804_0002`;
- поиск вакансий работает без HTTP 500;
- `/trudvsem/status` содержит secret-free `persisted_run`;
- после restart сохранились `cached_total=23`, `current_offset=30`, `last_processed=30`, `last_saved=30`, `last_started` и persisted run;
- пользователь подтвердил штатную работу сайта после перезагрузки.

## 7. SEC-001 — НУЖНА ПРОВЕРКА

### Реализовано

- host-only `aca_session` с production Secure/HttpOnly/SameSite=Lax и ограниченным lifetime; Strict отклоняется из-за OAuth compatibility;
- one-time OAuth state с TTL 10 минут для success/error callbacks, HTTPS-only production redirect URI и session cleanup после успешного callback;
- global Flask-WTF CSRF, token в POST forms и JavaScript header;
- Flask-Limiter route limits и controlled 429;
- trusted hosts, one-proxy scheme/client handling, CSP nonce, HSTS и browser security headers;
- request/form/file/PDF page/text limits;
- POST-only logout;
- neutral 400/404/405/413/429/500 и sanitized OAuth/provider errors;
- diagnostics gate: `DEBUG_DIAGNOSTICS` + `DIAGNOSTICS_SECRET` + header;
- public secret-free `/api/sources/trudvsem/status`;
- production refresh hidden, sync protected by `X-Sync-Secret`;
- university-logo SSRF/redirect/response-size/MIME-signature baseline;
- security config/route/template/SSRF tests и отдельный CI step.

### Совместимость

- database migration отсутствует, ожидаемая revision остаётся `20260804_0002`;
- UI/design/search payload не меняются;
- существующие browser sessions один раз сбросятся из-за нового cookie name;
- diagnostics URLs, ранее открывавшиеся напрямую, теперь намеренно возвращают 404; public UI использует sanitised API;
- current rate-limit storage process-local и рассчитан на один worker.

### Для завершения требуется

- зелёный GitHub Actions без skip Flask route/startup tests;
- Render deploy и `/health` revision `20260804_0002`;
- smoke main/search/resume/OAuth;
- подтверждение cookie/CSRF/rate limit/CSP/HSTS;
- закрытые diagnostics и чистые logs.

## 8. Текущее функциональное состояние

- Главная/AI Career/resume builder — работают.
- Search — Trudvsem, HH, Reed, conditional SuperJob.
- OAuth HH/SJ — текущий pre-MVP, tokens encrypted.
- Trudvsem — cache + daemon внутри web process.
- PDF parser — эвристический, не LLM.
- Saved jobs — localStorage.
- Own account/profile/real AI/match/letters/tracker — впереди.

## 9. Критические риски и очередь

1. SEC-001 verification — GitHub/Render/security smoke.
2. OPS-001 — logs/monitoring/backup restore.
3. DOMAIN-001 — собственный домен до beta.
4. SYNC/SEARCH core.
5. AUTH/PROFILE.
6. AI/JOB/LEGAL/REL.

## 10. DOMAIN-001 — трассировка

Пакет не потерян и не интегрирован в DATA-002. Он существует отдельно в этапе 6 и выполняется после `SEC-001`/`OPS-001`:

```text
регистрация домена -> DNS -> TLS -> PUBLIC_BASE_URL
-> HH/SJ callbacks -> trusted hosts/cookie/CSRF origins
```

Сначала домен может указывать на Render; при переходе на VPS меняется DNS target.

## 11. Правила рабочего чата

- Читать паспорт, PLAN_CURRENT и актуальный ZIP.
- Один пакет по ID.
- Не смешивать unrelated design/business changes.
- Возвращать files/change list/tests/GitHub/production steps/limitations.
- Не ставить ВЫПОЛНЕНО без criteria.
- Возвращать ZIP + PLAN_CURRENT DOCX/PDF/MD.
- Не включать secrets/runtime artifacts.
