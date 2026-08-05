# AI Career Agent — руководство по работе с проектом

## 1. Источник истины

1. GitHub — основной источник актуального кода.
2. Более новый ZIP в текущем чате является рабочей основой задачи.
3. Канонический план — `AI_Career_Agent_PLAN_CURRENT` с наибольшей версией и датой.
4. Старые дубликаты плана/паспорта удаляются после каждого пакета.

## 2. Обязательный цикл

```text
актуальный ZIP + PLAN_CURRENT
-> один пакет по ID
-> inventory/risks/rollback
-> изменения
-> compile/tests/migrations
-> ZIP + branch + PR
-> зелёный CI
-> deploy/manual verification
-> status/docs update
```

## 3. Неприкосновенные правила

- Главный файл — `app.py`; WSGI — `app:app`.
- `app_fixed.py` не создаётся.
- `.env`, credentials, databases, backups, virtualenv, caches и bytecode не попадают в ZIP/GitHub.
- OAuth `state` не отключается.
- Credentials не выводятся в logs/health.
- Реальные API не вызываются из CI.
- Production schema меняет только Alembic.
- Статус `ВЫПОЛНЕНО` ставится только после всех критериев пакета.

## 4. Ветки

Для DATA-002:

```text
data-002-domain-repositories
```

Commit:

```text
refactor: add domain model and repository layer
```

Не очищать ветку. Сохранять `.github`, `.gitignore` и migrations.

## 5. Проверки перед push

```bash
python scripts/check_repository_hygiene.py
python -m compileall -q app.py config.py database.py domain models repositories migrations services tests scripts
python scripts/manage_db.py upgrade
python -m alembic check
python -m pytest -ra
```

DATA-002 дополнительно проверяет:

- migration `20260804_0002`;
- legacy OAuth copy;
- canonical/source vacancy backfill;
- repository relationships/constraints;
- отсутствие SQLAlchemy/ORM/concrete repository imports в `app.py`;
- seeded legacy PostgreSQL migration, sequence continuity и reconnect persistence в GitHub Actions.

## 6. Слои данных

```text
routes -> StorageServices/application services -> repositories -> models/database
```

- Routes получают persistence через `StorageServices` и не выполняют SQL.
- Repositories возвращают detached User/OAuth/Vacancy/Source/SyncRun records.
- `VacancyStore` нормализует payload, `VacancyRepository` выполняет query.
- Legacy `accounts`/`hh_accounts` не удаляются до отдельной cleanup migration; HH/SJ writes временно зеркалируются для rollback.

## 7. Миграции и rollback

Команды:

```bash
python scripts/manage_db.py upgrade
python scripts/manage_db.py current
python scripts/manage_db.py check
```

После DATA-002 deploy `/health` должен показать:

```text
revision=20260804_0002
```

Downgrade production без backup запрещён. Для rollback предпочтительны clone/restore PostgreSQL и переключение `DATABASE_URL`.

## 8. Render, домен и VPS

Сейчас deploy — Render. `DOMAIN-001` не потерян: это отдельный пакет этапа 6 после `SEC-001` и `OPS-001`.

Порядок:

```text
DATA-002 -> SEC-001 -> OPS-001 -> DOMAIN-001
```

Домен сначала может указывать на Render. VPS выполняется позже через `INFRA-001`, `HOST-001`, `OPS-002`.

## 9. После каждого пакета вернуть

- новый ZIP;
- список файлов/изменений;
- test/migration results;
- GitHub/Render checklist;
- limitations/rollback;
- PLAN_CURRENT DOCX/PDF/MD;
- паспорт при изменении архитектуры/статуса.
