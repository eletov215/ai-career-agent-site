# AI Career Agent — справочник состояний источников SEARCH-004

| Поле | Значение |
|---|---|
| Документ | SEARCH004_SOURCE_STATE_REFERENCE |
| Пакет | SEARCH-004 |
| Версия | 1.0 |
| Дата | 10 августа 2026 |
| Статус | CANDIDATE CONTRACT |

## 1. Контрольный статус

Этот contract предназначен только для безопасного пользовательского UI. Он не заменяет admin telemetry SEARCH-005.

## 2. Состояния

| Код | Пользовательский смысл | Selectable |
|---|---|---|
| `available` | Live search настроен или успешно ответил | Да |
| `cached` | Выдача берётся из сохранённого PostgreSQL cache | Да |
| `degraded` | Данные/часть функции доступны, но обновление или текущий request прошли с ограничением | Да |
| `auth_required` | Для самого поиска действительно требуется подключение аккаунта | Нет до OAuth |
| `temporarily_unavailable` | Source сейчас не участвует в поиске | Нет |

## 3. Поля SourceState

```text
key
title
state
selectable
selected
label
detail
loaded
reported_total
auth_required_for_actions
```

`available`, `status_text` и `note` остаются compatibility properties для существующего Jinja markup.

## 4. Правила Trudvsem

`trudvsem` использует PostgreSQL cache и не получает label live search.

```text
fresh cache                         -> cached
cache + running/queued refresh      -> cached с пояснением
stale cache или failed refresh      -> degraded, selectable
cache empty + sync enabled          -> degraded, selectable; update ставится в durable queue
cache empty + sync disabled         -> temporarily_unavailable, non-selectable
```

## 5. Правила live providers

HH, SuperJob и Reed:

```text
configured, до запроса              -> available
success in current snapshot         -> available
failure in current snapshot         -> degraded
public search not configured        -> temporarily_unavailable, non-selectable
OAuth-only source                   -> auth_required
```

HH/SuperJob могут иметь `auth_required_for_actions=true`, оставаясь `available` для public vacancy search.

## 6. Source selection

Route вызывает только `selectable_source_keys(states)`. Явно запрошенный unavailable source удаляется из текущего search request и получает нейтральное пользовательское уведомление.

## 7. Безопасность

Public contract запрещает выводить:

```text
API keys
OAuth tokens
Authorization headers
environment variable names
provider response bodies
exception messages
tracebacks
internal hostnames
```

Допускаются только source title, neutral state copy и bounded counters.

## 8. Rollback

Удаление helper/presenter возвращает прежний binary available UI. Database data и SEARCH-003 snapshots не затрагиваются.

## 9. Следующее действие

Подтвердить contract через dedicated CI gate и Render source-state smoke.

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 10.08.2026 | Введён public source-state contract SEARCH-004. |
