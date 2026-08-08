# AI Career Agent — аудит источников v1.4.3

| Поле | Значение |
|---|---|
| Документ | SOURCE_AUDIT |
| Версия | 1.4.3 |
| Дата | 07 августа 2026 |
| Проверяемый пакет | SYNC-002 candidate |
| Текущий источник кода | `ai-career-agent-site-main (5).zip` — актуальный GitHub `main` после SYNC-001 |
| Канонический план до обновления | PLAN_CURRENT 1.4.2 |
| Канонический паспорт до обновления | PROJECT_PASSPORT 2.16 |
| Результат | SYNC-002 реализован локально; статус НУЖНА ПРОВЕРКА; docs синхронизированы до 1.4.3/2.17 |

## 1. Приоритет источников

1. ZIP `ai-career-agent-site-main (5).zip`, присланный как актуальный GitHub main, является рабочей основой кода этой задачи.
2. Внешние PLAN_CURRENT 1.4.2 и PROJECT_PASSPORT 2.16 определяют очередь и критерии SYNC-002.
3. Repository docs из ZIP имели более старые версии PLAN 1.4.1/passport 2.15 и не переопределяли внешние канонические источники.
4. После candidate merge главным источником кода снова станет GitHub main; внешние docs этой поставки определяют статус до следующего обновления.

## 2. Найденные источники

| Источник | Найден | Состояние до пакета | Действие |
|---|---|---|---|
| GitHub ZIP `(5)` | Да | Актуальный код после SYNC-001 | Принят как baseline |
| PLAN_CURRENT 1.4.2 MD/DOCX/PDF | Да | Действующий | Обновлён до 1.4.3 |
| PROJECT_PASSPORT 2.16 | Да | Действующий | Обновлён до 2.17 |
| SYNC001 implementation 1.1 | Да | Исторический завершённый package | Сохранён |
| SOURCE_AUDIT 1.4.2 | Да | Действующий до начала | Обновлён до 1.4.3 |
| Repository `docs/PLAN_CURRENT.md` | Да | Устарел: 1.4.1 | Заменяется 1.4.3 |
| Repository `docs/PROJECT_PASSPORT.md` | Да | Устарел: 2.15 | Заменяется 2.17 |
| README/ROADMAP/CHANGELOG | Да | SYNC-001 candidate/verification | Синхронизируются с SYNC-002 candidate |

## 3. Подтверждённая baseline

До SYNC-002 подтверждены:

```text
FND-001
FND-002
DATA-001
DATA-002
SEC-001
OPS-001
INFRA-PREP-001
SYNC-001
```

Production schema baseline — `20260807_0003`. Внешний Trudvsem worker, durable queue и cache persistence после restart подтверждены.

## 4. Реализованный candidate SYNC-002

В актуальном baseline добавлены:

- migration `20260807_0004`;
- `sync_checkpoints` с watermark/cursor/retry;
- lifecycle-поля vacancy source records;
- bounded bootstrap/incremental windows;
- API `modifiedFrom`/`modifiedTo` + page total;
- continuation после reconnect;
- idempotent upsert/closed reactivation;
- TTL closure и retention purge;
- persistent exponential retry;
- checkpoint backup inventory;
- отдельный CI gate и tests.

## 5. Локальная проверка

```text
full pytest: 130 passed, 6 skipped
SYNC-002 tests: 8 passed
migration upgrade/downgrade/upgrade: passed
Alembic check: passed
repository hygiene: passed
manifest/document checks: passed
```

Docker/PostgreSQL production paths должны быть подтверждены GitHub Actions. Render должен подтвердить revision 0004 и runtime behavior.

## 6. Новые канонические версии

```text
PLAN_CURRENT 1.4.3
PROJECT_PASSPORT 2.17
SOURCE_AUDIT 1.4.3
SYNC002_IMPLEMENTATION 1.0
SYNC002_VERIFICATION_STATUS 1.0
SYNC002_RUNBOOK 1.0
```

SYNC-002 остаётся **НУЖНА ПРОВЕРКА**. После подтверждения следующий package — SEARCH-001.

## 7. Исключённые артефакты

В поставку и GitHub не входят:

```text
.env
реальные secrets/tokens/passwords
*.db / *.sqlite / *.dump / *.enc
backups/
virtualenv
.pytest_cache
__pycache__
*.pyc
.git
private URLs/reports
```

## 8. Правило следующего чата

Следующий чат обязан:

1. прочитать PLAN_CURRENT 1.4.3 и PROJECT_PASSPORT 2.17;
2. использовать новый GitHub main либо более новый ZIP;
3. не повторять SYNC-001;
4. сначала завершить verification SYNC-002;
5. после выполнения начать SEARCH-001;
6. оставить real INFRA-001 отложенным до предрелизного окна.
