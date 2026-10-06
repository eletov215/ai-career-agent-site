# AI Career Agent — подготовка продолжения

<!-- DOC001-SUCCESSOR-20261006:START -->
## Текущий канонический successor / 6 октября 2026

> Этот блок является актуальным successor-состоянием после JOB-004 и infrastructure PR #74/#75. Датированные acceptance-блоки ниже сохраняются без переписывания для historical evidence и package guards.

| Поле | Текущее состояние |
|---|---|
| Current main | `cc12b7de80b73f372aa185fadc1e49f58e9c2817` |
| Schema | `20261002_0023` |
| JOB-004 | COMPLETE; production SITE QA accepted; migration NOT_APPLICABLE |
| HOST/INFRA | Stage B + Stage C preparation merged; Yandex apply/resource creation NOT_RUN |
| Current Render | `dep-db2ekrbncjis73ciogcg` LIVE on current main |
| Stage C field test | NEXT / separate owner approval required; recommended test ceiling remains 500 RUB |
| REED-COMPAT-001 | NEXT inside Russia-hosted field-test window; NOT_RUN |
| Trudvsem | non-blocking diagnostic during Russia field test; foreign-hosting cause NOT_PROVEN |
| DOMAIN-001 | PENDING before beta |
| Production transactional email | P0 pre-release gate / PENDING; AUTH logic remains COMPLETE |
| MIG-001 | NOT_AUTHORIZED / NOT_RUN |
| SRC-001 | restored to explicit pre-release sequence; PLANNED after migration evidence |
| Legal | TECHNICAL_ACCEPTED / LEGAL_PENDING; policy DRAFT / NOT_ACTIVE |
| Real-data Alice | CLOSED; `REAL_DATA_SUPPORTED=False` |

### Активная очередь

1. Stage C — короткий synthetic field test в Yandex Cloud Russia после отдельного owner approval на billable resources.
2. В том же окне — `REED-COMPAT-001` и ограниченное non-blocking наблюдение доступности Trudvsem из России.
3. `DOMAIN-001` + production transactional email gate: project-owned sender/domain, SPF/DKIM/DMARC и полный verification/reset E2E.
4. `MIG-001` — отдельный owner-gated перенос production с rollback/recovery evidence.
5. `SRC-001` — подключение новых источников; Reed является первым конкретным кандидатом только если `REED-COMPAT-001` пройден.
6. Legal activation / controlled real-data AI остаются отдельным gate и могут готовиться параллельно, но real-data AI не открывается автоматически инфраструктурой.
7. `REL-001` — финальная предрелизная проверка MVP 1.0.

### Email boundary

`AUTH-001 COMPLETE` сохраняется как исторически принятая account/token/session/verification business logic. Это **не равно production email readiness**. Personal Gmail API остаётся staging-only. Владелец сообщил, что текущие verification messages больше не приходят; точная причина нынешнего сбоя этим docs-sync не объявляется доказанной. Репозиторий уже фиксирует риск истечения/отзыва Google Auth Platform Testing refresh token. До beta/commercial release обязателен production-grade domain sender и новый E2E.

Актуальные successor-документы: `docs/PACKAGE_REGISTRY_CURRENT.md`, `docs/AUTH_PRODUCTION_EMAIL_GATE_20261006.md`, `docs/HOST001_STAGE_C_FIELD_TEST_PLAN_20261006.md`.
<!-- DOC001-SUCCESSOR-20261006:END -->

| Поле | Значение |
|---|---|
| Версия / дата | 1.6 / 24 сентября 2026 |
| Принято | LEGAL-001 technical foundation accepted; AI-005 r1 document part remains accepted in its recorded scope |
| Текущая разработка | LEGAL-001 TECHNICAL_ACCEPTED / LEGAL_PENDING; полный AI-005 IN_PROGRESS / LIVE_NOT_ACCEPTED |
| Схема | `20260922_0021` |
| Accepted technical main | `309afe0089356e6fb0d1c205ce7ca2c7cb682ae2` |

## 1. Следующий разрешённый этап

Инженерная часть consent/admission закрыта. Не требуется повторять consent mutation, ZIP/TXT или viewport QA без нового дефекта. Следующий этап — не AI-006 и не платный real-data call, а сбор фактических юридических исходных данных владельца и подготовка финальных документов/production policy.

До отдельного решения должны быть определены: фактический оператор и контактный канал, юрисдикция и страны запуска, аудитория/возраст, места приложения/БД/backup, processors/subprocessors и cross-border route, final retention. После этого готовятся Terms, Privacy Policy и AI-consent version; их активация должна быть отдельным reviewed code change. Environment flag не может заменить эту процедуру.

