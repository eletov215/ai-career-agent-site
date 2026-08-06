# AI Career Agent - аудит источников

| Поле | Значение |
|---|---|
| Версия | 1.3.5 |
| Дата | 06 августа 2026 |
| Статус | ДЕЙСТВУЮЩИЙ |
| Актуальный код | `ai-career-agent-site-main (3).zip` + INFRA-001 changes |
| Канонический план | PLAN_CURRENT 1.3.5 |
| Канонический паспорт | Project Passport 2.13 |

## 1. Результат проверки входного ZIP

| Область | Состояние до изменений | Решение |
|---|---|---|
| Production code | SEC-001 fix и OPS-001 присутствуют | Использован без отката |
| Database | Alembic 0001/0002, PostgreSQL 17 | Схема не изменялась |
| CI | SEC/OPS/backup steps присутствуют | Расширен INFRA build/smoke |
| `docs/PLAN_CURRENT.md` | Версия 1.3.2 | Синхронизирован до 1.3.5 |
| `docs/PROJECT_PASSPORT.md` | Версия 2.10 | Синхронизирован до 2.13 |
| `README_FIRST.txt` | Устаревшая инструкция SEC CI fix | Удалён |
| `.gitignore` | Отсутствовал | Восстановлен и расширен |
| Docker/VPS manifests | Отсутствовали | Добавлены в INFRA-001 |

## 2. Канонические статусы

| Пакет | Статус |
|---|---|
| FND-001 | ВЫПОЛНЕНО |
| FND-002 | ВЫПОЛНЕНО |
| DATA-001 | ВЫПОЛНЕНО |
| DATA-002 | ВЫПОЛНЕНО |
| SEC-001 | ВЫПОЛНЕНО |
| OPS-001 | НУЖНА ПРОВЕРКА: production backup/restore |
| INFRA-001 | НУЖНА ПРОВЕРКА НА VPS |
| AI-BENCH-001 | ЗАПЛАНИРОВАНО |

## 3. Новые канонические документы

- `docs/DOCUMENT_STANDARD.md`
- `docs/INFRA001_IMPLEMENTATION.md`
- `docs/INFRA001_VPS_TEST.md`
- `docs/INFRA001_PROVIDER_DECISION.md`
- `docs/OPS001_VERIFICATION_STATUS.md`
- `docs/PLAN_CURRENT.md`
- `docs/PROJECT_PASSPORT.md`

## 4. Внешние источники INFRA-001

Проверены только официальные материалы провайдеров и API:

- Timeweb Cloud: cloud servers, public IP, firewall, backup, API/IaC.
- Yandex Cloud: Compute, VPC pricing, snapshots и AI API endpoints.
- Beget Cloud: VPS geography, public IPv4, backups и monitoring.
- Selectel: cloud servers, snapshots и backup methods.
- Reed Jobseeker API: endpoint и Basic Auth.
- HeadHunter OpenAPI: base URL и User-Agent requirement.

Полный список ссылок находится в `docs/INFRA001_PROVIDER_DECISION.md`.

## 5. Секреты и runtime artifacts

Проверяется отсутствие:

```text
.env
OAuth/API tokens
DATABASE_URL
production backups
database files
virtualenv
cache/bytecode
infra/reports
```

`infra/vps/.env.example` содержит только `CHANGE_ME` и test-only placeholders.

## 6. Следующее действие

Загрузить полный ZIP INFRA-001 в новую ветку, дождаться зелёного CI, затем создать тестовый VPS и выполнить `docs/INFRA001_VPS_TEST.md`.

## 7. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.3.5 | 06.08.2026 | Синхронизированы code/docs sources и добавлен INFRA-001 toolkit |
