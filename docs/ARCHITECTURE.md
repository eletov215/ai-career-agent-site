# AI Career Agent — архитектура проекта

> Последнее обновление: 04 августа 2026 года  
> Текущий пакет: `DATA-001` — PostgreSQL и миграции  
> Статус пакета: **НУЖНА ПРОВЕРКА**

## 1. Цель архитектуры

Приложение должно поддерживать полный путь:

```text
аккаунт -> карьерный профиль -> анализ резюме -> поиск вакансий
-> объяснимое совпадение -> письмо -> трекер откликов
```

Инфраструктура не должна быть жёстко привязана к Render. До первой коммерческой beta рекомендуемая production-схема — платный Render + собственный домен + PostgreSQL. В дальнейшем тот же код должен переноситься на VPS без изменения бизнес-логики.

## 2. Технологический стек

- Python 3.11;
- Flask 3.1.3;
- Gunicorn;
- SQLAlchemy 2;
- Alembic;
- PostgreSQL через Psycopg 3;
- SQLite как локальный/test fallback;
- Requests, Cryptography/Fernet, pypdf;
- HTML, CSS, JavaScript;
- GitHub Actions;
- Render на текущем этапе;
- OAuth HeadHunter и SuperJob;
- API HeadHunter, Reed и Trudvsem.

## 3. Структура

```text
project/
├── app.py                       # Flask routes и WSGI app:app
├── config.py                    # единое чтение/валидация окружения
├── database.py                  # engine, sessions, health, Alembic helpers
├── models/
│   ├── base.py
│   ├── accounts.py
│   └── vacancy.py
├── migrations/
│   ├── env.py
│   └── versions/20260804_0001_initial_schema.py
├── alembic.ini
├── services/
│   ├── vacancy_store.py         # SQLAlchemy cache API
│   └── *_provider.py
├── scripts/
│   ├── manage_db.py
│   ├── import_legacy_sqlite.py
│   └── check_repository_hygiene.py
├── tests/
├── templates/
├── static/
├── render.yaml
└── .github/workflows/ci.yml
```

Главный рабочий файл — `app.py`. Файл `app_fixed.py` не создаётся.

## 4. Конфигурационный слой

`config.py` является единственным местом прямого чтения переменных окружения. `AppSettings` содержит:

- режим `production/development/test`;
- OAuth и encryption-настройки;
- параметры провайдеров и синхронизации;
- `DATA_DIR`;
- нормализованный `DATABASE_URL`;
- флаг, был ли `DATABASE_URL` задан явно.

Секретные значения не выводятся в ошибки, health endpoint или миграционные команды.

## 5. Слой базы данных

### 5.1 `database.py`

Создаёт единый `DatabaseRuntime`:

```text
SQLAlchemy Engine
+ sessionmaker
+ backend metadata
+ secret-free health
```

Для PostgreSQL включены `pool_pre_ping`, ограниченный pool и таймаут подключения. Для SQLite включены foreign keys, busy timeout и WAL; соединения не удерживаются пулом.

### 5.2 Выбор backend

```text
DATABASE_URL задан и указывает PostgreSQL
    -> production PostgreSQL

DATABASE_URL не задан
    -> SQLite <DATA_DIR>/app.db (совместимость/local/test)
```

Production считается переведённым на постоянную базу только тогда, когда `/health` возвращает:

```text
backend=postgresql
persistent=true
configured=true
revision=20260804_0001
```

### 5.3 Модели текущего pre-MVP

- `SuperJobAccount` -> таблица `accounts`;
- `HeadHunterAccount` -> таблица `hh_accounts`;
- `Vacancy` -> таблица `vacancies`.

Эти модели отражают уже существующие таблицы и не являются окончательной доменной моделью. Пакет `DATA-002` добавит `User`, `OAuthConnection`, `SyncRun` и репозитории.

## 6. Миграции

Alembic является единственным production-механизмом изменения схемы.

Первая миграция `20260804_0001`:

- создаёт текущие три таблицы в чистой базе;
- создаёт индексы вакансий;
- может принять существующую SQLite-схему без удаления строк;
- добавляет отсутствующее поле `experience`;
- нормализует `search_text`, `experience` и `published_at` старых вакансий;
- записывает Alembic revision.

`Base.metadata.create_all()` разрешён только в изолированных unit-тестах, но не заменяет Alembic в production.

## 7. Работа приложения с данными

### 7.1 OAuth

`app.py` использует SQLAlchemy Session для сохранения HeadHunter и SuperJob account rows. Токены остаются зашифрованы Fernet. Для чтения используется SQLAlchemy mapping, чтобы сохранить совместимость с текущими функциями `row["field"]`.

### 7.2 Вакансии

`VacancyStore` сохраняет прежний публичный API, но выполняет операции через SQLAlchemy. Он поддерживает SQLite и PostgreSQL и не читает окружение самостоятельно.

Нормализация, межисточниковая дедупликация и общая пагинация остаются отдельными пакетами `SEARCH-001..003`.

## 8. Health endpoint

`GET /health` проверяет реальное соединение и Alembic revision. Ответ не содержит host, username, password или полный URL.

HTTP-коды:

- `200` — база отвечает;
- `503` — база недоступна.

## 9. Deploy

Текущий бесплатный Render запускает:

```bash
python scripts/manage_db.py upgrade && gunicorn app:app
```

Это обеспечивает миграцию перед запуском worker. После перехода на платный Render или VPS миграции должны выполняться отдельной одноразовой pre-deploy/entrypoint-командой, а web-процесс — только `gunicorn app:app`.

## 10. Миграция данных

Существующая база Render могла находиться во временной файловой системе. Поэтому возможны два сценария:

1. **Новый PostgreSQL без переноса** — вакансии заново синхронизируются; HH/SuperJob подключаются заново.
2. **Импорт сохранённого `app.db`** — `scripts/import_legacy_sqlite.py`; нужен тот же `TOKEN_ENCRYPTION_KEY`.

Импорт не выполняется автоматически: источник должен быть явно указан, а перед production-операцией требуется backup и test run.

## 11. Тестирование

CI проверяет:

- импорт production-зависимостей;
- чистоту репозитория;
- Python compilation;
- повторяемую Alembic migration;
- отсутствие незаписанных schema changes (`alembic check`);
- SQLite compatibility;
- принятие legacy schema;
- legacy importer;
- Flask routes, конфигурацию, провайдеры, фильтры и парсер.

Неподменённые внешние HTTP-запросы в тестах запрещены.

## 12. Следующая архитектурная точка

После подтверждения `DATA-001` выполняется `DATA-002`:

- доменные модели `User`, `OAuthConnection`, `Vacancy`, `SyncRun`;
- repository/service layer;
- удаление raw SQL/SQLAlchemy details из routes;
- подготовка аккаунта, профиля и worker-процессов.
