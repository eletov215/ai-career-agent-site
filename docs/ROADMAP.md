# AI Career Agent — дорожная карта

| Поле | Значение |
|---|---|
| Версия | 1.3.5 |
| Дата | 2026-08-06 |
| Источник | docs/PLAN_CURRENT.md |

## Ближайшая последовательность

```text
OPS-001 production backup/restore
→ INFRA-001 real VPS matrix
→ AI-BENCH-001
→ REED-COMPAT-001
→ AI-PROVIDER-001
→ HOST-001
→ DOMAIN-001
→ MIG-001
```

## Пакеты

| ID | Статус | Следующее действие |
|---|---|---|
| FND-001 | ВЫПОЛНЕНО | Базовые тесты и CI |
| FND-002 | ВЫПОЛНЕНО | Централизованная конфигурация |
| DATA-001 | ВЫПОЛНЕНО | PostgreSQL и Alembic |
| DATA-002 | ВЫПОЛНЕНО | Доменная модель и repositories |
| SEC-001 | ВЫПОЛНЕНО | Базовое усиление безопасности |
| OPS-001 | НУЖНА ФИНАЛЬНАЯ ПРОВЕРКА | Production backup/restore реальной БД |
| INFRA-001 | НУЖНА ПРОВЕРКА | Выбор и технический тест VPS для РФ/РБ |
| AI-BENCH-001 | ЗАПЛАНИРОВАНО | Benchmark Yandex AI Studio/Alice AI |
| REED-COMPAT-001 | ЗАПЛАНИРОВАНО | Проверка Reed с выбранного VPS |
| AI-PROVIDER-001 | ЗАПЛАНИРОВАНО | Стратегия AI-провайдеров |
| HOST-001 | ЗАПЛАНИРОВАНО | Подготовка production VPS |
| DOMAIN-001 | ЗАПЛАНИРОВАНО | Домен, DNS и TLS |
| MIG-001 | ЗАПЛАНИРОВАНО | Миграция production с Render |
