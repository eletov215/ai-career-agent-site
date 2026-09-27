# AI-005 SITE QA — verification / r1 candidate

Дата: 27 сентября 2026. Основа `b828596c893d59a544f9678d7b45ab6ed7f44230`; схема `20260922_0021` без миграции.

| Gate | Статус |
|---|---|
| Реализация synthetic browser path | CANDIDATE |
| Python/Jinja syntax | Проверено в локальной подготовке; не runtime verification |
| Static component render | 20 geometry cases, 5 widths x 4 views; isolated Jinja/base harness, не Flask и не production |
| Новый pinned-dependency GitHub CI | PENDING |
| PostgreSQL + concurrency | Новые тесты подготовлены; результат нового CI отдельно |
| Browser mock transport | Новый workflow подготовлен; PENDING |
| DEPLOYED / production SITE_QA | NOT_RUN |
| LIVE_PROVIDER / QUALITY | NOT_RUN |
| LEGAL | TECHNICAL_ACCEPTED / LEGAL_PENDING; DRAFT сохранён |
| Paid Alice calls | 0 |
| Cloud resources / terraform apply | 0 / NOT_RUN |
| Full AI-005 | IN_PROGRESS / LIVE_NOT_ACCEPTED |

Локальная среда не содержит Flask и не имеет сетевого доступа к GitHub/PyPI. Существующие SQLAlchemy/Alembic/pytest и статическая проверка шаблона не подменяют закреплённую среду CI. Новые тесты не используют скрытую цепочку чужих pytest fixtures: собственный harness создаёт изолированную БД, synthetic users и настоящий provider adapter с явно поддельным транспортом.

Старые закрытые PR #46/#47 не используются как приёмка и не сливаются. Предыдущий отказ fixture job_env не переименовывается в успешный тест. Здесь требуется новый CI на точном head. Никаких заявлений о новой production QA, новом настоящем ответе модели или окончательной приёмке до соответствующего evidence нет.
