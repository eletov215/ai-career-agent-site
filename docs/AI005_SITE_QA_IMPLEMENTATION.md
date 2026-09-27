# AI-005 SITE QA — implementation / r1 candidate

## Архитектура

`routes/admin_sources.py` регистрирует дочерний blueprint с отдельным URL namespace. Четыре добавленные строки — единственное изменение существующего runtime-файла. `app.py`, исходные letter routes/services/repositories, provider/runtime/admission и все predecessor guards сохранены. Новый guard проверяет их Git blob hashes и точное восстановление исходного admin_sources.py после удаления зарегистрированной вставки.

`LetterSiteQA` создаёт две постоянные внутренние synthetic identities на администратора: RU и EN. Идентификаторы получаются HMAC от серверного ключа и actor ID. Email, normalized_email, password, auth session, OAuth identity, auth token и consent не выдаются. Для совместимости с существующим repository допуска внутренние записи имеют active/verified технический статус; это не почтовая проверка реального пользователя. Внешний tester обязан иметь настоящий активный подтверждённый allowlisted account.

Каждое действие проверяет tester и принадлежность письма его synthetic workspace. Перед dispatch и внутри atomic delivery повторно проверяется persisted actor. Глобальный current_user не подменяется. При чтении источника используется только synthetic owner, не профиль tester. Факты и вакансия должны точно совпадать с hash-verified `letter_synthetic_cases.json`; свободный ввод fixture, prompt или source не поддерживается.

## Идемпотентность

Подготовка письма привязана к подписанному server intention. Два параллельных одинаковых POST дают одно письмо; изменение параметров при прежнем intention отклоняется. Новое письмо является явным новым намерением, не повтором прежнего вызова.

`_FixedIntentionGenerator` расширяет только preview существующего генератора: operation вычисляется детерминированно для письма, issued/expires привязаны к created_at с окном 600 секунд. Повтор preview, refresh или перезапуск сервиса не создаёт новую operation и не продлевает окно. Общий persistent ledger предотвращает повторный dispatch. Истечение retention ledger не открывает старый ticket, поскольку его срок ограничен десятью минутами.

LetterRuntime выполняет один dispatch, без автоматического retry timeout/unknown. Proposal и учёт успеха коммитятся одной транзакцией. Правки пользователя никогда не добавляются в исходный provider payload. Бюджеты постоянны по synthetic owner, то есть отдельно для RU/EN; общие global budgets сохраняются. Это не утверждение об отдельной aggregate-квоте на реального tester.

## Интерфейс и сохранение

Новый шаблон использует base.html приложения, собственный scoped CSS и escaped text. После preview — одна кнопка генерации, без per-call checkbox. Подтверждение просмотра при сохранении версии сохранено отдельно. Непринятое предложение не экспортируется как готовое письмо. Отклонение не переписывает существующий текст. Ручная правка принятого письма создаёт следующую версию через обычный CoverLetterService.

## Ограничения

Автоматическая проверка формы, цитат и чисел не доказывает semantic grounding. Synthetic success не доказывает качество на реальном пользовательском содержимом. Нет автоматической очистки новых workspace; максимум писем ограничен MAX_LETTERS. Удаление настоящего tester блокирует доступ, но не удаляет отдельные synthetic owner rows автоматически. Сюда нельзя вводить реальные персональные данные. Работы по lifecycle/cleanup не должны затрагивать единственный рабочий аккаунт владельца.

Существующий общий preview-шаблон с checkbox не меняется: ordinary real-data path закрыт. Новый QA action не ослабляет LegalLetterAdmission и не делает существующий общий путь доступным.
