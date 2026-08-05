# AI Career Agent — паспорт проекта

**Версия паспорта:** 2.4  
**Дата:** 04 августа 2026  
**Статус:** ДЕЙСТВУЮЩИЙ  
**Связанный план:** `AI_Career_Agent_PLAN_CURRENT v1.2.6`  
**Актуальный рабочий пакет:** `DATA-002 — НУЖНА ПРОВЕРКА`

> Контрольные статусы: FND-001 — ВЫПОЛНЕНО; FND-002 — ВЫПОЛНЕНО; DATA-001 — ВЫПОЛНЕНО; DATA-002 — НУЖНА ПРОВЕРКА; DOMAIN-001 — ЗАПЛАНИРОВАНО, ЭТАП 6, ОБЯЗАТЕЛЕН ДО BETA. Следующий пакет после подтверждения — SEC-001.

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

## 6. DATA-002 — реализован, нужна проверка

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

### До статуса «ВЫПОЛНЕНО»

- зелёный GitHub Actions;
- PostgreSQL integration test не skipped;
- Render `/health` revision `20260804_0002`;
- OAuth/search smoke;
- restart persistence.

## 7. Текущее функциональное состояние

- Главная/AI Career/resume builder — работают.
- Search — Trudvsem, HH, Reed, conditional SuperJob.
- OAuth HH/SJ — текущий pre-MVP, tokens encrypted.
- Trudvsem — cache + daemon внутри web process.
- PDF parser — эвристический, не LLM.
- Saved jobs — localStorage.
- Own account/profile/real AI/match/letters/tracker — впереди.

## 8. Критические риски и очередь

1. DATA-002 verification.
2. SEC-001 — forms/sessions/endpoints/security headers/rate limits.
3. OPS-001 — logs/monitoring/backup restore.
4. DOMAIN-001 — собственный домен до beta.
5. SYNC/SEARCH core.
6. AUTH/PROFILE.
7. AI/JOB/LEGAL/REL.

## 9. DOMAIN-001 — трассировка

Пакет не потерян и не интегрирован в DATA-002. Он существует отдельно в этапе 6 и выполняется после `SEC-001`/`OPS-001`:

```text
регистрация домена -> DNS -> TLS -> PUBLIC_BASE_URL
-> HH/SJ callbacks -> trusted hosts/cookie/CSRF origins
```

Сначала домен может указывать на Render; при переходе на VPS меняется DNS target.

## 10. Правила рабочего чата

- Читать паспорт, PLAN_CURRENT и актуальный ZIP.
- Один пакет по ID.
- Не смешивать unrelated design/business changes.
- Возвращать files/change list/tests/GitHub/production steps/limitations.
- Не ставить ВЫПОЛНЕНО без criteria.
- Возвращать ZIP + PLAN_CURRENT DOCX/PDF/MD.
- Не включать secrets/runtime artifacts.
