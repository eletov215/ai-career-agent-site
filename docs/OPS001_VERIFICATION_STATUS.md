# OPS-001 - статус проверки

| Поле | Значение |
|---|---|
| Версия отчёта | 1.2 |
| Дата | 06 августа 2026 |
| Статус пакета | НУЖНА ФИНАЛЬНАЯ ПРОВЕРКА |
| Незакрытый критерий | Production backup/restore drill |
| План завершения | Выполнить на тестовом VPS INFRA-001 |

## 1. Подтверждённые проверки

| Проверка | Результат | Доказательство |
|---|:---:|---|
| GitHub observability tests | ПРОЙДЕНО | Green Actions |
| CI encrypted PostgreSQL backup/restore | ПРОЙДЕНО | Separate restore database |
| `/health/live` | ПРОЙДЕНО | HTTP 200 |
| `/health/ready` | ПРОЙДЕНО | DB and migrations ok |
| Revision | ПРОЙДЕНО | `20260804_0002` |
| `X-Request-ID` response | ПРОЙДЕНО | Header and JSON match |
| `X-Request-ID` application log | ПРОЙДЕНО | Structured JSON log found |
| Secret-free logs | ПРОЙДЕНО | No token/cookie/DB URL/resume body |
| Protected `/ops/status` | ПРОЙДЕНО | 404 without secret, 200 with secret |
| Provider telemetry | ПРОЙДЕНО | Trudvsem metrics present |
| Webhook alert | ПРОЙДЕНО | Real POST JSON delivered |
| Redeploy persistence | ПРОЙДЕНО | `cached_total=77` preserved |

## 2. Незакрытая проверка

Нужно создать encrypted backup реальной Render PostgreSQL, проверить manifest/SHA-256 и восстановить копию в отдельную test database. Production database не должна быть restore target.

## 3. Реализация в INFRA-001

Для завершения добавлены:

- Docker target `ops` с PostgreSQL 17 client tools;
- persistent backup volume;
- profile `restore-test` с isolated PostgreSQL 17;
- команды backup, verify и restore в `docs/INFRA001_VPS_TEST.md`.

## 4. Критерий закрытия

```text
production encrypted backup created
manifest and SHA-256 verified
restore database revision = 20260804_0002
table counts match
production database untouched
```

После этого OPS-001 переводится в `ВЫПОЛНЕНО`.

## 5. Временные настройки

После тестов удалить Webhook.site URL, установить `DEBUG_DIAGNOSTICS=0`, удалить temporary diagnostics secret и подтвердить `/ops/status -> 404`.

## 6. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.1 | 06.08.2026 | Подтверждены logs correlation, webhook и CI restore |
| 1.2 | 06.08.2026 | Production restore drill интегрирован в INFRA-001 VPS toolkit |