После ACTIVE legal policy разрешается только ограниченная real-data AI-005 проверка. Затем обязательна human quality acceptance настоящих писем. Только после этого полный AI-005 может стать COMPLETE и открывается AI-006.

Технические evidence limits остаются записанными: natural 24h cleanup cycle NOT_RUN; historical pre-migration production backup BLOCKED by missing historical evidence; baseline consent record ID not captured. Новая резервная копия не должна использоваться как доказательство старой.

## 2. Исторический r2 technical candidate / 20 сентября 2026

## 1. Что уже написано

Вместо очередного локального шаблона добавлены новый writer-контракт, минимальная проекция источников, подписанный предварительный просмотр, настоящий вызов интерфейса YandexAliceProvider, общие ограничения затрат, повторная проверка владельца/источника и атомарное сохранение предложения. В тестах транспорт имитируется; новый настоящий ответ Алисы ещё не получен.

## 2. Ближайший gate

После отдельного разрешения публикации: ветка/PR, обычный CI с полным набором, новыми HTTP/ledger тестами и PostgreSQL. Затем отдельное разрешение на ограниченный платный прогон scripts/ai005_synthetic_probe.py вне рабочей базы. По умолчанию скрипт лишь пишет preview и не делает запросов. Перезапуск команды с платным флагом — новая операция и потенциальный новый расход, а не безопасный повтор старой.

Синтетический прогон проверяет техническую совместимость нового запроса, но не доказывает качество для любых профилей. Нужны ручные рубрики RU/EN, короткого/полного письма, тона, фактов/чисел, отсутствия вымышленных достижений и соответствия вакансии. При отказе схемы или неестественном тексте исправляем контракт и повторно проверяем, не заменяя модель шаблоном.

## 3. Затем LEGAL-001

Согласовано перенести юридическую работу между технической реализацией и допуском реальных данных. Пока отсутствуют: страна фактического управления, страны первой аудитории, возраст/тип клиентов, режим регистрации/платности, фактический оператор и канал обращений; регионы приложения/БД/бэкапов и маршрут данных требуют отдельной проверки. ИП/компания не выдумываются; вопрос формы деятельности решается отдельно по выбранной юрисдикции.

В рамках допуска предстоит реализовать и проверить реальные версии документов/согласий, их запись/отзыв, admission-policy и разрешённую маршрутизацию. Текущая галочка подтверждает просмотр технического payload, а не заменяет правовое основание. ClosedLetterAdmission остаётся в приложении; старые синтетические runtime-флаги не являются допуском реальных данных.

## 4. Условия окончательной приёмки

Новый CI и тесты сайта, разрешённая обработка реальных данных, настоящий ответ модели и человеческая оценка качества обязательны. Простое отсутствие ошибок редактора, старый AI-BENCH или зелёные фиктивные ответы не закрывают AI-005. У пользователя пока пустой профиль: после допуска понадобится подтверждённый реальный источник; заполнять его вымышленными данными для нынешней приёмки не нужно.

## 5. Открытые эксплуатационные вопросы

Не подтверждены реальная резервная копия Neon до прошлой миграции и восстановление рабочей базы. Отсутствующий второй аккаунт остаётся исключением ручной изоляции. Доставка писем регистрации, свободные живые AI-003/004 и финальный production-хостинг не считаются автоматически готовыми благодаря r2.

## Исторический снимок предыдущей версии / 17 сентября 2026

Следующий текст сохранён полностью как история; актуальный статус и очередность заданы выше.

# AI Career Agent - Next-package preparation / 1.3

| Field | Value |
|---|---|
| Date | 2026-09-17 |
| Full package | AI-005 IN_PROGRESS |
| Delivery | r1 NEEDS_VERIFICATION; LIVE_NOT_ACCEPTED |
| Base / candidate schema | 0019 / 0020 |

## 1. Current request and audit

The owner explicitly requested implementation after JOB-001 acceptance. Current main c095bfb, 608-file tree6bb34ab, source schemas, access/privacy and fixed-fixture AI runtime were inspected. Technical ownership/storage prerequisites are available; general real-data generation is not already present. No keys/payments or new user secrets are required to write offline/document code.

## 2. Implemented and remaining

AI-005 r1 general document workflow is now a local candidate; full AI-005 is IN_PROGRESS, not complete. Native editing, selected local factual templates, confirmed version history, compare/delete/TXT, source snapshots and privacy are implemented. The generic evidence-selection model contract is offline. Actual arbitrary-input Alice integration, admission/consent, accounting/idempotency and general writing quality remain to implement. An environment flag must not substitute for that work. The original requirements and order are preserved; no restricted-reference completion is claimed.

