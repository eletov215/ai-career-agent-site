# AI-005 LIVE QA — controlled synthetic Alice preflight

Дата проверки: 28 сентября 2026. Issue: `AI-005-LIVE-QA-001`. Проверенная основа:
`f702c0c2bab53e6b24e53ca3b80ba7cb896018ec` (remote baseline независимо подтверждён
владельцем; GitHub из рабочего контейнера недоступен).

## 1. Результат Phase A

Preflight существующего SITE QA не обнаружил дефекта application code, который мешал бы
одному будущему controlled live test. Текущий результат —
`READY_FOR_OWNER_LIVE_APPROVAL`, а не разрешение вызова и не `COMPLETE`.

- provider dispatches: `0`;
- paid provider calls: `0`;
- production changes: `0`;
- GitHub Actions: `NOT_RUN / BLOCKED_GITHUB_ACCESS`;
- live provider и human quality acceptance: `NOT_RUN`;
- real-data AI: `CLOSED`, `REAL_DATA_SUPPORTED=False`;
- production legal policy: `DRAFT / NOT_ACTIVE`.

Phase B не требует изменения runtime: подтверждены действующие границы ниже. Этот документ
добавлен как воспроизводимый operator checklist, потому что прежний runbook перечислял
названия controls, но не фиксировал их точную комбинацию и порядок проверки перед вызовом.
Historical evidence и его hashes не изменяются.

## 2. Подтверждённые границы кода

SITE QA регистрируется в отдельном `/admin/ai/letters/site-qa` namespace и до любой
операции требует active verified account из `SEARCH_ADMIN_EMAILS`; недоступный или
неразрешённый раздел отвечает `404`. Два QA flags принимают только `0` или `1`.

Источники выбирает сервер из неизменяемых RU/EN `synthetic_cases()`. Отправить profile,
resume, vacancy, user id, произвольный fixture или request-level live switch нельзя.
Отдельные non-login synthetic owners не имеют email/password и не заменяют tester account.
Следовательно, тест не требует и не читает реальный профиль, резюме, вакансию или другой
пользовательский content.

Preview подписан и действует десять минут от создания письма. Его ticket связан с actor,
synthetic owner, letter, revision, source hashes, options и стабильной operation
`site-qa-one-dispatch-v1`. Повторный preview не продлевает окно. Повтор/параллельный POST
для той же operation попадает в существующий idempotency ledger и не создаёт второй
dispatch; новое письмо является новой потенциально платной operation.

`SiteQASettingsGate` сначала вызывает общий `AISettings.gate(now)` и игнорирует только
`no_logging_wait`. Он сохраняет `AI_ENABLED`, `AI_KILL_SWITCH`,
`AI_SYNTHETIC_ACCESS_ENABLED`, credential/model checks и делегирует provider properties.
DB policy дополнительно сохраняет versioned enable/kill switch, pricing freshness,
input/output limits, user/global request and budget limits, concurrency, leases и circuit
breaker. `LetterRuntime` делает максимум один provider dispatch даже если общая policy
допускает два attempts; timeout/unknown учитывается консервативно и автоматически не
повторяется.

Production `YandexAliceProvider` всегда формирует строковый header
`x-data-logging-enabled: false`. One-shot HTTP worker проверяет точное строковое значение
до создания `requests.Session`; отсутствующее значение, `true` или boolean `false`
возвращает configuration failure без network dispatch.

SITE QA использует существующие таблицы AI ledger, user/profile/saved-vacancy и
cover-letter на schema `20260922_0021`. Новая migration не нужна. Provider response
сохраняется только как pending proposal; отправки работодателю нет.

## 3. Точная конфигурация будущего одного вызова

До отдельного owner approval значения не менять. После approval оператор должен сначала
проверить deployment SHA, recovery point и фактические secrets/DB policy, а затем открыть
только следующий synthetic контур:

| Control | Требуемое значение для короткого окна |
|---|---|
| `SEARCH_ADMIN_EMAILS` | содержит email active verified tester |
| `AI_SITE_QA_ENABLED` | `1` |
| `AI_SITE_QA_LIVE_ENABLED` | `1` только на разрешённое окно |
| `AI_ENABLED` | `1` |
| `AI_KILL_SWITCH` | `0` |
| `AI_SYNTHETIC_ACCESS_ENABLED` | `1` |
| `AI_YANDEX_API_KEY` | непустой существующий production secret; значение не записывать |
| `AI_YANDEX_FOLDER_ID` | существующий folder id, допустимый по `^[A-Za-z0-9_-]{3,128}$`; значение не записывать |
| `AI_YANDEX_MODEL_URI` | точно `gpt://<AI_YANDEX_FOLDER_ID>/aliceai-llm/latest` |
| `AI_NO_LOGGING_DISABLED_AT` | SITE QA от него не зависит; не подделывать и не менять ради теста |
| DB policy `enabled` / `kill_switch` | `true` / `false` |

Перед активацией выполнить read-only `python scripts/manage_ai_runtime.py show`. Не считать
repository defaults состоянием production. В выведенной versioned policy проверить:

1. `pricing_checked_on` не находится в будущем и его возраст строго меньше
   `pricing_valid_days`; одновременно вручную подтвердить текущий тариф провайдера и
   значения `input_microrub_per_token`/`output_microrub_per_token`;
2. worst-case reservation
   `(max_input_tokens * input_rate + max_output_tokens * output_rate) * max_attempts`
   помещается в остатки user daily, global daily и global monthly budgets;
3. user/global request и concurrency limits имеют запас для одной operation;
4. provider circuit не открыт, нет зависшей reservation/unknown operation с предыдущего
   теста, а ledger доступен;
5. `attempt_timeout_seconds`, `total_timeout_seconds` и `lease_seconds` остаются валидны;
6. изменение policy, если оно действительно нужно, выполняется только отдельной
   owner-approved командой `set` с `--expected-version` из `show`, затем повторяется
   read-only `show`. Pricing нельзя «освежить» одной датой без проверки тарифа.

Не печатать secrets и не добавлять их в PR/evidence. Не менять Render, Neon, Yandex,
Terraform или production DB в рамках этого preflight.

## 4. Строго разрешаемая live operation после нового approval

Одна операция: `language=ru`, `length=short`, `tone=professional`, источник — встроенный
fixed synthetic SITE QA fixture. Maximum initial provider dispatches: `1`.

Порядок: открыть SITE QA как разрешённый tester, создать ровно одно новое письмо, получить
его signed preview, ещё раз сверить ledger/circuit и нажать generate ровно один раз.
Refresh/replay не считать разрешением новой операции. При timeout, unknown outcome,
неясном UI result или потере соединения **не создавать новое письмо и не повторять
generate**, пока не проверены `ai_usage_events`, accounting, operation/idempotency status и
provider-side сведения. После проверки закрыть `AI_SITE_QA_LIVE_ENABLED=0`; остальные
production изменения требуют отдельного решения владельца.

## 5. Что остаётся NOT_RUN

GitHub Actions, deployment, production SITE QA, live provider response, provider-side
accounting comparison, screenshot/browser QA настоящего ответа, human quality review и
legal approval не выполнялись. Никакое из них не следует из локальных mock-transport
тестов. AI-006 не начат; полный AI-005 остаётся `IN_PROGRESS / LIVE_NOT_ACCEPTED`.
