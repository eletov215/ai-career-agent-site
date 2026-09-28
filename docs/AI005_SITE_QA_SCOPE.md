# AI-005 SITE QA — scope / r1 candidate

Дата: 27 сентября 2026. Рабочая основа: main `b828596c893d59a544f9678d7b45ab6ed7f44230`, tree `05fc57dd0294cd5814637cc6e61e864f2bba9d2d`.

## Решение владельца

После отдельного аудита владелец разрешил реализацию synthetic SITE QA. Эта работа идёт перед созданием Yandex Cloud infrastructure. Она не разрешает платные вызовы, изменения production consent, real-data activation, миграцию рабочей БД или AI-006.

## Результат пакета

Закрытый раздел `/admin/ai/letters/site-qa`: server-selected RU/EN fixtures, параметры short/full и professional/friendly, preview, одна action-кнопка без новой checkbox, существующий production YandexAliceProvider/LetterRuntime/validation, proposal, редактирование, принятие/отклонение, версии, сравнение, TXT.

Код приложения не импортирует поддельный provider. В тестах подменяется только HTTP transport настоящего адаптера. Оба новых переключателя по умолчанию равны 0; live-включение требует отдельного решения и существующих AI/runtime gates. Обычный LegalLetterAdmission и `REAL_DATA_SUPPORTED=False` остаются неизменными.

## Граница приёмки

IMPLEMENTED, CI_PASS, DEPLOYED, SITE_QA_PASS, LIVE_PROVIDER_PASS, QUALITY_PASS и LEGAL_PASS — разные статусы. Пакет не переводит полный AI-005 из IN_PROGRESS / LIVE_NOT_ACCEPTED в COMPLETE. Финальная синхронизация семи канонических документов выполняется после приёмки пакета; исторические свидетельства не переписываются.

## Не входит

Нет terraform apply, VM/Managed PostgreSQL/IP/Lockbox creation, production DB migration, billable Alice call, изменения DRAFT policy или реальных аккаунтов/согласий. Новые тестовые владельцы создаются только при явно разрешённом POST в включённом QA-разделе; запуск приложения не создаёт записей.

## Successor: no-logging wait

Successor от 28 сентября 2026 снимает историческое 24-часовое ожидание только внутри этого fixed synthetic SITE QA. Общий gate и остальные AI surfaces не меняются; обязательный `x-data-logging-enabled: false` сохраняется. Подробная граница зафиксирована в `AI005_SITE_QA_NO_LOGGING.md`; это не legal activation и не разрешение real-data AI.
