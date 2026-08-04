# AI Career Agent — руководство по работе с проектом

## 1. Источник истины

1. GitHub — основной источник актуального кода.
2. Если в текущем чате загружен более новый ZIP, он считается актуальным для этой задачи.
3. Канонический план — файл `AI_Career_Agent_PLAN_CURRENT` с наибольшей версией и датой.
4. Старые дубликаты плана и паспорта не должны оставаться одновременно активными источниками.

## 2. Обязательный цикл работы

```text
актуальный ZIP + PLAN_CURRENT
-> выбор одного пакета по ID
-> анализ зависимостей и рисков
-> изменения
-> compile/test/migration checks
-> новый ZIP
-> GitHub branch + Pull Request
-> зелёный CI
-> deploy и ручная проверка
-> обновление статуса и PLAN_CURRENT
```

Статус `ВЫПОЛНЕНО` ставится только после всех критериев конкретного пакета.

## 3. Неприкосновенные правила

- Главный файл — `app.py`.
- WSGI-приложение — `app:app`.
- Не создавать `app_fixed.py`.
- Не помещать `.env`, токены, базы, backups, `__pycache__`, `.pytest_cache` или virtualenv в ZIP/GitHub.
- Не отключать OAuth `state`.
- Не выводить credentials в логи и health.
- Не обращаться к реальным API из CI.
- Не объединять несвязанные пакеты без необходимости.

## 4. Работа с ветками

Для каждого пакета создаётся ветка, например:

```text
data-001-postgresql
```

Рекомендуемое сообщение:

```text
feat: add PostgreSQL persistence and migrations
```

Не очищать ветку и не удалять проект перед загрузкой. Для большого набора файлов использовать GitHub Desktop или git CLI. Скрытые служебные пути (`.github`, `.gitignore`) должны сохраниться.

## 5. Проверки перед push

```bash
python scripts/check_repository_hygiene.py
python -m compileall -q app.py config.py database.py models migrations services tests scripts
python scripts/manage_db.py upgrade
python -m alembic check
python -m pytest
```

Для `DATA-001` нужно дополнительно проверить, что `/health` не содержит connection URL или password.

## 6. Базы и миграции

- Схему production меняет только Alembic.
- `DATABASE_URL` хранится только в окружении.
- SQLite fallback разрешён локально и в тестах.
- Production должен использовать PostgreSQL после завершения `DATA-001`.
- Перед импортом или миграцией реальных данных создаётся backup.
- Alembic downgrade без backup не выполняется.

Команды:

```bash
python scripts/manage_db.py upgrade
python scripts/manage_db.py current
python scripts/manage_db.py check
```

## 7. Render и будущий VPS

Сейчас deploy выполняется на Render. Собственный домен обязателен перед коммерческим запуском. Архитектура должна оставаться платформонезависимой:

- подключение базы только через `DATABASE_URL`;
- логи в stdout/stderr;
- фоновые задачи отдельной командой;
- пользовательские файлы не на локальном ephemeral disk;
- secrets вне GitHub/image;
- один и тот же WSGI entrypoint на Render и VPS.

Переход на VPS выполняется отдельными пакетами `INFRA-001`, `HOST-001`, `OPS-002`, а не внутри продуктовых изменений.

## 8. После каждого пакета вернуть

- новый ZIP проекта;
- список изменённых файлов;
- тестовые результаты;
- инструкции GitHub/Render;
- известные ограничения;
- обновлённые `PLAN_CURRENT.docx`, `.pdf`, `.md`;
- обновлённый паспорт, если изменилось текущее состояние/архитектура.
