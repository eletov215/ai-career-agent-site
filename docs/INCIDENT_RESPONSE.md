# AI Career Agent - краткий incident response runbook

## 1. Приоритеты

1. Безопасность людей и данных.
2. Остановить дальнейшую потерю/утечку.
3. Сохранить evidence без секретов.
4. Восстановить минимально безопасный сервис.
5. Зафиксировать root cause и предотвращение повторения.

## 2. Severity

| Уровень | Пример | Реакция |
|---|---|---|
| SEV-1 | Утечка token/resume, потеря production DB, полный outage | немедленно остановить writes/deploy, revoke secrets, incident owner |
| SEV-2 | Основной поиск/OAuth недоступен, readiness 503 | диагностика и rollback в согласованное окно |
| SEV-3 | Один provider недоступен, alert/metrics degraded | graceful degradation, issue и плановое исправление |

## 3. Первые 15 минут

1. Записать UTC time, symptom, affected URL и `X-Request-ID`.
2. Проверить `/health/live` и `/health/ready`.
3. Проверить latest deploy/commit и database revision.
4. Проверить Render/VPS/network status.
5. Не публиковать log excerpts с credentials/body/query.
6. При подозрении на compromise: rotate affected secrets и отключить provider/endpoint.
7. При regression: остановить auto-deploy, подготовить application rollback без schema downgrade.

## 4. Диагностика

При временно включённых diagnostics:

```text
GET /ops/status
X-Diagnostics-Secret: ...
```

Использовать только header secret. После incident выключить `DEBUG_DIAGNOSTICS` и при необходимости rotate secret.

Проверить:

- status/latency HTTP endpoints;
- provider failure/timeouts;
- recent sanitised errors;
- DB connectivity/revision;
- worker state;
- alert delivery counters.

## 5. Rollback

- Application rollback предпочтительнее schema downgrade.
- PostgreSQL не удалять.
- Перед data restore создать новый backup.
- Restore выполнять в clone/test DB, затем переключать connection/DNS по runbook.
- После rollback проверить `/health/ready`, OAuth, vacancy search, PDF upload и public status.

## 6. Data/security incident

1. Остановить affected route/integration feature flag.
2. Revoke/rotate OAuth/API/database/session secrets по affected scope.
3. Не удалять audit evidence до фиксации incident.
4. Определить затронутые пользователи/данные/период.
5. Выполнить юридическую и пользовательскую коммуникацию по применимым требованиям.
6. Добавить regression test и обновить runbook.

## 7. Post-incident report

Минимум:

- UTC timeline;
- impact и duration;
- detection source;
- root cause;
- mitigation/rollback;
- data exposure assessment;
- corrective actions с owner/deadline;
- tests/alerts/runbooks, предотвращающие повторение.
