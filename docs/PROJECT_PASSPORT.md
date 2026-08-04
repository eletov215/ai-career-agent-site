# AI Career Agent - Паспорт проекта

**Версия паспорта:** 2.0  
**Дата:** 04 августа 2026  
**Статус:** ДЕЙСТВУЮЩИЙ  
**Связанный план:** `AI_Career_Agent_PLAN_CURRENT` v1.2.0  
**Актуальный рабочий пакет:** `DATA-001` - НУЖНА ПРОВЕРКА

## 1. Назначение

AI Career Agent - коммерческий веб-сервис карьерного сопровождения. Целевой пользовательский путь:

```text
аккаунт -> резюме -> подтверждённый карьерный профиль -> AI-анализ
-> поиск реальных вакансий -> объяснимый match -> письмо -> трекер откликов
```

Пользователь принимает окончательные решения самостоятельно. Автоматическая отправка откликов без явного подтверждения не является целевой функцией.

## 2. Источник истины

1. GitHub - главный источник актуального кода.
2. Более новый ZIP, загруженный в текущий чат, является рабочей основой задачи.
3. Канонический план - `AI_Career_Agent_PLAN_CURRENT` с наибольшей версией и датой.
4. После каждого пакета старые план и паспорт заменяются новыми; параллельные устаревшие версии удаляются из источников.
5. Главный файл - `app.py`; WSGI entrypoint - `app:app`; `app_fixed.py` не используется.

## 3. Технологии

- Python 3.11;
- Flask 3.1.3;
- Gunicorn;
- SQLAlchemy 2;
- Alembic;
- PostgreSQL через Psycopg 3;
- SQLite как local/test fallback;
- GitHub Actions;
- Render на текущем этапе;
- будущий собственный домен;
- возможный VPS после отдельного решения;
- OAuth HeadHunter и SuperJob;
- HeadHunter, Reed и Trudvsem API;
- pypdf, Cryptography/Fernet;
- HTML/CSS/JavaScript.

## 4. Структура

```text
app.py                         Flask routes и app:app
config.py                      конфигурация production/development/test
database.py                    SQLAlchemy runtime и health
models/                        текущие persistence models
migrations/                    Alembic revisions
services/                      providers, filters, parser, vacancy store
scripts/manage_db.py           migration/readiness commands
scripts/import_legacy_sqlite.py optional legacy import
tests/                         unit/provider/route/database tests
templates/                     HTML
static/                        CSS/JS/images
render.yaml                    текущий Render deploy
.github/workflows/ci.yml       CI
```

## 5. Подтверждённые пакеты

### FND-001 - ВЫПОЛНЕНО

- добавлены базовые tests и GitHub Actions;
- подтверждены зелёный CI, намеренно красный CI и повторный зелёный CI;
- подтверждена Render smoke-проверка.

### FND-002 - ВЫПОЛНЕНО

- добавлен `config.py` и `AppSettings`;
- разделены `production/development/test`;
- ранняя валидация окружения;
- `HH_CURRENCY_SCAN_PAGES` на Render исправлен на `20`;
- GitHub Actions и Render deploy подтверждены.

## 6. Текущий пакет DATA-001

### Реализовано в коде

- `DATABASE_URL`;
- SQLAlchemy engine/sessions;
- PostgreSQL/Psycopg 3;
- Alembic и migration `20260804_0001`;
- модели `accounts`, `hh_accounts`, `vacancies`;
- SQLAlchemy persistence в `app.py` и `VacancyStore`;
- `/health` с backend/persistence/revision без credentials;
- `manage_db.py` и legacy SQLite importer;
- CI migration checks, PostgreSQL 17 service container и реальный persistence round-trip.

### Статус

`НУЖНА ПРОВЕРКА` до выполнения всех пунктов:

- зелёный GitHub Actions;
- создан production PostgreSQL;
- `DATABASE_URL` использует internal URL;
- `/health` показывает `postgresql`, `persistent=true`, `revision=20260804_0001`;
- данные переживают restart/redeploy;
- основные маршруты и поиск работают.

## 7. Текущее функциональное состояние

- Публичная главная и AI Career pages - работают.
- Единый поиск - Trudvsem, HeadHunter, Reed, SuperJob после подключения.
- OAuth HH/SJ - реализован в текущем pre-MVP, токены шифруются.
- Trudvsem - локальный cache и background thread внутри web process.
- PDF resume parse - эвристический, не LLM.
- Resume builder - live preview, PDF export, mobile/tablet fixes.
- Saved jobs - localStorage only.
- Собственный User, server profile, real AI, match, letters и tracker - ещё не реализованы.

## 8. Критические риски и очередность

1. Завершить DATA-001 и исключить ephemeral SQLite production.
2. DATA-002 - доменные модели и repository layer.
3. SEC-001 - sessions/forms/endpoints/security headers/rate limits.
4. OPS-001 - monitoring/logging/backup restore.
5. DOMAIN-001 - собственный домен до коммерческой beta.
6. SYNC/SEARCH - worker, normalization, dedup, stable pagination.
7. AUTH/PROFILE.
8. AI/JOB/LEGAL/REL.

## 9. Домен и hosting

- Собственный домен обязателен к коммерческому запуску.
- Первая коммерческая beta рекомендуется на платном Render с собственным доменом и managed PostgreSQL.
- VPS не обязателен заранее. Решение принимается по реальным расходам, нагрузке, региону данных и операционной готовности.
- Код должен быть переносимым: `DATABASE_URL`, stdout logs, separate jobs, object storage, Docker/Compose на INFRA-001.
- При миграции домен остаётся прежним, меняется только DNS target.

## 10. Правила рабочего чата

- Перед изменениями изучить паспорт, PLAN_CURRENT и актуальный ZIP.
- Выбрать один пакет по ID.
- Не менять unrelated design/business logic.
- После работы перечислить файлы, изменения, tests, GitHub/production steps и limitations.
- Не ставить `ВЫПОЛНЕНО` без подтверждения критериев.
- Вернуть новый ZIP и обновлённые PLAN_CURRENT DOCX/PDF/MD.
- Не помещать secrets, `.env`, databases, backups, virtualenv и caches в архив.
