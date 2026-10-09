# HOST-001 Stage C — инцидент и восстановление 9 октября 2026

## Основание и граница

- Проект: AI Career Agent; tracks HOST-001 / Issues #73 и #78.
- Подтверждённый owner ceiling *для совершённого теста*: до **1 000 ₽** суммарно и до **4 часов**, synthetic only.
- Проверяемый apply commit: `e68e3a7be1e2817ae6d251d9f83f9efa797053df`.
- Render/Neon production, MIG-001 и production database: **NOT TOUCHED**.
- Пользовательские данные, реальные Alice/Yandex provider calls, emails/employer sends: **FORBIDDEN / NOT_RUN**.
- Этот документ не выдаёт разрешения на повторный платный запуск.

## Проверенные события

| Этап | Evidence | Фактический результат |
|---|---|---|
| Credentialed plan-only #8 | [run 37911719343](https://github.com/eletov215/ai-career-agent-site/actions/runs/37911719343) | SUCCESS, 22 planned create-only resources, no apply |
| Stage C bounded apply #5 | [run 37917270157](https://github.com/eletov215/ai-career-agent-site/actions/runs/37917270157) | FAILED на `Apply reviewed Stage C plan`; Terraform output был направлен в удалённый при cleanup временный файл. Первичная причина Yandex provider по безопасному логу не определена |
| Auto recovery teardown #7 | [run 37917319022](https://github.com/eletov215/ai-career-agent-site/actions/runs/37917319022) | FAILED: `SOURCE_RUN_STARTED_AT: unbound variable`; до `terraform destroy` не дошёл |
| Manual recovery teardown #8 | [run 37918593453](https://github.com/eletov215/ai-career-agent-site/actions/runs/37918593453) | SUCCESS; Terraform выполнил удаление, итоговая проверка `no managed Terraform resources remain`; `had_changes=true` |
| Исправление recovery/diagnostics | [PR #92](https://github.com/eletov215/ai-career-agent-site/pull/92) | MERGED, SHA `2dc5c715953eefd166e71a9079df727e6bce80ab`; CI #644 SUCCESS на PR-head. Live retry не проводился |

## Остаточные проверки

- Оператор предоставил изображения пустых списков виртуальных машин, Managed PostgreSQL и сетей VPC в целевом каталоге Yandex Cloud.
- Dedicated Object Storage bucket `aca-stage-c-tfstate-deniz-20261007` с одним объектом оставлен для Terraform state/recovery. Его ключ доступа остаётся отдельной операционной задачей; не удалять до закрытия доказательств и принятого решения по следующему тесту.
- Публичные резервируемые IP **не были независимо подтверждены** через соответствующий раздел консоли; не подменять это утверждением `0 IP`.
- Видимые в Billing 0,00 ₽ являются снимком экрана, а не окончательной сверкой расходов: данные могут поступать позже. Итоговую стоимость требуется подтвердить отдельно.
- Само `0 managed resources` относится к управляемому Terraform remote state, а не к полному аудиту всех возможных вручную созданных ресурсов в Yandex Cloud.

## Принятое техническое решение

PR #92 исправляет `SOURCE_RUN_STARTED_AT` только для шага автоматического удаления; добавлена fail-closed проверка значения перед deadline calculation. Ручной recovery не изменён. При сбое `terraform apply` workflow теперь сохраняет exit code и выводит **только фиксированные классы ошибок, allowlisted resource addresses и HTTP status codes**, без необработанного provider stdout и секретов.

Все CI-проверки на PR-head прошли, платные provider jobs пропущены. Это `CODE_GUARD_PASS`, **не** `FIELD_TEST_PASS`.

## Что требуется до следующего Stage C

1. Подтвердить отсутствие резервируемых публичных IP и иных остаточных billable ресурсов, повторно проверить Billing.
2. Зафиксировать либо выяснить root cause первого apply; если его нельзя восстановить из безопасных журналов, классифицировать как `ROOT_CAUSE_NOT_PROVEN` и применять диагностический workflow только в отдельно согласованном тесте.
3. Убедиться, что `main` и CI обновлены и проверены, автоматический teardown использует тот же зафиксированный commit и запланирован до apply.
4. Получить **новое явное одобрение** бюджета/временного окна/условий recovery перед любым дополнительным платным запуском.
5. Пройти синтетические acceptance-сценарии HOST-001 и подтвердить destroy; до этого Stage C = **FAILED / NOT_ACCEPTED**.
