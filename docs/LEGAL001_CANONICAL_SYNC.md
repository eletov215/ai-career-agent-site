# LEGAL-001 — синхронизация технической приёмки / 24 сентября 2026

## Финальное состояние

После production QA, исправления layout/heartbeat, закрытия T-05/T-06 и post-merge main CI пакет переведён из `IMPLEMENTED + CI_PASS` в `TECHNICAL_ACCEPTED / LEGAL_PENDING`. Accepted technical main: `309afe0089356e6fb0d1c205ce7ca2c7cb682ae2`; tree: `2616a3b15df09f85bf7ae261e605356fb9f52f9d`. Main CI #324, Package preflight #11 и LEGAL-001 PostgreSQL verification #5 — SUCCESS.

Production runtime evidence `28db01b719003149a0d616934e469b1b83c0237f` остаётся применимым: compare до accepted main содержит только verification workflow/guard/tests. Application runtime не менялся. Production legal policy по-прежнему DRAFT/NOT_ACTIVE, real-data Alice CLOSED, paid provider calls=0.

Canonical versions: PLAN 1.6.5, PASSPORT 2.80, SOURCE_AUDIT/CANONICAL_DOCUMENTS/ROADMAP 1.6.5, NEXT_PACKAGE_PREPARATION 1.6. Исторический `LEGAL001_DEFERRED_DECISION.md` не переписывается.

## Следующий gate

Только owner/legal facts → final Terms/Privacy/AI-consent → reviewed policy activation → controlled real-data AI-005 test → human quality acceptance. AI-006 не начинается до полного закрытия AI-005.

---

# LEGAL-001 — синхронизация проверок документации / 22 сентября 2026

## Причина повторного красного CI

CI #304 успешно проверил технический код `fe3a7e1b553ccc9ebb5b956efce3779287291c04`. Последующие коммиты обновили документы, но не все связанные проверки. В #305 из актуального блока исчезли маркеры принятого JOB-001; #306 восстановил их, но provider guard всё ещё требовал старые версии PLAN 1.6.3 / PASSPORT 2.78. Дополнительно LEGAL-001 guard не разрешал переход от NEEDS_VERIFICATION к подтверждённому CI_PASS, а добавление текста в историческое юридическое решение нарушало его byte-level защиту.

## Исправление

Актуальные версии PLAN 1.6.4 / PASSPORT 2.79 проверяются по первой таблице метаданных, а не по совпадению в старой истории. Датированный DOC-001 checkpoint 1.6.3 / 2.78 в сохранённой части плана остаётся историческим, не текущим инвентарём. Активный инвентарь задают верхние блоки PLAN/PASSPORT и CANONICAL_DOCUMENTS 1.6.4.

LEGAL-001 CI_PASS сопоставляется с отдельной записью `evidence/legal-001/ci304_verified_summary.json`, точным SHA, деревом и результатами шагов. Принятие, deploy и production QA не выводятся из этого статуса. Исторический `LEGAL001_DEFERRED_DECISION.md` сохранён в исходных байтах; дополнение о технической реализации вынесено сюда и в текущие LEGAL001_* документы. Юридические решения владельца остаются открытыми.

Добавлен независимый ранний прогон всех девяти package guards и негативные тесты статусов. Основной CI, полный pytest, PostgreSQL, security, privacy, backup/restore и ограничения платных jobs не отключаются.

## Граница этого исправления

Изменяются документация, её validators, тесты и ранняя CI-проверка. Application runtime, consent persistence, migration 0021, AI policy, provider transport и Render variables не изменяются. Реальные данные Алисе не разрешены. Платных provider calls: 0.

После нового зелёного CI разрешён владельцем merge в main. Post-merge CI и проверка на сайте выполняются отдельно; этот документ не утверждает, что они уже прошли.
