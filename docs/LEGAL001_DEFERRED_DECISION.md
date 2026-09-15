# LEGAL-001 — отложенное решение владельца

| Поле | Значение |
|---|---|
| Документ | LEGAL001_DEFERRED_DECISION |
| Версия | 1.2 |
| Дата | 2026-09-15 |
| Статус | ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА |
| Блокирует | публичное включение AI, финальную публикацию юридических текстов и коммерческий релиз |
| Не блокирует | техническую разработку AI-001..AI-006 в fail-closed режиме |

## 1. Решение владельца

На 2026-09-14 владелец проекта прямо подтвердил, что юридическое оформление сервиса пока не определено и к этому вопросу нужно вернуться позднее. Никакие недостающие реквизиты не считаются известными по умолчанию.

Не определены:

- страна/юрисдикция оператора;
- юридическая форма оператора: физическое лицо, самозанятый, ИП или организация;
- окончательное наименование/ФИО оператора и обязательные регистрационные реквизиты;
- контактный адрес/канал для юридически значимых обращений;
- страны первого публичного запуска;
- финальная схема размещения и трансграничной обработки персональных данных;
- финальные тексты пользовательского соглашения, политики конфиденциальности и AI-согласия с учётом выбранной юрисдикции.

Имя `Шекунов Д.С.`, использованное как имя human reviewer в AI-BENCH, **не является автоматически реквизитом оператора** и не должно переноситься в публичные юридические документы без отдельного решения владельца.

## 2. Технический режим до решения

До закрытия LEGAL-001:

```text
AI_ENABLED=0
AI_KILL_SWITCH=1
AI_SYNTHETIC_ACCESS_ENABLED=0
```

AI-001 может реализовывать provider interface, structured-output contract, технические лимиты, usage/cost ledger, circuit breaker и manual fallback. Однако пользовательские запросы с реальными данными не должны отправляться AI-провайдеру.

Юридические страницы/consent UX могут проектироваться как черновики и тестироваться на синтетических данных, но не должны объявляться финальными или использоваться как доказательство согласия реальных пользователей.

## 3. Обязательный gate перед публичным AI

Перед включением AI для реальных пользователей требуется отдельный пакет/решение, которое минимум фиксирует:

1. оператора и его юрисдикцию;
2. перечень рынков публичного запуска;
3. фактические категории данных и процессоров;
4. data-location/transborder схему для production;
5. сроки хранения и процедуры отзыва/удаления;
6. версии публичных Terms/Privacy/AI consent;
7. порядок versioned acceptance;
8. owner/legal review этих текстов.

Только после этого можно выполнять activation checklist AI-001/AI-002. Техническая готовность AI сама по себе не заменяет LEGAL-001.

## 4. Следующее действие

LEGAL-001 остаётся в статусе `ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА`. AI-001 технически завершён; следующий пакет - AI-002 после загрузки свежего GitHub ZIP. Возврат к LEGAL-001 обязателен до public/real-data AI, платных подписок или коммерческого релиза.


## 5. Scope of this deferral / 1.5.0

This is an explicit sequencing change requested by the owner, not legal clearance. PLAN_CURRENT moves to a MINOR version (1.5.0) because technical AI development now precedes completion of LEGAL-001. The release/real-data gate is unchanged.

AI-001 accepts only eight pinned synthetic fixture IDs. There is no `AI_LEGAL_APPROVED` shortcut in this package: an environment variable cannot turn a fictional consent into a real one. A future reviewed implementation must add real-data entry points and actual owner-bound, versioned consent checks.

The earlier LEGAL-001 prototype and candidate documents were never delivered/deployed. They are not included in this code package, and their proposed migration was not applied. No fictitious operator data or consent acceptance is added to any account.

Return trigger: before public AI activation, paid subscriptions or commercial release, whichever happens first. Responsible decision-maker: project owner. Due date: not supplied; do not invent one.

## 6. Version log

| Version | Date | Change |
|---|---|---|
| 1.2 | 2026-09-15 | AI-001 closure recorded; unresolved operator/jurisdiction questions unchanged; return trigger preserved before public AI/subscriptions/release |
| 1.1 | 2026-09-14 | Verified deferral; no boolean legal bypass; technical-only AI-001 and mandatory return trigger |
