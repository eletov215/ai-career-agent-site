# OPS-001 — статус проверки

| Поле | Значение |
|---|---|
| Версия отчёта | 1.3 |
| Дата | 07 августа 2026 |
| Статус пакета | ВЫПОЛНЕНО |
| Перенесённый release gate | Production backup/restore drill → OPS-002/REL-001 |
| Текущая candidate schema после SYNC-002 | `20260807_0004` |

## 1. Подтверждённые проверки

| Проверка | Результат | Доказательство |
|---|:---:|---|
| GitHub observability tests | ПРОЙДЕНО | Green Actions |
| CI encrypted PostgreSQL backup/restore | ПРОЙДЕНО | Separate restore database |
| `/health/live` | ПРОЙДЕНО | HTTP 200 |
| `/health/ready` | ПРОЙДЕНО | DB and migrations ok |
| OPS-001 revision на момент проверки | ПРОЙДЕНО | `20260804_0002` |
| `X-Request-ID` response/log | ПРОЙДЕНО | Header, JSON и structured log match |
| Secret-free logs | ПРОЙДЕНО | No token/cookie/DB URL/resume body |
| Protected `/ops/status` | ПРОЙДЕНО | 404 without secret, 200 with secret |
| Provider telemetry | ПРОЙДЕНО | Trudvsem metrics present |
| Webhook alert | ПРОЙДЕНО | Real sanitised POST JSON delivered |
| Redeploy persistence | ПРОЙДЕНО | Cached state preserved |

## 2. Решение PLAN_CURRENT 1.4.0

Базовый OPS-001 закрыт как выполненный: код, CI, Render observability и alerting подтверждены; vendor-neutral backup/restore tooling проверен на PostgreSQL в CI.

Encrypted backup **реальной** production PostgreSQL и restore в отдельную test database не отменены и не объявлены выполненными. Они перенесены в обязательный `OPS-002` и повторно проверяются в `REL-001`, когда будет выбран production VPS и isolated restore database.

## 3. Текущий regression gate

Каждый merge продолжает выполнять:

```text
Verify OPS-001 observability controls
Verify PostgreSQL encrypted backup and restore
```

SYNC-001 добавил migration `20260807_0003`; candidate SYNC-002 добавляет `20260807_0004`. OPS tooling должно backup/restore checkpoint и lifecycle metadata без изменения формата безопасности.

## 4. Предрелизный production drill

В OPS-002 выполнить:

```text
production encrypted backup created
manifest and SHA-256 verified
restore database revision = current production revision
table counts match
production database untouched
rollback rehearsal passed
```

## 5. Временные diagnostics

После тестов webhook/ops status:

- удалить temporary Webhook.site URL;
- установить `DEBUG_DIAGNOSTICS=0`;
- удалить temporary diagnostics secret;
- подтвердить `/ops/status -> 404`.

## 6. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.1 | 06.08.2026 | Подтверждены logs correlation, webhook и CI restore |
| 1.2 | 06.08.2026 | Production restore drill интегрирован в INFRA toolkit |
| 1.3 | 07.08.2026 | OPS-001 закрыт как базовый пакет; real production drill перенесён в OPS-002/REL-001 без отмены |
