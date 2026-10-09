# HOST-001 — безопасная подготовка повторного Stage C / 2026-10-09

**Статус: OFFLINE_PREPARATION_ONLY / FIELD_TEST_NOT_ACCEPTED / NO_PAID_APPLY.**

Этот документ — план подготовки следующего synthetic-only теста. Он не является одобрением повторной оплаты, deployment, `terraform apply/destroy`, миграции Render/Neon, LEGAL activation или реальных AI-вызовов.

## 1. Основание: первый live-тест

| Проверка | Доказательство | Статус |
|---|---|---|
| Credentialed plan-only, 22 planned creates | [run 37911719343](https://github.com/eletov215/ai-career-agent-site/actions/runs/37911719343) | PASS |
| Первый billed apply | [run 37917270157](https://github.com/eletov215/ai-career-agent-site/actions/runs/37917270157) | FAILED; исходный provider stderr был удалён с временным runner log |
| Автоматический recovery | [run 37917319022](https://github.com/eletov215/ai-career-agent-site/actions/runs/37917319022) | FAILED из-за `SOURCE_RUN_STARTED_AT` |
| Ручной recovery | [run 37918593453](https://github.com/eletov215/ai-career-agent-site/actions/runs/37918593453) | PASS: в Terraform remote state осталось 0 managed resources |
| Исправление ошибок CI/workflow | [PR #92](https://github.com/eletov215/ai-career-agent-site/pull/92) | MERGED, classified safe apply diagnostics + repaired automatic teardown |
| Канонический инцидент | [PR #94](https://github.com/eletov215/ai-career-agent-site/pull/94) | MERGED; исторический статус зафиксирован |

**ROOT_CAUSE_NOT_PROVEN:** нет безопасного сохранённого сообщения провайдера из первого `terraform apply`. Новые диагностические классы доступны в коде, но не проходили live-проверку. Прежний успех сетевых ресурсов не доказывает готовности VM и Managed PostgreSQL.

Из предоставленных владельцем скриншотов 9 октября:
- VPC operations: шесть успешных create в 13:23 и соответствующие шесть successful delete в 13:36 по Москве, включая public IP;
- Compute VM, PostgreSQL clusters и VPC networks после recovery отсутствовали в списках каталога;
- Managed PostgreSQL operations — пустой список; Audit Trails не настроен в выбранном каталоге;
- Billing для 9 октября и каталога `ai-career-agent-ai`: потребление **0,13 ₽**, скидка **−0,13 ₽**, к оплате на момент скриншота **0,00 ₽**. **Повторить 10 октября**, когда детализация за 9-е окончательно обновится.
- Dedicated remote-state bucket и временный доступ к нему оставлены до завершения evidence/recovery процесса; не путать с удалённым field-test backup bucket.

Эти данные не подтверждают полный ресурсный аудит облака, окончательный счёт или успешный Stage C.

## 2. Разделение с параллельным AI004-M04-B

[Issue #95](https://github.com/eletov215/ai-career-agent-site/issues/95) — **новая миграция приложения/БД для персонального кеша сравнения вакансий**, **не** `MIG-001` (перенос production-хостинга).

- Уже объединён M04-A: cache identity / report seals **без схемы**.
- M04-B может готовить отдельный PR с `user_match_reports`, `user_match_cache`, новой Alembic revision, ownership/privacy/backup integration — **только после отдельного одобрения на разработку**.
- Сам по себе approved **PR preparation** не разрешает merge, deploy, применение миграции к Neon или реальные данные.
- В `render.yaml` заданы `autoDeployTrigger: checksPass` и `startCommand: python scripts/manage_db.py upgrade && python scripts/start_runtime.py`. **Merge миграции в main способен автоматически применить её в production**. Этот факт обязан быть принят во внимание перед разрешением merge M04-B.
- Наш HOST-001 не меняет `migrations/versions`, `database.py`, models, repositories, privacy, backups, Render/Neon config. Эти файлы остаются во владении потока AI004-M04.
- Если M04-B войдёт в `main` до повторного Stage C, необходимо заново сверить schema revision, synthetic fixture и recovery evidence; **нельзя заявлять M04-B tested** только по старым синтетическим backup/restore сценариям.

## 3. Новая офлайн-проверка ревизии

Добавлен `scripts/host001_stage_c_revision_gate.py`, не использующий ключи или внешние сервисы. Он:

1. Проверяет единственный Alembic head без ветвлений, циклов, отсутствующих родителей или orphan revisions.
2. Требует равенства head и `database.CURRENT_REVISION`.
3. Проверяет, что Stage C fixture получает `CURRENT_REVISION` из runtime, а не жёстко заданного номера.
4. Сопоставляет локальный `git HEAD` с **независимо выбранным и проверенным** 40-символьным SHA.
5. Печатает только статус/ревизию/число файлов/commit, не подключаясь ни к БД, ни к Terraform.

Для офлайн-проверки после выбора будущего baseline:

```bash
python -m unittest tests.test_host001_stage_c_revision_gate -v
REVIEWED_MAIN_SHA='PASTE_40_CHARACTER_SHA_FROM_GITHUB_MAIN'
python scripts/host001_stage_c_revision_gate.py --expected-sha "$REVIEWED_MAIN_SHA"
```

`<REVIEWED_MAIN_SHA>` необходимо взять из GitHub main *после* завершения параллельных PR и required CI, а не подставлять автоматически `$(git rev-parse HEAD)`: иначе проверка git-pin теряет смысл. Эта команда выполняется в checkout выбранного SHA. Она **не** доказывает, что схема production или Yandex DB уже мигрирована.

HOST-001 CI запускает этот test на изменениях `database.py`/`migrations/versions/**`, но не получает Yandex credentials и не запускает платную инфраструктуру.

## 4. Следующий gate: только после явного одобрения владельца

Прежде чем **рассматривать** второй billed Stage C:

1. Повторно проверить начисления Billing 10 октября, отдельные зарезервированные IP и состояние control-plane ресурсов/ролей; сохранить evidence. Не удалять Terraform state без готового recovery решения.
2. Убедиться в отсутствии активного/billable Stage C и в нуле managed resources по всем Stage C state objects; не использовать старый shared state key.
3. Определить на каком commit и Alembic revision будет выполнен synthetic test. Если M04-B изменил schema, расширить synthetic/privacy/backup/restore acceptance так, чтобы новые таблицы проверялись **только при наличии согласованной M04-B схемы**.
4. Проверить CI нового frozen commit, Terraform/static, allowlist create-only plan, квоты/стоимость и Yandex cloud IAM privileges; не расширять ресурсный scope по собственной инициативе.
5. Удостовериться, что независимый recovery-teardown запускается **до** apply, использует exact source SHA и ID run, остаётся внутри владельческого лимита и теперь обрабатывает source start timestamp; оператор знает ручную recovery процедуру.
6. Получить **новое явное разрешение** на конкретное 1-time synthetic-only окно, общий денежный потолок и план удаления. Предыдущее разрешение 1 000 ₽ / ≤4 часов относилось к уже завершённому тесту и **не переносится автоматически**.
7. Если после отдельного одобренного apply снова возникает ошибка — **никаких повторов apply**; сохранить только классифицированную диагностику, провести teardown и отметить `FIELD_TEST_NOT_ACCEPTED`. Реальные production данные и AI calls запрещены.

**Стоп-условия:** отсутствует один required check; возникла новая Alembic revision без согласованного schema/fixture плана; `main` изменился после frozen-review; нечёткое ownership ресурсов; бюджеты/квоты/деадлайны не доказаны; секреты попали в журнал; Terraform managed resources от старого run ещё живы.

Текущий `HOST-001`: **CODE_GUARD_PASS / LIVE_FIELD_TEST_FAILED / TEARDOWN_VERIFIED / BILLING_PRELIMINARY / NEW_APPLY_NOT_AUTHORIZED**.
