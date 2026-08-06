# AI Career Agent - backup и восстановление PostgreSQL

**Пакет:** `OPS-001`  
**Схема:** Alembic `20260804_0002`  
**Правило:** backup не считается рабочим, пока restore не проверен на отдельной базе.

## 1. Формат

PostgreSQL backup создаётся стандартным `pg_dump --format=custom`, затем проверяется `pg_restore --list`. При заданном `BACKUP_ENCRYPTION_KEY` файл шифруется AES-256-GCM.

Рядом создаётся secret-free manifest:

- timestamp;
- backend/host/database без user/password;
- Alembic revision;
- controlled table counts;
- file size;
- SHA-256;
- encryption flag/cipher.

SQLite поддерживается только для local/test через online backup API.

## 2. Ключ шифрования

Создать отдельный ключ:

```bash
python - <<'PY'
import base64
import os
print(base64.urlsafe_b64encode(os.urandom(32)).decode())
PY
```

Сохранить как secret:

```text
BACKUP_ENCRYPTION_KEY=<value>
```

Не использовать `TOKEN_ENCRYPTION_KEY`. Потеря backup key делает encrypted backup невосстановимым. Хранить минимум две защищённые копии key вне сервера.

## 3. Требования

Для PostgreSQL нужны compatible client tools:

```text
pg_dump
pg_restore
```

При необходимости пути задаются:

```text
PG_DUMP_BIN=/path/to/pg_dump
PG_RESTORE_BIN=/path/to/pg_restore
```

Желательно использовать ту же major version client tools, что и PostgreSQL server, либо более новую совместимую версию.

## 4. Создание backup

```bash
APP_ENV=production \
DATABASE_URL='postgresql+psycopg://...' \
BACKUP_ENCRYPTION_KEY='...' \
BACKUP_DIR='/secure/backups' \
BACKUP_RETENTION_DAYS=14 \
python scripts/backup_database.py
```

Для deterministic automation:

```bash
python scripts/backup_database.py \
  --output-dir /secure/backups \
  --name ai-career-agent-20260805T120000Z.dump
```

Production backup без encryption блокируется. `--allow-unencrypted` допускается только для явно контролируемой аварийной процедуры и не должен использоваться в регулярном расписании.

## 5. Integrity verification

```bash
python scripts/verify_backup.py \
  --backup /secure/backups/<backup>.enc
```

Проверяются manifest, size и SHA-256. Это не заменяет restore drill.

## 6. Restore drill в отдельную базу

1. Создать пустую test database.
2. Не использовать production `DATABASE_URL` как target.
3. Выполнить:

```bash
APP_ENV=development \
RESTORE_DATABASE_URL='postgresql+psycopg://.../ai_career_agent_restore_test' \
BACKUP_ENCRYPTION_KEY='...' \
python scripts/restore_database.py \
  --backup /secure/backups/<backup>.enc
```

После restore скрипт сравнивает:

- Alembic revision;
- counts для `users`, `oauth_connections`, `vacancies`, `vacancy_source_records`, `sync_runs`, legacy OAuth tables.

Несовпадение завершает команду ошибкой.

## 7. Production restore

По умолчанию блокируется. Перед production restore:

1. Зафиксировать incident/maintenance window.
2. Остановить writes и background sync.
3. Сделать новый pre-restore backup.
4. Проверить target URL дважды.
5. Подтвердить rollback path.
6. Запустить только осознанно:

```bash
APP_ENV=production \
RESTORE_DATABASE_URL='postgresql+psycopg://...' \
BACKUP_ENCRYPTION_KEY='...' \
python scripts/restore_database.py \
  --backup /secure/backups/<backup>.enc \
  --allow-production \
  --clean
```

7. Выполнить `/health/ready`, smoke OAuth/search/resume и counts check.
8. Сохранить incident report.

## 8. Offsite policy

До commercial beta требуется:

- минимум ежедневный encrypted backup;
- хранение вне VPS;
- retention минимум 14 daily + 4 weekly copies;
- отдельное хранение encryption key;
- ежемесячный restore drill;
- alert при failed/missing backup;
- документированный RPO/RTO.

OPS-001 предоставляет инструменты и CI restore proof. Реальное offsite schedule на production-площадке подтверждается в HOST/OPS-002.

## 9. Запрещено

- добавлять `.dump`, `.backup`, `.sql`, `.sqlite3`, `.enc` или manifests в Git;
- передавать `DATABASE_URL` в CLI argument/log;
- публиковать backup key;
- считать cloud provider snapshot единственной копией;
- выполнять downgrade/restore единственной production DB без backup и rollback.

## 10. Compose restore drill INFRA-001

```bash
docker compose --env-file .env --profile restore-test up -d restore-db
docker compose --env-file .env --profile ops run --rm --no-deps \
  -e APP_ENV=production \
  -e DATABASE_URL="$RENDER_DATABASE_URL" \
  ops python scripts/backup_database.py \
  --output-dir /var/backups/ai-career-agent \
  --name render-production.dump

docker compose --env-file .env --profile ops run --rm --no-deps \
  ops python scripts/verify_backup.py \
  --backup /var/backups/ai-career-agent/render-production.dump.enc

docker compose --env-file .env --profile ops --profile restore-test run --rm \
  ops python scripts/restore_database.py \
  --backup /var/backups/ai-career-agent/render-production.dump.enc
```

Перед выполнением сверить `RESTORE_DATABASE_URL`, manifest, SHA-256 и целевую revision `20260804_0002`.
