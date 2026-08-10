# AI Career Agent — реализация SEARCH-004

| Поле | Значение |
|---|---|
| Документ | SEARCH004_IMPLEMENTATION |
| Пакет | SEARCH-004 — canonical `/vacancies` и честные состояния источников |
| Версия | 1.0 |
| Дата | 10 августа 2026 |
| Статус | НУЖНА ПРОВЕРКА |
| Основа кода | `ai-career-agent-site-main (14).zip` — актуальный GitHub `main` |
| Production schema | `20260809_0007` — без новой migration |

## 1. Контрольный статус

SEARCH-004 реализован поверх завершённых SEARCH-001/002/003. Код готов к GitHub Actions и Render smoke, но до этих доказательств пакет не переводится в ВЫПОЛНЕНО.

## 2. Цель и границы

Цель пакета — сделать `/vacancies` единственным публичным маршрутом поиска, сохранить работоспособность старых ссылок `/vacancies/internal` и показывать пользователю безопасное фактическое состояние каждого источника.

В пакет входят:

- canonical GET route `/vacancies`;
- permanent method-preserving compatibility redirect `/vacancies/internal` с точным сохранением raw query string;
- сохранение повторяющихся `source`, `snapshot`, `page`, filters, sort и period;
- обновление generated forms, pagination, navbar, footer и home CTA URL;
- SEO canonical link на `/vacancies`;
- безопасный source-state contract;
- явное различие live search и PostgreSQL-backed Trudvsem cache;
- исключение недоступного provider из текущего search request;
- route/source-state regression tests и отдельный CI gate.

Не входят: admin source center, новые providers, OAuth redesign, SEARCH-003 algorithm changes, AI matching и redesign vacancy cards.

## 3. Реализация

### 3.1 Canonical routing

`app.py` теперь обслуживает текущий unified search UI непосредственно на:

```text
GET /vacancies
```

Исторический маршрут:

```text
GET /vacancies/internal
```

возвращает permanent `308` на `/vacancies` и переносит raw query string без пересборки. Это сохраняет порядок и повторение параметров, включая:

```text
source=hh&source=superjob&snapshot=<uuid>&page=1
```

Redirect получает `Cache-Control: no-store, max-age=0` и `X-Robots-Tag: noindex`, чтобы старый URL не индексировался и не закреплялся stale redirect cache в verification/rollback окне.

### 3.2 Canonical generated URLs

Обновлены:

- main и compact search forms;
- pagination links;
- navbar/footer/home CTA через `url_for('vacancies')`;
- legacy HH/SuperJob redirects;
- canonical meta URL в `<head>`.

HTML canonical search page не генерирует `/vacancies/internal`.

### 3.3 Public source-state contract

Добавлен `services/source_status.py` с пятью разрешёнными состояниями:

```text
available
cached
degraded
auth_required
temporarily_unavailable
```

Frozen `SourceState` содержит только безопасные UI-поля:

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

Provider exception text, response body, environment variable names, tokens и credentials в public contract не попадают.

### 3.4 Live providers

Для HH, SuperJob и Reed UI различает:

- `available`: live search настроен или успешно ответил;
- `degraded`: выбранный provider не ответил в текущем snapshot, но общая выдача продолжается;
- `temporarily_unavailable`: public search сейчас не настроен, checkbox отключён и provider не вызывается;
- `auth_required`: contract поддержан для будущего source, где сам поиск требует подключения аккаунта.

HH и SuperJob сохраняют public vacancy search через app-level credential без browser OAuth. Для будущих персональных действий contract отдельно хранит `auth_required_for_actions=true`, не блокируя публичный поиск.

### 3.5 Trudvsem cache

Работа России не маскируется под live provider. UI использует:

- `cached`: свежий сохранённый cache доступен;
- `degraded`: cache доступен, но устарел, последнее обновление завершилось ошибкой либо пустой cache ещё загружается;
- `temporarily_unavailable`: cache пуст и background sync отключён.

Возраст и размер cache отображаются нейтрально. Raw worker/provider errors не выводятся. При cache miss и включённом sync search ставит durable update в очередь, не выполняя provider I/O внутри web request.

### 3.6 Source selection safety

Перед созданием SEARCH-003 snapshot route вычисляет selectable sources. Явно запрошенный, но недоступный provider:

1. исключается из `selected_sources`;
2. не создаётся и не вызывается;
3. показывается нейтральным сообщением пользователю;
4. не раскрывает имя environment variable или техническую причину.

Если пользователь не выбрал source, route выбирает первый реально доступный источник в стабильном порядке.

### 3.7 UI

Source cards, compact source menu и result-state panel получили semantic state dot, безопасный `label` и нейтральный `detail`. После поиска пользователь видит состояние выбранных площадок отдельно от approximate provider totals. Generic warning не содержит traceback, provider body или credentials.

## 4. Влияние на код и сайт

Изменённые области:

```text
app.py
services/source_status.py
templates/base.html
templates/vacancies_unified.html
static/theme.css
tests/test_routes.py
tests/test_source_status.py
.github/workflows/ci.yml
docs/
```

Пользовательское влияние:

- кнопка «Вакансии» открывает реальную выдачу на `/vacancies`;
- старые bookmarks продолжают работать;
- snapshot/page SEARCH-003 сохраняются при redirect;
- live, cached, degraded, auth-required и unavailable больше не выглядят одинаково;
- недоступный source не замедляет текущий поиск;
- техническое слово `internal` исчезает из generated public URLs.

## 5. Проверки и доказательства

Локально выполнено:

```text
python -m py_compile app.py services/source_status.py    passed
Jinja parse всех templates                               passed
python -m pytest -q tests/test_source_status.py          6 passed
python -m pytest -q                                      193 passed, 6 skipped
```

Проверены unit/route contracts:

- live source success;
- partial provider failure;
- unconfigured provider исключается до вызова;
- fresh cached Trudvsem;
- stale/failed Trudvsem refresh;
- пустой cache + disabled sync;
- `auth_required` contract;
- HH/SuperJob public search без user OAuth;
- отсутствие secret/token/error leakage;
- exact raw query preservation в `308` redirect.

Шесть local skips относятся к Flask/Psycopg/PostgreSQL service scenarios и должны пройти в GitHub Actions.

## 6. Ограничения и риски

- Redirect использует permanent method-preserving `308` и `Cache-Control: no-store`; production smoke должен подтвердить сохранение query/snapshot/page.
- Source-state UI показывает безопасное пользовательское состояние, а не SLA и не admin telemetry. Подробный центр остаётся SEARCH-005.
- Состояние live provider относится к текущему snapshot/request.
- Database migration отсутствует; SEARCH-003 snapshot schema и dedup thresholds не менялись.

## 7. Rollback

Application revert возвращает прежнюю route policy. Revision `20260809_0007`, canonical vacancy cache и SEARCH-003 snapshots не изменяются. На rollback-окне `/vacancies/internal` должен оставаться либо рабочим route, либо compatibility redirect.

## 8. Следующее действие

```text
branch search-004-canonical-vacancies
→ green GitHub Actions
→ Render deploy без migration change
→ /vacancies 200
→ /vacancies/internal?... 308 с сохранением query
→ source-state smoke
→ SEARCH-004 COMPLETE
```

После закрытия SEARCH-004 ближайшая обязательная последовательность PLAN_CURRENT переводит разработку к `AUTH-001`; подробный admin source center SEARCH-005 остаётся после account/profile/privacy foundation.

## 9. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 10.08.2026 | Реализованы canonical route, compatibility redirect, safe source-state contract, source exclusion, UI и tests. |
