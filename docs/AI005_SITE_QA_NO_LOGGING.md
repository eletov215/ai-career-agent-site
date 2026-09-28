# AI-005 SITE QA — исключение исторического no-logging wait

Дата: 28 сентября 2026. Successor к принятому SITE QA r1 на commit `cd526df75ca13cfed310114be1d96c0551ecb06b`.

## Решение и граница

По предоставленному владельцем официальному разъяснению Yandex Cloud отдельного ожидания 24 часа нет, если каждый запрос содержит `x-data-logging-enabled: false`. Поэтому только закрытый admin-only SITE QA с фиксированными RU/EN synthetic fixtures игнорирует результат `no_logging_wait` общего `AISettings.gate()`.

Общий `AISettings.gate()` не изменён. Обёртка сначала вызывает его и возвращает без изменений любую причину, кроме `no_logging_wait`. Она создаётся внутри `LetterSiteQA`; включить её через query, form, fixture или environment parameter нельзя. Обычные cover-letter routes, resume AI, interview AI, vacancy match, real-data admission и другие runtime её не получают.

## Обязательный transport boundary

`x-data-logging-enabled: false` остаётся обязательным для каждого provider request. Production adapter устанавливает header, а отдельный HTTP worker отклоняет отсутствующее, boolean или иное значение до создания сетевой сессии. Это исправление не ослабляет transport boundary и не запускает provider calls.

Разъяснение не означает отсутствия любого хранения: возможно кратковременное provider-side хранение, необходимое для обработки запроса и генерации ответа. Номер и дата обращения поддержки здесь не указываются, поскольку в доступных материалах их нет.

## Не является активацией

Изменение не является legal activation. `REAL_DATA_SUPPORTED=False`, legal policy `DRAFT`, admin allowlist, synthetic verification, shared runtime/DB gates, budgets, limits, circuit breaker, idempotency, operation binding и 10-минутный signed preview сохраняются. Real-data AI остаётся закрыт. До отдельного разрешения live provider test и deployment имеют статус `NOT_RUN`; paid Alice calls = 0.

Historical evidence r1 не меняется. Новый `docs/evidence/ai-005-site-qa-no-logging/change_boundary.json` явно фиксирует только successor для SITE QA service и новой узкой gate-обёртки.
