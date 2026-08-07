# INFRA-PREP-001 — контейнерная упаковка и комплект будущего VPS-теста

| Поле | Значение |
|---|---|
| Пакет | INFRA-PREP-001 |
| Версия реализации | 1.1 |
| Дата | 07 августа 2026 |
| Статус | ВЫПОЛНЕНО; real INFRA-001 отложен |
| Основа кода | GitHub main после INFRA-PREP merge + SYNC-001 candidate |
| Связанный план | PLAN_CURRENT 1.4.1 |

> Кодовая часть классифицирована как выполненный `INFRA-PREP-001`. Реальная аренда и полевая проверка VPS остаются отдельным отложенным `INFRA-001` перед beta.

## 1. Цель

Подготовить одинаковый, воспроизводимый и безопасный запуск AI Career Agent на локальной машине, GitHub Actions и тестовом VPS. Одновременно пакет создаёт инструменты, с помощью которых можно объективно сравнить провайдеров и завершить production backup/restore drill пакета OPS-001.

## 2. Архитектура тестового стенда

```text
Internet
   |
   v
Caddy (optional TLS profile)
   |
   v
Gunicorn / Flask web container
   |
   +---- internal Docker network ---- PostgreSQL 17
   |
External sync-worker service (profile: sync)
   |
   +---- external HTTPS ------------ Yandex AI Studio / Reed / HH / Trudvsem

One-shot migration container
OPS container with PostgreSQL 17 client tools
Isolated restore-test PostgreSQL container
```

## 3. Реализованные компоненты

| Компонент | Назначение |
|---|---|
| `Dockerfile` target `runtime` | Non-root web image с healthcheck |
| `Dockerfile` target `ops` | Отдельный non-root image с `pg_dump`/`pg_restore` PostgreSQL 17 |
| `compose.yaml` | PostgreSQL, one-shot migrations, web, optional Caddy, OPS и restore-test profiles |
| `.dockerignore` | Исключает secrets, runtime data, backups, docs и tests из runtime image |
| `infra/gunicorn.conf.py` | Единая конфигурация Gunicorn для container/VPS |
| `infra/vps/.env.example` | Полный, но secret-free шаблон VPS environment |
| `infra/vps/Caddyfile` | Reverse proxy и автоматический TLS для временного тестового hostname |
| `scripts/infra_probe.py` | DNS/TCP/TLS/HTTP probe приложения, Yandex AI, Reed и providers |
| `scripts/infra_manifest_check.py` | Проверка Docker/Compose/security invariants |
| `scripts/infra_container_smoke.sh` | Автоматизированный локальный container smoke |
| `tests/test_infra_probe.py` | Unit tests probe/report logic |
| `tests/test_infra_manifests.py` | Regression tests Docker/Compose manifests |
| CI steps INFRA-001 | Manifest validation, build runtime/ops images и runtime health smoke |

## 4. Ключевые решения безопасности

| Решение | Причина |
|---|---|
| Web container работает под UID/GID 10001 | Исключить root runtime |
| PostgreSQL не публикует host port | База доступна только во внутренней сети Compose |
| Backend network имеет `internal: true` | Ограничить случайный доступ к DB/OPS services |
| Migrations выполняются отдельным one-shot service | Не запускать конкурирующие миграции каждым worker |
| Один Gunicorn worker | Сохранить корректность process-local limiter и embedded Trudvsem state до SYNC-001 |
| `TRUDVSEM_SYNC_ENABLED=0` по умолчанию на тестовом VPS | Не дублировать фоновые потоки |
| OPS image содержит client tools версии PostgreSQL 17 | Исключить несовместимый older `pg_dump` |
| Secrets передаются только через untracked `.env` | Не запекать credentials в image или GitHub |
| Probe очищает URL query/userinfo | Отчёты не раскрывают поисковые запросы или credentials |

## 5. Влияние на сайт

Внешний интерфейс и пользовательские маршруты не изменены. После успешного VPS deploy сайт должен выглядеть и работать так же, как на Render. Изменяется только способ упаковки, запуска и диагностики.

## 6. Что намеренно не входит

- Выбор окончательного production-провайдера без реального теста.
- Перенос production PostgreSQL с Render.
- Подключение коммерческого домена.
- Полная server hardening, SSH policy и patch management - это HOST-001/OPS-002.
- Вынос Trudvsem в отдельный worker - это SYNC-001.
- Redis для shared rate limiting - добавляется перед несколькими workers/instances.

## 7. Локальные и CI-проверки

| Проверка | Фактический результат | Где подтверждается |
|---|---|---|
| Repository hygiene | ПРОЙДЕНО | Локально |
| Python compileall | ПРОЙДЕНО | Локально |
| Full pytest | `103 passed, 6 skipped` | Локально; skips только Flask/Psycopg/PostgreSQL environment |
| INFRA unit/manifest tests | `12 passed` | Локально |
| SQLite migrations | Revision `20260807_0003` | Локально |
| Alembic check | No new upgrade operations | Локально |
| `infra_manifest_check.py` | `ok: true` | Локально |
| CI YAML / shell syntax | ПРОЙДЕНО | Локально |
| `docker compose ... config` | ТРЕБУЕТ GITHUB ACTIONS | Docker отсутствует в локальной среде |
| Build `runtime`/`ops` | ТРЕБУЕТ GITHUB ACTIONS | Docker отсутствует в локальной среде |
| Non-root runtime + health smoke | ТРЕБУЕТ GITHUB ACTIONS | Отдельный CI step |

## 8. Критерии завершения пакета

1. Выбран тестовый VPS и создан постоянный публичный IPv4.
2. Docker/Compose stack развернут из актуального commit.
3. Test URL доступен без VPN из минимум двух сетей РФ и одной сети РБ.
4. TLS certificate валиден; HTTP redirect и `/health/ready` работают.
5. `infra_probe.py --strict` не имеет required failures.
6. Yandex AI endpoint доступен по TLS/HTTPS.
7. Reed endpoint доступен на транспортном уровне; authenticated smoke переносится в REED-COMPAT-001.
8. Основные страницы, поиск и PDF smoke проходят.
9. Encrypted backup Render PostgreSQL создан на VPS и восстановлен в isolated `restore-db`.
10. Отчёт теста заполнен и приложен к PLAN_CURRENT.

## 9. Rollback

INFRA-001 не меняет production Render. Неудачный VPS test откатывается удалением test VM. DNS production и `DATABASE_URL` Render не переключаются.

## 10. Следующее действие

Создать тестовый VPS у кандидата №1, выполнить `docs/INFRA001_VPS_TEST.md`, сохранить probe reports и принять решение о провайдере.

## 11. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 06.08.2026 | Добавлены container baseline, VPS probe, CI build/smoke и restore-test profile |
