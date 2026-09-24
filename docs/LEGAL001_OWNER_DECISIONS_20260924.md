# LEGAL-001 — owner decisions / 24 сентября 2026

| Поле | Решение владельца |
|---|---|
| Статус | PARTIAL_DECISIONS_RECORDED / LEGAL_ACTIVATION_PENDING |
| Фактическое управление | Россия |
| Первая страна запуска | Россия |
| Беларусь / другие страны СНГ | Будущий отдельный этап; не входят в первый launch scope |
| Аудитория | Физические лица, ищущие работу |
| Работодатели как пользователи | Нет |
| Минимальный возраст | **18+** |
| Коммерческая модель | Free + платный Standard |
| Контакт по юридическим вопросам / ПД | `eletov215@gmail.com` |
| Целевая production cloud | **Yandex Cloud, регион Россия** |
| Домен | PENDING / не выбран |
| Оператор / правовая форма / реквизиты | PENDING / не определены |

## 1. Что это решение разрешает

Можно реализовать HOST-001 как fail-closed Yandex Cloud Russia foundation,
подготовить российскую data-localization architecture и продолжить составление
матрицы данных/процессоров. Возрастной launch scope теперь однозначно 18+; DOB
для этого решения собирать не требуется.

## 2. Что решение не разрешает

Это не финальная Privacy Policy, Terms, AI consent или правовое заключение.
Оператор/форма бизнеса, реквизиты, домен, платёжный провайдер Standard, финальная
retention/offsite-backup policy и договорные роли processors/subprocessors ещё
не определены. Нельзя переводить `services/legal_policy.py` в ACTIVE или менять
`domain/ai.py::REAL_DATA_SUPPORTED=False`.

## 3. Инфраструктурная граница

Первичная запись/хранение данных российских пользователей планируется в Yandex
Cloud Russia. HOST-001 использует Compute + Managed PostgreSQL в российских
availability zones и Lockbox. Offsite backup destination остаётся OPS-002 gate
и до запуска также должен быть согласован в рамках российского launch scope.

Render/Neon не объявляются российским production data store. Фактический перенос
данных с текущего staging/production контура относится к MIG-001 и не выполняется
этим решением.

## 4. Следующие нерешённые owner/legal facts

1. Оператор: физлицо/ИП/компания, полное наименование и реквизиты.
2. Коммерческий домен и публичные contact URLs.
3. Платёжный провайдер и правила Standard/BILL-001.
4. Финальный срок хранения active owner content, backup lifecycle и incident
   contact/process.
5. Финальные Terms, Privacy Policy, отдельное AI-consent wording/version/hash.
6. Отдельная оценка Беларуси/других стран СНГ перед их добавлением.

До закрытия этих пунктов LEGAL-001 остаётся `TECHNICAL_ACCEPTED / LEGAL_PENDING`.