## 3. Next action

Review delivered scope/code. Publish only on the owner's later instruction, run new CI then obtain a real recovery point before migration0020/site tests. Keep public AI manual. Continue the outstanding AI-005 live-runtime work and its quality/legal gates; do not advance to AI-006 under a false completed-AI-005 status. Earlier next-package-not-started statements below are history only.

## 4. Historical predecessor (unchanged dated source)

The following reflects the previous release. It does not override the active sections above.

# AI Career Agent - next-package preparation / 1.2

| Field | Value |
|---|---|
| Version and date | 1.2 / 2026-09-17 |
| Preparation status | Technical prerequisite JOB-001 satisfied; next feature design pending |
| Accepted base | `c095bfb70bad5b1ba22cd9b1aeac1795a0b59c4c`; schema20260917_0019 |
| Next package | AI-005 - cover-letter generation and versions |
| Implementation started | No |
| Public/live activation | Not approved; existing gates remain |

## 1. Agreed feature scope

PLAN_CURRENT's AI-005 card requires a personalized editable draft, short/full modes, tone/language, editor, versions and export; sending only on explicit user action. Letters remain associated with the vacancy. Unsupported facts, automatic send and loss of history are prohibited. Dependencies remain AI-001, PROF-001, AI-004 and JOB-001; none is removed.

JOB-001 was deliberately implemented first at the owner's instruction and is now accepted. The previous ordering conflict is resolved. Saved source content, owner identity, canonical confirmed profile and editable resume content remain distinct; a saved note is not automatically a confirmed candidate fact.

## 2. Required design before writing AI-005

Re-read actual main, approved current documents, the saved-vacancy access/deletion rules and the limited AI-001/AI-004 input contracts. Define letter ownership and immutable source/provenance binding, edits/version conflict behavior, comparison/export/delete, and the effect of deleting a linked vacancy. Choose contracts from existing verified fields, not presumed database columns.

A live implementation needs arbitrary real-input handling, candidate-fact evidence checks, hallucination/unsupported-number controls, token/cost/idempotency/failure behavior, consent/data-routing and quality acceptance. Existing AI-001/AI-004 reference foundations are not a proof that those paths already work. Do not silently substitute another pinned demonstration for the complete planned feature. A restricted reference-only delivery would need a separate explicit scope decision.

## 3. Publication, safety and next action

Publish the local JOB-001 closure only on instruction and run its ordinary CI. Then begin AI-005 as a separate package after a fresh source audit and an explicit implementation request. LEGAL-001 remains deferred and public AI unavailable/manual. No billable run, service payment, free-form real-data dispatch, auto-apply or live activation is authorized here. Before any new migration, obtain a confirmed real recovery point; CI restores do not replace it.

## 4. Version history

1.2: JOB-001 accepted; prerequisite resolved, live-feature design/activation gates remain. 1.1: owner approved JOB-001 first and the rebuilt candidate was delivered. 1.0: AI-004 closure identified the original ordering conflict.

## 5. Historical preparation / 1.1

The following retains earlier decisions and their dated state. Pending JOB-001 and unresolved-order labels are historical, not current.

# AI Career Agent - next-package preparation / 1.1

| Field | Value |
|---|---|
| Date | 2026-09-17 |
| Order | JOB-001 before AI-005, explicitly approved by the owner |
| Current implementation | JOB-001 r1.1 REBUILT, local NEEDS_VERIFICATION |
| Next | AI-005 only after JOB-001 acceptance and a fresh source audit |

## 1. Current decision and scope

The earlier proposal below is now approved in the project conversation. JOB-001 provides a durable owner-bound vacancy snapshot on which the future letter/history can depend. AI-005 itself is not implemented by this candidate. Real-data AI/legal/quality activation stays separately gated; a real saved vacancy must not be given the reference fixture's67/71 score.

## 2. Next action

Deliver the rebuilt archive first; do not publish it during the recovery request. Subsequent upload requires the user's publication instruction, then ordinary CI with installed Flask and PostgreSQL, a confirmed recovery point before migration0019, and JOB001_RUNBOOK staging tests. No new paid provider benchmark is needed for saved vacancies.

## 3. Historical preparation / 1.0

The following proposed-order and no-code statements describe the earlier AI-004 closure, not the current approved implementation. Its dependencies and safety requirements remain valid.

# AI Career Agent — подготовка следующего пакета

