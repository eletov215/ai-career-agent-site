# AI Career Agent — аудит источников

| Поле | Значение |
|---|---|
| Версия | 1.4.1 |
| Дата | 07 августа 2026 |
| Статус | ДЕЙСТВУЮЩИЙ |
| Входной код | `ai-career-agent-site-main (4).zip` |
| SHA-256 входного ZIP | `2d3c4cc36121ae70a0deec98f64abf29efb4562f6501dce062186ed781e62419` |
| GitHub snapshot | Пользователь подтвердил, что ZIP выгружен из актуального `main`; commit metadata в ZIP отсутствует |
| Канонический план до пакета | PLAN_CURRENT 1.4.0 |
| Канонический паспорт до пакета | PROJECT_PASSPORT 2.14 |
| Результат | SYNC-001 candidate + PLAN_CURRENT 1.4.1 + паспорт 2.15 |

## 1. Проверка входного ZIP

| Область | Найдено | Решение |
|---|---|---|
| Production code | INFRA-PREP-001, SEC-001, OPS-001 присутствуют | Использован как рабочая основа без отката |
| GitHub workflow | `.github/workflows/ci.yml` присутствует | Расширен отдельным SYNC-001 step |
| Dotfiles | `.gitignore`, `.dockerignore`, `.env.example` присутствуют | Сохранены |
| Database | Alembic 0001/0002 | Добавлена migration 0003 |
| Repository plan | 1.3.5 | Устарел относительно загруженного PLAN 1.4.0; заменён и обновлён до 1.4.1 |
| Repository passport | 2.13 | Устарел относительно загруженного паспорта 2.14; заменён и обновлён до 2.15 |
| README/ROADMAP | INFRA-001 как ближайший пакет | Синхронизированы с новой hosting-independent очередью |
| Trudvsem lifecycle | daemon thread внутри Gunicorn | Заменён external worker/durable queue |

## 2. Актуальные источники после пакета

1. GitHub `main` после последнего подтверждённого merge остаётся главным источником кода.
2. До merge SYNC-001 рабочей основой является полный ZIP этого package.
3. Канонический план: PLAN_CURRENT 1.4.1.
4. Канонический паспорт: PROJECT_PASSPORT 2.15.
5. Implementation: `docs/SYNC001_IMPLEMENTATION.md`.
6. Verification: `docs/SYNC001_VERIFICATION_STATUS.md`.
7. Operations: `docs/SYNC001_RUNBOOK.md`.

## 3. Статусы

| Пакет | Статус |
|---|---|
| FND-001/FND-002 | ВЫПОЛНЕНО |
| DATA-001/DATA-002 | ВЫПОЛНЕНО |
| SEC-001 | ВЫПОЛНЕНО |
| OPS-001 | ВЫПОЛНЕНО |
| INFRA-PREP-001 | ВЫПОЛНЕНО |
| DOC-001 | В РАБОТЕ как постоянный процесс |
| SYNC-001 | НУЖНА ПРОВЕРКА НА GITHUB/RENDER |
| SYNC-002 | ЗАПЛАНИРОВАНО |
| INFRA-001 | ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА |

## 4. Изменённые категории файлов

- Flask queue/status integration;
- external sync service, lock и worker scripts;
- domain/models/repositories/storage;
- Alembic migration и expected revision;
- Render/Docker/Compose runtime;
- config/CI/tests;
- README, ROADMAP, CHANGELOG, architecture, operations, migration docs;
- canonical plan/passport and package runbooks.

## 5. Секреты и runtime artifacts

Финальный пакет не должен содержать:

```text
.env
OAuth/API tokens
DATABASE_URL credentials
production backups/dumps
*.db
virtualenv
.pytest_cache
__pycache__
*.pyc
infra/reports
```

`infra/vps/.env.example` содержит только placeholders.

## 6. Внешние источники

SYNC-001 не требует новых внешних данных или платных API. Provider HTTP в tests mocked. Инфраструктурная стратегия по VPS/Yandex AI/Reed остаётся без изменений относительно PLAN_CURRENT 1.4.0.

## 7. Следующее действие

Загрузить полный SYNC-001 ZIP в отдельную ветку, дождаться зелёного CI, затем выполнить Render checklist. Старые PLAN_CURRENT ниже 1.4.1 и паспорт ниже 2.15 считать устаревшими для текущего статуса.

## 8. Журнал

| Версия | Дата | Изменение |
|---|---|---|
| 1.3.5 | 06.08.2026 | INFRA-PREP toolkit и source sync |
| 1.4.0 | 07.08.2026 | Hosting strategy: real VPS перенесён в pre-release |
| 1.4.1 | 07.08.2026 | Проверен актуальный GitHub ZIP; repository docs синхронизированы; реализован SYNC-001 candidate |
