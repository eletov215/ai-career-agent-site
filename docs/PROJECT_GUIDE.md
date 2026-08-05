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
- OAuth `state` не отключается, проверяется до success/error callback и не отражается в URL/logs после callback.
- Credentials, tokens и arbitrary provider response bodies не выводятся в logs/health/public endpoints.
- Реальные API не вызываются из CI.
- Production schema меняет только Alembic.
- State-changing browser routes используют CSRF; machine endpoints требуют отдельный secret.
- Статус `ВЫПОЛНЕНО` ставится только после всех критериев пакета.

## 4. Текущая ветка

Для SEC-001:

```text
sec-001-security-baseline
```

Commit:

```text
security: add baseline request and session protections
```

Не очищать ветку. Сохранять `.github`, `.gitignore`, migrations и существующие docs.

## 5. Проверки перед push

```bash
python scripts/check_repository_hygiene.py
python -m compileall -q app.py config.py database.py security.py domain models repositories migrations services tests scripts
python scripts/manage_db.py upgrade
python -m alembic check
python -m pytest -ra
```

SEC-001 дополнительно проверяет:

- production не позволяет отключить secure cookie, CSRF, rate limits и security headers, требует `SameSite=Lax` и HTTPS OAuth callbacks;
- все template scripts используют CSP nonce;
- POST forms имеют CSRF token;
- inline event handlers отсутствуют;
- API/form POST без CSRF отклоняется, с token доходит до route validation;
- logout — POST only;
- diagnostics скрыты без header secret;
- public Trudvsem status не содержит raw error/internal run;
- rate limit выдаёт controlled 429;
- PDF page/text/body limits;
- university-logo resolver не следует на private redirect и проверяет image signature;
- startup modes и PostgreSQL integration остаются зелёными.

## 6. Security surfaces

### Browser

```text
aca_session
Secure + HttpOnly + SameSite=Lax
CSRF token
CSP nonce
route-specific rate limit
```

### Machine sync

```text
POST /sync/trudvsem
X-Sync-Secret
CSRF exempt only because it is not a browser form
```

### Diagnostics

```text
DEBUG_DIAGNOSTICS=1
DIAGNOSTICS_SECRET=<secret>
X-Diagnostics-Secret: <secret>
```

Без всех трёх условий `/debug/*` и `/trudvsem/status` возвращают 404. Public UI использует `/api/sources/trudvsem/status`.

## 7. Слои данных

```text
routes -> StorageServices/application services -> repositories -> models/database
```

- Routes получают persistence через `StorageServices` и не выполняют SQL.
- Repositories возвращают detached User/OAuth/Vacancy/Source/SyncRun records.
- `VacancyStore` нормализует payload, `VacancyRepository` выполняет query.
- Legacy `accounts`/`hh_accounts` не удаляются до отдельной cleanup migration.

## 8. Миграции и rollback

Команды:

```bash
python scripts/manage_db.py upgrade
python scripts/manage_db.py current
python scripts/manage_db.py check
```

SEC-001 не добавляет migration; `/health` должен остаться на:

```text
revision=20260804_0002
```

Rollback SEC-001 выполняется application commit/redeploy без изменения PostgreSQL. Downgrade production schema без backup запрещён.

## 9. Render, домен и VPS

Сейчас deploy — Render. `DOMAIN-001` остаётся отдельным пакетом этапа 6 после `SEC-001` и `OPS-001`.

Порядок:

```text
SEC-001 verification -> OPS-001 -> DOMAIN-001
```

При DOMAIN-001 нужно добавить коммерческий hostname в `TRUSTED_HOSTS`, обновить OAuth redirect URI и проверить secure cookie/CSRF/HSTS на новом HTTPS-домене.

## 10. После каждого пакета вернуть

- новый ZIP;
- список файлов/изменений;
- test/migration results;
- GitHub/Render checklist;
- limitations/rollback;
- PLAN_CURRENT DOCX/PDF/MD;
- паспорт при изменении архитектуры/статуса.