| Поле | Значение |
|---|---|
| Документ | NEXT_PACKAGE_PREPARATION |
| Версия и дата | 1.0 / 17 сентября 2026 |
| Статус | ПОДГОТОВКА; реализация не начата |
| Принятая основа | AI-004; схема 20260916_0018 |
| Следующий номер AI | AI-005 — генерация и версии сопроводительного письма |
| Невыполненная зависимость | JOB-001 — серверные сохранённые вакансии |
| Требуемое решение | Подтвердить порядок реализации с учётом зависимости |

## 1. Что прямо записано в плане

Карточка AI-005 предусматривает персонализированный редактируемый черновик письма: короткий и полный варианты, тон и язык, редактор, версии и экспорт. Отправка — только по явному действию пользователя. Письмо хранится рядом с вакансией; неподтверждённые факты и автоматическая отправка недопустимы. Зависимости: AI-001, PROF-001, AI-004 и JOB-001.

Карточка JOB-001 предусматривает замену localStorage серверной карточкой-снимком: SavedVacancy, исходные площадки, сохранённое содержание, заметки, соответствие и состояние устаревания. Повторы не создаются; снимок остаётся после исчезновения исходной публикации; доступ принадлежит только владельцу. Зависимости AUTH-001, DATA-002 и SEARCH-001 выполнены. Сам JOB-001 остаётся запланированным.

Источник этих требований — подробные карточки PLAN_CURRENT в проверенном GitHub. Существование кнопки сохранения не доказывает завершение серверного хранения.

## 2. Вывод о готовности

Это архитектурный вывод из перечисленных зависимостей, а не ранее принятое владельцем решение: полноценному AI-005 требуется постоянная сохранённая вакансия, с которой можно связать письмо и его историю. В прежней очереди JOB-001 стоит позже AI-005, хотя является его обязательной зависимостью. Поэтому объявлять полный AI-005 готовым к немедленному старту нельзя.

Закрытие AI-004 не устраняет зависимость от JOB-001. Оно также не включает свободный ввод настоящего опыта и живую генерацию Алисы автоматически.

## 3. Предлагаемый порядок — пока не утверждён

Предложение: сначала реализовать JOB-001, затем вернуться к полноценной интеграции AI-005. Так сохраняются требования к принадлежности вакансии пользователю, её снимку и связи с историей писем.

Изменение очереди должно быть отдельно согласовано и отражено новой MINOR-версией плана согласно его правилам. Выпуск 1.5.7 фиксирует только завершение AI-004 и подготовку: порядок не изменён, ни одна зависимость не удалена, новый код не написан.

Альтернативная ограниченная основа писем на закреплённых примерах потребует отдельного согласования объёма и критериев последующей интеграции. Её нельзя выдавать за готовность полного пользовательского сценария AI-005.

## 4. Что проверить перед реализацией JOB-001

Нужно повторно прочитать актуальный main и изучить реальное поведение кнопок сохранения и localStorage, единый контракт вакансии SEARCH-001, ссылки площадок и идентификаторы дублей, авторизацию владельца, экспорт и удаление данных. Схема хранения и уникальность должны опираться на существующие данные, а не на предположительные поля.

Связь с отчётом AI-004 допустима только с проверкой владельца и согласованности исходных данных. Нельзя предполагать, что каждая реальная вакансия уже имеет живую AI-оценку.

Будущие проверки: повторное сохранение без дублей; чужой пользователь; исчезновение публикации; сохранность снимка; повторный вход и другое устройство; заметки и устаревание; экспорт и удаление; отсутствие регрессий. Миграция и откат должны быть рассмотрены до развёртывания. Перед изменением рабочей базы потребуется подтверждённая резервная копия.

Имена новых файлов, таблиц, маршрутов и номер миграции здесь не назначаются: это предмет следующего аудита и реализации.

## 5. Неизменные ограничения

LEGAL-001 остаётся отложенным. Публичный AI выключен; техническая готовность не подменяет юридическое решение и согласие пользователя. Свободное интервью, произвольное сопоставление и живые письма требуют отдельной разработки, проверки качества и допуска реальных данных.

Доставка verification email и полевое восстановление базы остаются самостоятельными задачами. Этот документ не разрешает новые платные вызовы провайдера, оплату инфраструктуры или коммерческий запуск.

## 6. Следующее действие и журнал версий

Нужно принять решение о JOB-001 перед AI-005, затем обновить последовательность и проверить фактический GitHub перед изменением кода. Версия 1.0 фиксирует только подготовку и выявленное противоречие зависимостей.
