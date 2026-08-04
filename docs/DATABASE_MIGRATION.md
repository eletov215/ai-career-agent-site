# DATA-001 — инструкция перехода на PostgreSQL

## 1. Цель

Перевести production с временного SQLite-файла на постоянный PostgreSQL, сохранив локальный/test SQLite и возможность отката приложения.

## 2. До начала

Подтвердить:

- GitHub Actions зелёный;
- текущий commit находится в отдельной ветке;
- `TOKEN_ENCRYPTION_KEY` сохранён;
- значение `HH_CURRENCY_SCAN_PAGES` равно `1..20`;
- известен статус текущих HH/SuperJob подключений;
- при необходимости старый `app.db` сохранён локально.

## 2.1 Что проверяет CI

GitHub Actions поднимает одноразовый PostgreSQL 17 service container и проверяет:

- применение Alembic migration к реальному PostgreSQL через Psycopg 3;
- повторяемость migration и `alembic check`;
- сохранение OAuth account rows и vacancy row после закрытия и повторного создания SQLAlchemy engine;
- отсутствие реальных внешних API-вызовов.

Эта проверка снижает риск несовместимости SQLite/PostgreSQL, но не заменяет production persistence test на Render.

## 3. Создание PostgreSQL на Render

1. Создать PostgreSQL в том же регионе, что и web service.
2. Не публиковать credentials в GitHub, issue, screenshot или чат.
3. Скопировать **Internal Database URL**.
4. В web service открыть `Environment`.
5. Добавить/заменить `DATABASE_URL`.
6. Не менять `TOKEN_ENCRYPTION_KEY`.

## 4. Deploy

Start command текущего пакета:

```bash
python scripts/manage_db.py upgrade && gunicorn app:app
```

В логах должна появиться строка без credentials:

```text
Database ready: backend=postgresql, persistent=True, configured=True, revision=20260804_0001
```

Ошибки соединения, миграции или конфигурации должны прервать deploy до запуска нового web worker.

## 5. Проверка

### 5.1 Health

Открыть `/health` и подтвердить:

```text
status = ok
database.ok = true
database.backend = postgresql
database.persistent = true
database.configured = true
database.revision = 20260804_0001
```

### 5.2 Smoke

Проверить:

```text
/
/privacy
/ai-career
/resume-builder
/vacancies
/vacancies/internal
/dashboard
```

Проверить поиск минимум через один доступный источник и отсутствие HTTP 500.

### 5.3 Персистентность

1. Сохранить тестовую запись штатной функцией приложения либо дождаться синхронизации вакансий.
2. Выполнить manual redeploy/restart.
3. Убедиться, что запись осталась.
4. Проверить повторный запуск миграции — он должен быть безопасным.

## 6. Старые данные

### Вариант A — начать с чистой базы

- вакансии будут восстановлены синхронизацией;
- пользователи заново подключат HeadHunter/SuperJob;
- это безопасный вариант, если достоверного снимка SQLite нет.

### Вариант B — импортировать снимок

```bash
DATABASE_URL='postgresql+psycopg://...' \
python scripts/import_legacy_sqlite.py --source /secure/path/app.db
```

Требования:

- source file не хранится в репозитории;
- `TOKEN_ENCRYPTION_KEY` совпадает со старым;
- сначала выполнить импорт в тестовый PostgreSQL;
- после импорта проверить количество account/vacancy rows;
- удалить временную копию из небезопасных мест.

## 7. Откат

### Откат кода

Вернуть предыдущий стабильный commit и выполнить deploy. PostgreSQL не удалять — он остаётся источником данных для повторной попытки.

### Откат данных

Не запускать Alembic downgrade без backup. Для критического сбоя восстановить PostgreSQL из проверенной резервной копии или создать новую базу и переключить `DATABASE_URL`.

### Временный fallback

Удаление `DATABASE_URL` вернёт приложение к SQLite fallback. Это допустимо только для диагностики, но не считается production-решением и может привести к потере новых данных при следующем redeploy.

## 8. Критерии «ВЫПОЛНЕНО»

- GitHub Actions зелёный;
- production `/health` сообщает PostgreSQL и revision `20260804_0001`;
- основные маршруты работают;
- миграция повторяется без ошибки;
- данные переживают restart/redeploy;
- rollback описан и понятен;
- план и CHANGELOG обновлены.
