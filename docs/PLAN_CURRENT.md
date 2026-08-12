# AI Career Agent - Единый план реализации и ведения разработки

| Поле | Значение |
|---|---|
| Документ | PLAN_CURRENT |
| Версия | 1.4.21 |
| Дата | 12 августа 2026 |
| Статус | ДЕЙСТВУЮЩИЙ |
| Основа кода | GitHub `main` после merge PROF-001 candidate и Render migration `20260811_0010`; production E2E выявил validation defect пустых repeatable rows; hotfix v1.4.21 подготовлен без новой migration |
| Следующий gate | `PROF-001` hotfix — green Pull Request CI, Render redeploy на той же revision `20260811_0010`, повтор partial-profile save и продолжение owner/versioning E2E |

> ОБЯЗАТЕЛЬНО ДЛЯ КАЖДОГО НОВОГО ЧАТА: прочитать этот план, новый паспорт и актуальный архив. После завершения любого пункта вернуть обновлённые DOCX/PDF/Markdown, новый ZIP, доказательства проверки и запись в журнале версий.

> КОНТРОЛЬНЫЕ СТАТУСЫ ЭТОЙ ВЕРСИИ: `FND-001`, `FND-002`, `DATA-001`, `DATA-002`, `SEC-001`, `OPS-001`, `INFRA-PREP-001`, `SYNC-001`, `SYNC-002`, `SEARCH-001`, `SEARCH-002`, `SEARCH-003`, `SEARCH-004`, `AUTH-001` и `AUTH-002` — **ВЫПОЛНЕНО**; `PROF-001` — **НУЖНА ПРОВЕРКА**; `SEARCH-005` — **ЗАПЛАНИРОВАНО**; `DOC-001` — **В РАБОТЕ как постоянный процесс**; `INFRA-001` — **ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА**. Документы с версией ниже `1.4.21` считаются устаревшими для определения очереди разработки.

## 1. Источник истины и аудит источников

- GitHub является главным источником актуального кода.
- Если в текущем чате загружен более новый ZIP, он является рабочей основой этого чата.
- Канонический план определяется наибольшей версией и датой; старые дубликаты не должны оставаться действующими.
- Перед DATA-002 проверено, что актуальный код находится в `ai-career-agent-site-main (1).zip` и соответствует завершённому DATA-001.
- Загруженные планы/паспорт были устаревшими: они содержали версии 1.0.0/1.0.1 и раннее состояние HH 403, не отражали подтверждение FND-001/FND-002 и согласованную стратегию собственного домена/VPS.
- Версия 1.4.8 закрывает SEARCH-002 как ВЫПОЛНЕНО. GitHub Actions полностью зелёный, включая отдельный `Verify SEARCH-002 cross-source deduplication controls`, PostgreSQL migration/integration, SEC/OPS/SYNC/SEARCH-001 regressions, backup/restore и container smoke. Render `/health/ready` подтвердил `current_revision=expected_revision=20260809_0006`, PostgreSQL `persistent=true`, `status=ok`. Public SuperJob vacancy search отвязан от обязательного user OAuth и работает по app-level credential. Production verification endpoint `/health/search-dedup` подтвердил реальную обработку multi-source candidate sets без ложных merge: контрольный поиск обработал 164 вакансии (`hh=20`, `reed=60`, `superjob=24`, `trudvsem=60`), `input_count=output_count=164`, `cross_source_duplicate_count=0`, `cross_source_groups=0`. Дополнительные реальные поиски также не выявили безопасной duplicate-pair; positive merge semantics подтверждены зелёным CI fixture. Остаточная задача — не dedup, а стабильная cross-page пагинация/сортировка/total в SEARCH-003.
- Версия 1.4.9 реализует SEARCH-003: persistent bounded snapshots, per-provider cursor state, canonical filter + SEARCH-002 dedup до stable ordinal, deterministic global sort, committed page prefix, honest totals и secret-free `/health/search-pagination`. Additive migration `20260809_0007` создаёт четыре TTL snapshot tables и не затрагивает canonical vacancy cache. Пакет остаётся НУЖНА ПРОВЕРКА до зелёного GitHub Actions и Render cross-page smoke.
- Версия 1.4.10 закрывает SEARCH-003 как ВЫПОЛНЕНО. GitHub Actions полностью зелёный, включая отдельный `Verify SEARCH-003 stable pagination and totals controls`, PostgreSQL migration/integration, SEC/OPS/SYNC/SEARCH-001/002 regressions, encrypted backup/restore и container smoke. Render `/health/ready` подтвердил `current_revision=expected_revision=20260809_0007`, PostgreSQL `persistent=true`, `status=ok`. Первая production-версия выявила latency regression с бесконечной загрузкой поиска; hotfix разделил provider page size и UI page size (`SEARCH_PAGE_SIZE=20`), ограничил extension одним round на request (`SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST=1`) и перевёл snapshot persistence на batch-операции. После hotfix поиск работает штатно. Production snapshot `9368cb00-e7fd-4b67-9276-ea3afcf428ff` подтвердил `page_size=20`, `committed_count=40`, `known_unique_total=69`, `candidate_count=69`, `provider_reported_total=64027`, `late_arrival_count=19`, `total_is_exact=false`, `bounded=false`; page 0 сохранил состав/порядок после перехода на следующую страницу. После Render restart тот же snapshot и source cursor state сохранились в PostgreSQL. Следующий пакет — SEARCH-004.
- Версия 1.4.11 реализовала SEARCH-004 candidate без migration: `/vacancies` стал canonical search route, `/vacancies/internal` получил query-preserving compatibility redirect, а public `SourceState` contract разделил `available`, `cached`, `degraded`, `auth_required`, `temporarily_unavailable`.
- Версия 1.4.12 закрывает SEARCH-004 как ВЫПОЛНЕНО. GitHub Actions полностью зелёный, включая отдельный `Verify SEARCH-004 canonical route and source-state controls` и все regression/infrastructure gates. Production `/health/ready` на Render подтвердил PostgreSQL `persistent=true`, `current_revision=expected_revision=20260809_0007`, `migrations.ok=true`, `status=ok`. Мобильный production-smoke подтвердил штатный поиск на canonical `/vacancies` с SEARCH-003 snapshot и page=0. Старый `/vacancies/internal?search=1&keyword=Бухгалтер&source=hh&source=superjob` корректно перенаправился на `/vacancies` с сохранением `keyword` и обоих repeated `source`; новый snapshot/page были сформированы уже canonical route. Database migration не добавлялась. SEARCH-004 закрыт как ВЫПОЛНЕНО.
- Версия 1.4.13 реализует AUTH-001 candidate: существующий `users` становится first-party identity root; migration `20260810_0008` добавляет password fields, revocable `auth_sessions` и single-use `auth_tokens`; добавлены versioned scrypt, enumeration-safe register/login/reset, session rotation/revoke, provider-neutral email adapter, auth blueprint/UI и dedicated CI gate. Production email default `disabled`; пакет остаётся НУЖНА ПРОВЕРКА до green CI, Render `0008`, SMTP и полного account E2E.
- Версия 1.4.14 фиксирует production Safari CSRF regression, обнаруженный после успешных Render `0008` и SMTP readiness checks: auth responses использовали `Referrer-Policy: no-referrer`, а production `WTF_CSRF_SSL_STRICT=true` требовал same-origin Referer. Hotfix заменяет policy на `strict-origin`, сохраняя CSRF strict mode и скрывая path/query token data. Новой migration нет; требуется green CI и полный Render Safari E2E.
- Версия 1.4.15 подтверждает Safari CSRF hotfix реальным production register POST: запрос дошёл до auth business logic и попытки email delivery. Yandex sender вернул `SMTPDataError`; ручная отправка из того же ящика показала внешнюю anti-spam блокировку на сутки. Для быстрого staging fallback добавлена backward-compatible поддержка implicit SMTP SSL/TLS (`AUTH_SMTP_USE_SSL`) поверх существующего STARTTLS. Mail.ru официально использует `smtp.mail.ru:465` с SSL/TLS и password for external app. Новой migration нет; AUTH-001 остаётся НУЖНА ПРОВЕРКА до green CI, Render Mail.ru delivery и полного E2E.
- Версия 1.4.16 фиксирует следующий blocker: v1.4.15 прошёл green GitHub Actions и Render `/health/ready`, но реальная Mail.ru delivery на Render Free завершилась `OSError` до SMTP provider из-за ограничения SMTP egress free web service. Для staging добавлен provider-neutral `gmail_api` backend: OAuth refresh token обменивается на short-lived access token по HTTPS, письмо отправляется через Gmail `users.messages.send`; CI использует mocks и не обращается к Google. Gmail API является только временным staging transport. До beta/commercial release обязателен переход на sender собственного домена (целевой пример `noreply@ai-career-agent.ru`) через production-grade transactional delivery с SPF/DKIM/DMARC; registration/verification/reset business logic при этом не переписывается. Новой migration нет; AUTH-001 остаётся НУЖНА ПРОВЕРКА до green CI, Render Gmail API delivery и полного E2E.
- Версия 1.4.17 закрывает AUTH-001 как ВЫПОЛНЕНО. GitHub Actions полностью зелёный, включая dedicated `Verify AUTH-001 first-party account controls` и все PostgreSQL/SEC/OPS/SYNC/SEARCH/Docker gates. Render `/health/ready` подтвердил `auth.email_backend=gmail_api`, `auth.email_delivery_configured=true`, PostgreSQL `persistent=true`, `current_revision=expected_revision=20260810_0008`, `migrations.ok=true`, `status=ok`. Реальная Gmail API delivery получена на внешний test mailbox. Production E2E подтвердил registration, supersede/одноразовость verification link, email verification, login, две независимые server-side sessions, отзыв отдельной сессии, `revoke others` с сохранением текущей, logout с защитой `/dashboard`, forgot/reset, смену пароля, отказ старого пароля, отзыв pre-reset sessions, успешный вход новым паролем и одноразовость reset link. Gmail API остаётся только staging transport; до beta/commercial release обязателен sender собственного домена с SPF/DKIM/DMARC. Следующий пакет — AUTH-002.

- Версия 1.4.18 реализует AUTH-002 candidate. OAuth HeadHunter/SuperJob больше не является browser identity: connect routes требуют first-party session, state привязан к `user_id` и `auth_session_id`, callback атомарно создаёт/claim/refresh owner-bound `OAuthConnection`. Migration `20260811_0009` сохраняет unique external identity и добавляет unique `(user_id, provider)` без email auto-link; legacy unbound rows остаются nullable и claim-ятся только после свежего OAuth proof. Dashboard и disconnect owner-scoped, tokens продолжают храниться зашифрованно, legacy browser keys не авторизуют. Local tests green; пакет остаётся НУЖНА ПРОВЕРКА до GitHub/Render/real HH/SJ E2E.
- Версия 1.4.19 закрывает AUTH-002 как ВЫПОЛНЕНО. GitHub Actions полностью зелёный, включая dedicated `Verify AUTH-002 first-party OAuth identity ownership controls`; Render `/health/ready` подтвердил PostgreSQL `persistent=true`, `current_revision=expected_revision=20260811_0009`, `migrations.ok=true`, `status=ok`, `oauth_configured=true`. Production E2E подтвердил для HeadHunter и SuperJob: первичную привязку, сохранение после logout/login, reconnect/`Обновить доступ` без дублей, запрет cross-user claim той же external identity, сохранение ownership первого User после конфликтной попытки, disconnect и устойчивое отключённое состояние после refresh/relogin. Итоговый regression smoke `/dashboard`, `/vacancies`, first-party login/logout и Render logs подтверждён пользователем как штатный. AUTH-002 закрыт; следующий пакет — PROF-001.
- Версия 1.4.20 реализует PROF-001 candidate. Добавлены owner-scoped `career_profiles`, immutable `career_profile_versions`, optimistic version conflict protection и migration `20260811_0010`. Профиль хранит вручную подтверждённые contacts, goals, geography, salary, skills, employment, achievements, education и languages; неполные данные допустимы. Добавлены `/profile`, editor, history/read-only version views, dashboard/navigation integration, backup inventory и dedicated `Verify PROF-001 structured career profile controls`. Импорт резюме, AI enrichment, restore historical version, export/delete и autosave исключены. Пакет остаётся НУЖНА ПРОВЕРКА до green Pull Request CI, Render `0010`, owner isolation/version/persistence E2E и regression smoke.
- Версия 1.4.21 фиксирует production E2E defect PROF-001 после green Pull Request CI и успешного Render upgrade `20260811_0010`: пустые repeatable rows формы отправляли UI default values (`employment_current=0`, `skill_level=unspecified`, `language_level=unspecified`) и ошибочно считались заполненными, из-за чего частичный профиль требовал компанию/должность или другие необязательные данные. Hotfix игнорирует только эти default-only rows, сохраняет строгую validation при реальном частичном вводе и добавляет regression tests service/route. Новой migration нет; PROF-001 остаётся НУЖНА ПРОВЕРКА до green hotfix CI, redeploy и повторного production E2E.


## 2. Обязательный протокол работы

1. Выбрать один пакет по ID и назвать исходный статус.
2. Изучить актуальный ZIP, связанные файлы, зависимости, риски и rollback.
3. Не создавать `app_fixed.py`; менять реальный `app.py` и сохранять `app:app`.
4. Не считать код выполненным без compile/tests и требуемой GitHub/Render/API/E2E проверки.
5. Не включать `.env`, tokens, databases, backups, virtualenv, caches и bytecode в ZIP/GitHub.
6. После работы обновить CHANGELOG, ROADMAP, PLAN_CURRENT и паспорт при изменении архитектуры/статуса.
7. Вернуть новый ZIP и все канонические документы; пользователь заменяет старые источники.

## 3. Статусы

| Статус | Значение |
|---|---|
| ГОТОВО К СТАРТУ | Следующий согласованный пункт; код ещё не изменён. |
| ЗАПЛАНИРОВАНО | Пункт в очереди и не начат. |
| В РАБОТЕ | Изменения начаты, критерии не достигнуты. |
| НУЖНА ПРОВЕРКА | Код готов, но нужен deploy, real DB/API, E2E или подтверждение пользователя. |
| ВЫПОЛНЕНО | Все критерии выполнены и подтверждены. |
| ЗАБЛОКИРОВАНО | Есть внешняя зависимость/ошибка. |
| ОТЛОЖЕНО | Осознанно не входит в ближайший MVP. |

Версионирование плана: PATCH - обновление статуса/доказательств; MINOR - новые или перестроенные пакеты; MAJOR - смена стратегии.

## 4. Определение готовности пакета

- Изменён только актуальный проект; список файлов известен.
- Python/JS/templates проверены применимым способом.
- Есть позитивные и негативные tests; внешние API в CI mocked.
- Миграции/rollback/backward compatibility описаны.
- Секреты и runtime artifacts отсутствуют в ZIP.
- GitHub Actions зелёный.
- Render/production/API/E2E подтверждены, если являются критерием.
- PLAN_CURRENT, CHANGELOG и документация обновлены.

## 5. Зафиксированное состояние проекта

| Область | Состояние |
|---|---|
| Запуск | Flask + Gunicorn, WSGI `app:app`. |
| Конфигурация | `config.py`, `APP_ENV=production/development/test`, ранняя валидация. |
| База | Production работает на PostgreSQL 17 через SQLAlchemy/Alembic; SQLite оставлен только как local/test fallback. |
| OAuth | AUTH-002 complete: HeadHunter/SuperJob owner-bound к first-party `User`, Fernet encryption, state bound to first-party session; production ownership E2E подтверждён. |
| Вакансии | Trudvsem cache, HH, Reed и public SuperJob search; SEARCH-001/002 подтверждены; SEARCH-003 persistent snapshot pagination подтверждена GitHub CI и production Render, включая latency hotfix, stable page boundaries и restart persistence. |
| Резюме | PDF extraction на pypdf и browser resume builder; LLM пока нет. |
| Тесты | GitHub Actions, unit/provider/route/config/database/migration/security/observability/backup tests. |
| Hosting | Render временно используется как staging/резервная площадка. Для production требуется проверенный VPS с доступностью из РФ/РБ, собственный домен и план миграции. |
| Текущая схема | Production `20260811_0010`; hotfix v1.4.21 не меняет schema и исправляет только optional repeatable-row validation в PROF-001. |

### 5.1 Выполнено/частично

- BASE-001: Flask/Gunicorn/Render и публичные страницы - реализовано.
- BASE-002: единый поиск по текущим providers - реализован в текущем объёме.
- BASE-003: AUTH-002 owner binding/encryption завершён и подтверждён GitHub/Render/real provider E2E.
- BASE-004: Trudvsem cache, внешний worker и SYNC-002 incremental checkpoint/retry/lifecycle policy реализованы и подтверждены; внешний success-smoke Trudvsem повторяется на российском VPS без блокировки текущей разработки.
- BASE-005: SEARCH-001 typed contract/canonical filtering и SEARCH-002 conservative cross-source dedup подтверждены в CI/Render; public SuperJob search включён без обязательного OAuth; stable pagination/total подтверждена SEARCH-003 в CI и production.
- BASE-006: PDF parse - частично, это не AI.
- BASE-007: resume builder/live preview/PDF/mobile - реализовано.
- BASE-008: спокойные homepage transitions/reduced motion - реализовано.
- BASE-009: first-party account и OAuth ownership выполнены; structured profile PROF-001 реализован как candidate. Real AI, server saved jobs, tracker/legal/commercial core остаются впереди.

### 5.2 Ключевые риски

| ID | Уровень | Риск |
|---|---|---|
| R-01 | Закрыт 04.08.2026 | Production переведён на PostgreSQL; restart подтвердил сохранность кэша и служебного состояния. |
| R-02 | Закрыт 07.08.2026 | Daemon thread удалён; durable queue/external worker подтверждены GitHub CI и production Render, включая restart persistence. |
| R-03 | Закрыт 06.08.2026 | SEC-001 подтверждён в production: headers/cookies/CSRF, diagnostics, безопасные ответы и `429` с `Retry-After`. |
| R-04 | Закрыт 09.08.2026 | SEARCH-003 подтвердил persistent snapshot, stable page boundaries, honest totals, late-arrival policy и restart persistence; latency regression исправлена hotfix. |
| R-05 | Высокий | Маркетинговые AI promises опережают real implementation. |
| R-06 | Средний | Большие assets и inline JS усложняют performance/support. |
| R-07 | Снижен стратегией 1.4.0 | VPS не арендуется до предрелизного окна; portability проверяется через INFRA-PREP-001 и CI. |
| R-08 | Критический | Render/Cloudflare недоступен из части сетей РФ: DNS работает, но TCP 443 до edge IP не устанавливается, запросы не доходят до Render Logs. |
| R-09 | Высокий | OpenAI API не является базовым провайдером для пользователей РФ/РБ; Yandex AI Studio/Alice AI требует benchmark, а Reed — проверку с точного VPS и договорное подтверждение. |
| R-10 | Средний | Отложенный реальный VPS test может поздно выявить сетевую несовместимость; поэтому probe tooling готов заранее, Reed имеет graceful degradation, а INFRA-001 проводится до beta, не в день релиза. |

## 6. Целевой пользовательский путь MVP 1.0

```text
создать аккаунт -> загрузить резюме -> подтвердить профиль -> получить AI-анализ
-> найти вакансии -> увидеть объяснимый match -> сохранить -> подготовить письмо
-> зафиксировать статус отклика
```

MVP не готов, если работает только отдельная демонстрация. Путь должен быть связан единым пользователем, постоянной базой, понятным consent и проверяемым восстановлением.

## 7. Сводная дорожная карта

### Этап 1. Стабилизация и безопасная основа

| ID | Приоритет | Статус | Пункт |
|---|---|---|---|
| FND-001 | P0 | ВЫПОЛНЕНО | Базовые тесты и CI перед архитектурными изменениями |
| FND-002 | P0 | ВЫПОЛНЕНО | Конфигурация приложения и разделение development/test/production |
| DATA-001 | P0 | ВЫПОЛНЕНО | Переход с временной SQLite на PostgreSQL и миграции |
| DATA-002 | P0 | ВЫПОЛНЕНО | Базовая доменная модель и слой доступа к данным |
| SEC-001 | P0 | ВЫПОЛНЕНО | Базовое усиление безопасности и proxy-aware rate limiting подтверждены на Render |
| OPS-001 | P0 | ВЫПОЛНЕНО | Observability/alerting/backup tooling подтверждены; реальный production restore drill перенесён без отмены в OPS-002/REL-001 |
| INFRA-PREP-001 | P0 | ВЫПОЛНЕНО | Hosting-independent Docker/Compose baseline, probes и CI без аренды VPS |
| DOC-001 | P0 | В РАБОТЕ | Постоянная синхронизация канонических и repository docs; не блокирует кодовые пакеты |

### Этап 2. Надёжный поиск и обновление вакансий

| ID | Приоритет | Статус | Пункт |
|---|---|---|---|
| SYNC-001 | P0 | ВЫПОЛНЕНО | Durable queue и внешний worker подтверждены GitHub CI и production Render; cache переживает restart |
| SYNC-002 | P1 | ВЫПОЛНЕНО | GitHub CI и Render revision 0004 подтверждены; checkpoint/retry/restart persistence проверены на реальных upstream timeouts; внешний success-smoke перенесён в INFRA-001/OPS-002 |
| SEARCH-001 | P0 | ВЫПОЛНЕНО | Typed `NormalizedVacancy`, central normalizer, canonical code columns `0005`, provider adapters, CI и Render/search smoke подтверждены |
| SEARCH-002 | P0 | ВЫПОЛНЕНО | Консервативная cross-source deduplication, reversible grouping и multi-source карточки подтверждены CI/Render |
| SEARCH-003 | P0 | ВЫПОЛНЕНО | Persistent bounded snapshots, stable committed pages, deterministic sort и honest totals подтверждены CI/Render |
| SEARCH-004 | P1 | ВЫПОЛНЕНО | Canonical `/vacancies`, compatibility redirect и safe source states подтверждены GitHub CI и Render/mobile production smoke |
| SEARCH-005 | P1 | ЗАПЛАНИРОВАНО | Центр состояния источников для администратора |

### Этап 3. Собственный аккаунт и карьерный профиль

| ID | Приоритет | Статус | Пункт |
|---|---|---|---|
| AUTH-001 | P0 | ВЫПОЛНЕНО | First-party account, verification/reset, revocable sessions и provider-neutral email delivery подтверждены green CI, Render Gmail API delivery и полным production E2E |
| AUTH-002 | P0 | ВЫПОЛНЕНО | Owner-bound HeadHunter/SuperJob OAuth identities, migration 0009, dashboard/reconnect/disconnect и cross-user ownership подтверждены CI/Render/production E2E |
| PROF-001 | P1 | НУЖНА ПРОВЕРКА | Owner-scoped structured facts, immutable versions, migration `0010`, UI/tests; требуется CI/Render/E2E |
| PROF-002 | P1 | ЗАПЛАНИРОВАНО | Импорт резюме в профиль с проверкой пользователем |
| PROF-003 | P1 | ЗАПЛАНИРОВАНО | Серверные черновики и версии резюме |
| PRIV-001 | P1 | ЗАПЛАНИРОВАНО | Экспорт, удаление и сроки хранения персональных данных |

### Этап 4. Реальный AI-контур

| ID | Приоритет | Статус | Пункт |
|---|---|---|---|
| AI-BENCH-001 | P0 | ЗАПЛАНИРОВАНО | Сравнительное тестирование Yandex AI Studio/Alice AI на функциях проекта |
| AI-PROVIDER-001 | P0 | ЗАПЛАНИРОВАНО | Стратегия AI-провайдеров, география, стоимость, fallback и privacy |
| AI-001 | P1 | ЗАПЛАНИРОВАНО | Независимый слой AI-провайдера и контроль стоимости |
| AI-002 | P1 | ЗАПЛАНИРОВАНО | Настоящий анализ резюме |
| AI-003 | P1 | ЗАПЛАНИРОВАНО | Адаптивное AI-интервью в конструкторе |
| AI-004 | P1 | ЗАПЛАНИРОВАНО | Объяснимая оценка соответствия вакансии |
| AI-005 | P1 | ЗАПЛАНИРОВАНО | Генерация и версии сопроводительного письма |
| AI-006 | P1 | ЗАПЛАНИРОВАНО | Оценка качества AI и защита от галлюцинаций |

### Этап 5. Управление вакансиями и откликами

| ID | Приоритет | Статус | Пункт |
|---|---|---|---|
| JOB-001 | P1 | ЗАПЛАНИРОВАНО | Серверные сохранённые вакансии |
| JOB-002 | P1 | ЗАПЛАНИРОВАНО | Трекер откликов и история действий |
| JOB-003 | P2 | ЗАПЛАНИРОВАНО | Добровольные напоминания и уведомления |
| JOB-004 | P2 | ЗАПЛАНИРОВАНО | Личная аналитика поиска работы |

### Этап 6. Коммерческий запуск, VPS, домен и миграция

| ID | Приоритет | Статус | Пункт |
|---|---|---|---|
| INFRA-001 | P0 | ОТЛОЖЕНО | Реальная аренда и полевой тест VPS выполняются в предрелизном инфраструктурном окне |
| REED-COMPAT-001 | P0 | ЗАПЛАНИРОВАНО | Техническая и договорная проверка Reed API с выбранного VPS |
| HOST-001 | P0 | ЗАПЛАНИРОВАНО | Подготовка production VPS: контейнеры, reverse proxy, PostgreSQL, TLS, deploy |
| OPS-002 | P0 при выборе VPS | ЗАПЛАНИРОВАНО | Эксплуатация VPS + production backup/restore drill, перенесённый из OPS-001 |
| DOMAIN-001 | P0 до beta | ЗАПЛАНИРОВАНО | Собственный домен, DNS, TLS и публичные URL |
| MIG-001 | P0 | ЗАПЛАНИРОВАНО | Перенос PostgreSQL и production с Render на VPS с rollback |
| PERF-001 | P2 | ЗАПЛАНИРОВАНО | Оптимизация frontend и статических ресурсов |
| A11Y-001 | P2 | ЗАПЛАНИРОВАНО | Доступность интерфейса |
| LEGAL-001 | P0 до публичного AI | ЗАПЛАНИРОВАНО | Юридические документы и согласия |
| ANL-001 | P2 | ЗАПЛАНИРОВАНО | Продуктовая аналитика без содержимого резюме |
| BILL-001 | P3 | ОТЛОЖЕНО | Тарифы, платежи и лимиты использования |
| SRC-001 | P3 | ОТЛОЖЕНО | Подключение новых источников вакансий |
| REL-001 | P0 для релиза | ЗАПЛАНИРОВАНО | Предрелизная проверка MVP 1.0 |

## 8. Подробные карточки пакетов

### Этап 1. Стабилизация и безопасная основа

#### FND-001 - Базовые тесты и CI перед архитектурными изменениями

**Приоритет:** P0
**Статус:** ВЫПОЛНЕНО

**Цель:** Зафиксировать текущее поведение проекта и не допускать незамеченных регрессий.

**Реализация:** Добавлены pytest, route/unit/provider tests, блокировка непреднамеренной внешней сети и GitHub Actions.

**Влияние на код:** tests/, requirements-dev.txt, pytest.ini, .github/workflows/ci.yml, scripts/check_repository_hygiene.py.

**Влияние на сайт:** Внешний вид не изменился; ошибки обнаруживаются до merge/deploy.

**Критерии готовности:** Подтверждены зелёный CI, намеренно красный CI, повторный зелёный CI и Render smoke.

**Зависимости:** Нет.

#### FND-002 - Конфигурация приложения и разделение development/test/production

**Приоритет:** P0
**Статус:** ВЫПОЛНЕНО

**Цель:** Сделать запуск предсказуемым и централизовать окружение.

**Реализация:** Введён config.py, AppSettings, ранняя валидация, test-only defaults и явный APP_ENV.

**Влияние на код:** config.py, app.py, services/hh_provider.py, tests, render.yaml, CI и документация.

**Влияние на сайт:** Интерфейс не изменился; ошибочная конфигурация останавливает deploy с понятным сообщением.

**Критерии готовности:** GitHub Actions и Render подтверждены; HH_CURRENCY_SCAN_PAGES исправлен на 20.

**Зависимости:** FND-001.

#### DATA-001 - Переход с временной SQLite на PostgreSQL и миграции

**Приоритет:** P0
**Статус:** ВЫПОЛНЕНО

**Цель:** Исключить потерю OAuth-подключений, кэша и будущих пользовательских данных после restart/redeploy.

**Реализация:** Добавить SQLAlchemy, Alembic, Psycopg 3, DATABASE_URL, текущие модели, первую миграцию, health и контролируемый импорт legacy SQLite.

**Влияние на код:** config.py, database.py, models/, migrations/, app.py, vacancy_store.py, scripts/manage_db.py, import_legacy_sqlite.py, requirements, CI, render.yaml, tests и документация.

**Влияние на сайт:** Визуально ничего не меняется. После подключения PostgreSQL данные должны переживать restart/redeploy. /health показывает backend и revision без секретов.

**Критерии готовности:** ВЫПОЛНЕНО: зелёный CI; production `/health` подтверждает PostgreSQL и revision `20260804_0001`; повторная миграция прошла; после restart сохранились `cached_total=24`, `current_offset=100` и служебные отметки синхронизации.

**Зависимости:** FND-001, FND-002.

#### DATA-002 - Базовая доменная модель и слой доступа к данным

**Приоритет:** P0
**Статус:** ВЫПОЛНЕНО

**Цель:** Отделить persistence от Flask routes и подготовить данные для аккаунта, профиля, вакансий и синхронизаций.

**Реализация:** Добавлены User, unified OAuthConnection, canonical Vacancy, VacancySourceRecord, SyncRun, immutable User/OAuth/Vacancy/Source/SyncRun records, repositories и StorageServices. Migration `20260804_0002` копирует legacy OAuth rows, преобразует source-only vacancies без потери raw data и выравнивает PostgreSQL sequence. app.py больше не импортирует SQLAlchemy/ORM/concrete repositories; OAuth writes временно dual-write в legacy tables; VacancyStore делегирует SQL; Trudvsem сохраняет sync lifecycle.

**Влияние на код:** domain/, models/, repositories/, services/storage.py, services/vacancy_store.py, app.py, migration 0002, legacy importer, CI, tests и документация.

**Влияние на сайт:** Визуально ничего не меняется. Existing OAuth/session/templates и search payload совместимы. `/trudvsem/status` после sync может показать persisted_run.

**Критерии готовности:** Локально migration/rollback/alembic check и 55 tests пройдены; требуется зелёный GitHub Actions, PostgreSQL legacy migration/integration без skip, Render `/health` revision `20260804_0002`, OAuth/search smoke и restart persistence.

**Зависимости:** DATA-001.

#### SEC-001 - Базовое усиление безопасности

**Приоритет:** P0
**Статус:** ВЫПОЛНЕНО

**Цель:** Защитить state-changing формы/API, browser sessions, загрузки, внешние URL и технические endpoints до появления first-party аккаунтов.

**Реализация:** Добавлен `security.py` с Flask-WTF CSRF, Flask-Limiter, ProxyFix, trusted hosts, request/body/form limits, CSP nonce, HSTS и набором browser headers. Production получает host-only `aca_session` с `Secure`, `HttpOnly`, `SameSite=Lax`, 12-часовой lifetime и принудительный запрет запуска с отключёнными CSRF/rate limits/headers. Logout переведён на POST; OAuth state одноразовый и ограничен 10 минутами. Debug/status endpoints скрыты за `DEBUG_DIAGNOSTICS` + `DIAGNOSTICS_SECRET` + `X-Diagnostics-Secret`; public UI использует sanitised `/api/sources/trudvsem/status`; `/sync/trudvsem` остаётся machine endpoint за `X-Sync-Secret`. Добавлены PDF page/text limits, safe filename, bounded request sizes и SSRF/redirect/MIME/signature protection university-logo resolver. Provider errors стали нейтральными, а HH logs не содержат response bodies/tokens.

**Влияние на код:** `security.py`, `config.py`, `app.py`, `requirements.txt`, `.github/workflows/ci.yml`, `.gitignore`, `services/hh_provider.py`, `services/resume_parser.py`, `services/university_logo.py`, `templates/base.html`, `templates/ai_career.html`, `templates/resume_builder.html`, `templates/vacancies_unified.html`, `static/styles.css`, security/config/route/template/SSRF tests и `docs/SECURITY.md`.

**Влияние на сайт:** Дизайн и основной пользовательский путь сохраняются. Сессии получают новое cookie name и существующие browser sessions будут разлогинены один раз после deploy. POST без CSRF получает нейтральный 400; частые дорогие запросы — 429; logout работает только через кнопку POST. Public `/trudvsem/status` и `/debug/*` становятся 404, но интерфейс продолжает получать безопасный status через `/api/sources/trudvsem/status`. Ошибки provider/API больше не показывают технические детали.

**Критерии готовности:** ВЫПОЛНЕНО. Подтверждены production health/revision `20260804_0002`, основные страницы, поиск и PDF, CSP/HSTS/browser headers, secure `aca_session`, CSRF без токена `400`, закрытые diagnostics, безопасный публичный Trudvsem status, отсутствие секретов в application logs и контролируемый `429` с `Retry-After` после 20 запросов к защищённому diagnostic route.

**Совместимость и rollback:** Database migration отсутствует. Rollback — application commit/redeploy; PostgreSQL остаётся на `20260804_0002`. `RATELIMIT_STORAGE_URI=memory://` рассчитан на текущий один worker; перед несколькими workers/instances нужен общий Redis-compatible backend. CSP пока допускает inline styles; PDF остаётся внутри web process до будущего queue/sandbox.

**Зависимости:** FND-002, DATA-001; DATA-002 подтверждён. После выполнения — OPS-001.

#### OPS-001 - Наблюдаемость, безопасные логи и резервное восстановление

**Приоритет:** P0
**Статус:** ВЫПОЛНЕНО

**Цель:** Дать приложению vendor-neutral наблюдаемость, безопасную диагностику и проверяемый backup/restore toolchain до продолжения функциональной разработки.

**Реализация:** Добавлены production JSON logs, `X-Request-ID`, bounded HTTP/provider metrics, sanitised recent errors, optional HTTPS alert webhook, `/health/live`, `/health/ready`, diagnostics-only `/ops/status`, PostgreSQL/SQLite backup tooling, AES-256-GCM encryption, secret-free manifest, SHA-256/revision/table-count verification, restore guard и operational runbooks.

**Подтверждено:** зелёные OPS/backup GitHub Actions; production live/readiness/revision; request ID correlation в response и structured log; закрытый `/ops/status`; provider telemetry; реальная sanitised POST-доставка alert webhook; сохранность PostgreSQL state после redeploy.

**Изменение DoD в PLAN_CURRENT 1.4.0:** ранее оставшийся encrypted backup **реальной** production PostgreSQL и restore в отдельную test database не считается отменённым или пройденным. Этот полевой drill переносится целиком в `OPS-002` и повторно проверяется в `REL-001`, потому что он логически относится к выбранной production-инфраструктуре. CI backup/restore остаётся обязательным для каждого merge.

**Влияние на сайт:** Основной интерфейс не меняется; каждый ответ получает `X-Request-ID`, а liveness/readiness разделены. Логи не содержат query/body/cookies/tokens/resume text.

**Критерии готовности OPS-001:** код, CI, Render observability и alerting подтверждены; vendor-neutral backup/restore tooling проверен на PostgreSQL в CI. **ВЫПОЛНЕНО.** Реальный production restore остаётся отдельным release gate `OPS-002/REL-001`.

**Совместимость и rollback:** Database migration отсутствует; revision остаётся `20260804_0002`. In-process metrics сбрасываются при restart. Alert webhook опционален. Rollback — application commit/redeploy; backup artifacts не удаляются автоматически.

**Зависимости:** DATA-001, DATA-002, SEC-001. После выполнения разрешены `SYNC-001` и другие hosting-independent пакеты.

#### INFRA-PREP-001 - Hosting-independent подготовка приложения к VPS

**Приоритет:** P0
**Статус:** ВЫПОЛНЕНО

**Цель:** Подготовить приложение к будущему VPS без аренды сервера и без привязки бизнес-логики к Render/Yandex Cloud/другому хостингу.

**Реализация:** В пакет перенесена уже реализованная кодовая часть прежнего `INFRA-001`: multi-target `Dockerfile`, non-root runtime/ops images, `compose.yaml` с private PostgreSQL и one-shot migrations, optional Caddy TLS, isolated restore DB, Gunicorn config, secret-free environment template, DNS/TCP/TLS/HTTP probes, manifest validator, provider shortlist, container tests и CI build/runtime smoke.

**Доказательства:** GitHub Actions зелёный, включая manifest/probe/document structure, Docker Compose validation, build container targets и runtime smoke. Код этой редакцией плана не меняется - изменена классификация пакета.

**Влияние на сайт:** Нет пользовательских изменений. Render остаётся текущей staging/резервной площадкой до `MIG-001`.

**Критерии готовности:** Container baseline воспроизводим, non-root/security requirements закреплены tests, environment templates не содержат секреты, web-код не зависит от конкретного хостинга. **ВЫПОЛНЕНО.**

**Зависимости:** SEC-001, OPS-001. Реальный VPS не требуется.

#### DOC-001 - Синхронизация README, ROADMAP, CHANGELOG и фактического кода

**Приоритет:** P0
**Статус:** В РАБОТЕ - ПОСТОЯННЫЙ ПРОЦЕСС

**Цель:** Исключить противоречивые источники и повторение уже выполненных задач.

**Реализация:** Канонические PLAN_CURRENT и паспорт обновляются после каждого архитектурного решения; README/ROADMAP/CHANGELOG и package-specific docs синхронизируются вместе с ближайшим кодовым пакетом, чтобы документация и код проходили один CI/merge cycle.

**Текущее состояние:** PLAN_CURRENT 1.4.21 и паспорт 2.35 фиксируют SEARCH-001/002/003/004, AUTH-001 и AUTH-002 как ВЫПОЛНЕНО; PROF-001 — НУЖНА ПРОВЕРКА. Production PostgreSQL уже на `20260811_0010`; hotfix не добавляет migration. Gmail API staging contract сохраняется.

**Влияние на сайт:** Нет.

**Критерии готовности:** Это постоянный процесс, а не блокирующий одноразовый gate. Для каждого package release source docs, канонические документы и changelog должны совпадать.

**Зависимости:** Постоянный процесс; не блокирует `SEARCH-001` и последующие пакеты.

### Этап 2. Надёжный поиск и обновление вакансий

#### SYNC-001 - Вынести синхронизацию Trudvsem из web-процесса

**Приоритет:** P0
**Статус:** ВЫПОЛНЕНО

**Цель:** Не связывать актуальность кэша с жизненным циклом Gunicorn и исключить дублирующие синхронизации при нескольких web/worker-процессах.

**Реализация:** Удалены `threading.Event`, `threading.Thread`, `before_request`-запуск и process-local sync state из `app.py`. Web теперь только создаёт idempotent durable job в `sync_runs`. Добавлены `TrudvsemSyncService`, CLI `scripts/sync_trudvsem.py`, long-running worker `scripts/trudvsem_sync_worker.py`, Render supervisor `scripts/start_runtime.py`, отдельный Compose `sync-worker`, cross-process lock (PostgreSQL advisory lock / SQLite lock file), heartbeat-таблица `sync_workers`, stale-run recovery и Alembic revision `20260807_0003`.

**Контроль параллелизма:** Partial unique index `uq_sync_runs_active_source` разрешает только один `queued` или `running` run на источник. PostgreSQL advisory lock и SQLite lock file являются вторым уровнем защиты. Для SQLite проверяется PID владельца: живой процесс не теряет lock из-за возраста файла, а stale lock удаляется только после исчезновения владельца и превышения порога.

**Поведение web:** Search и manual/machine routes не выполняют provider I/O. При пустом/просроченном кэше web создаёт одну durable queue row и продолжает обслуживать запрос из существующего кэша. Public status остаётся sanitised; diagnostics показывают active/latest run и heartbeat внешнего worker.

**Поведение worker:** Worker polls durable queue, автоматически создаёт scheduled run при истечении cache interval, пишет heartbeat, обновляет progress, завершает run как `succeeded`/`failed` и сохраняет прежний кэш при upstream error. Для Render free worker запускается отдельным sibling OS process через supervisor; на Docker/VPS он запускается самостоятельным Compose service profile `sync`.

**Изменённые области:** `app.py`, `config.py`, `database.py`, `domain/`, `models/`, `repositories/`, `services/`, `scripts/`, `compose.yaml`, `render.yaml`, `infra/vps/`, migration `20260807_0003`, CI, tests и документация.

**Влияние на сайт:** Визуальных изменений нет. Поиск больше не запускает daemon thread и не ждёт внешнюю API-синхронизацию. Статус `queued/running/progress` берётся из PostgreSQL и переживает restart web-процесса. При ошибке Trudvsem пользователю остаётся доступен последний успешный кэш.

**Доказательства:** локальные compile/migration/repository checks пройдены; GitHub Actions полностью зелёный, включая `Verify SYNC-001 external worker controls`, PostgreSQL integration, container build/runtime smoke и полный pytest. На Render применена revision `20260807_0003`; supervisor запускает Gunicorn и Trudvsem worker как sibling OS processes. После import-path hotfix worker выполняет реальные provider batches: в логах подтверждены `TRUDVSEM normalized items=10 raw_items=10` и `sync_fetch_batch result_count=10`. Public status показал `running=true`, `progress_percent=43`, `cached_total=102`, затем terminal idle `running=false`, `queued=false`, `cached_total=102`. После реального restart `uptime_seconds` сбросился до 89 и затем вырос до 112, при этом `cached_total=102` сохранился.

**Критерии завершения:**

1. GitHub Actions зелёный, включая `Verify SYNC-001 external worker controls`, PostgreSQL migration/integration и полный pytest.
2. Render применяет revision `20260807_0003`; `/health/ready` и `/health` возвращают `200`.
3. После deploy diagnostics показывают `worker_mode=external_process` и свежий `worker_alive=true`.
4. Machine/manual trigger создаёт `queued` run; worker переводит его в `running`, затем `succeeded` или контролируемый `failed`.
5. Повторные trigger-запросы не создают более одного active run.
6. Restart web/worker не обнуляет кэш и не оставляет вечный `running` run; stale run закрывается.
7. Ошибка upstream не удаляет ранее сохранённые вакансии и не раскрывает body/token/credentials в public response/logs.

**Исправление production startup:** первый Render smoke выявил `ModuleNotFoundError: No module named 'config'` при прямом запуске `scripts/trudvsem_sync_worker.py`. В `trudvsem_sync_worker.py` и `sync_trudvsem.py` добавлен bootstrap корня проекта в `sys.path` до импортов project modules. Повторный CI и production deploy прошли успешно; restart loop исчез.

**Ограничения:** Render free не предоставляет отдельный бесплатный background service, поэтому временно используется supervisor с двумя sibling processes в одном контейнере. Это уже исключает worker из Gunicorn, но общий container restart остаётся до будущего `HOST-001`. Очистка устаревших вакансий и полноценный cursor/watermark относятся к `SYNC-002`.

**Rollback:** Остановить worker, выставить `TRUDVSEM_SYNC_ENABLED=0`, закрыть active jobs как failed, вернуть прежний start command и application commit. Revision `0003` additive и может оставаться; controlled downgrade переводит `queued/running` в `failed`, затем удаляет `sync_workers` и active-run index. Production downgrade выполняется только после backup.

**Зависимости:** DATA-001, DATA-002, OPS-001. Все критерии SYNC-001 подтверждены; `SYNC-002` разрешён к старту.

#### SYNC-002 - Инкрементальная загрузка и очистка устаревших вакансий

**Приоритет:** P1  
**Статус:** ВЫПОЛНЕНО

**Цель:** Загружать только изменения Trudvsem в ограниченных временных окнах, продолжать большой change-set с сохранённого cursor и контролируемо убирать устаревшие записи без потери последнего успешного кэша.

**Реализация:**

- migration `20260807_0004` добавляет таблицу `sync_checkpoints` и lifecycle-поля `source_modified_at`, `closed_at`, `closed_reason`, `last_seen_run_id`;
- `SyncCheckpointRepository` хранит committed watermark, bounded pending window, next offset/limit/total, last success/cleanup и retry state;
- worker использует API-параметры `modifiedFrom` и `modifiedTo`, фиксируя верхнюю границу окна до первого запроса;
- offset/total сохраняются после каждой страницы, поэтому continuation переживает новый run и reconnect БД;
- overlapping watermark (`TRUDVSEM_SYNC_WATERMARK_OVERLAP_SECONDS`) предотвращает пропуски на границе времени, а upsert по `(source, external_id)` не создаёт дублей;
- provider lifecycle переводит явно закрытые/удалённые/expired записи в `closed`; повторное появление активирует запись обратно;
- после полного успешного окна выполняются TTL closure старых публикаций и purge закрытых source rows после retention-периода;
- cleanup и watermark advance не выполняются при upstream failure; checkpoint сохраняет pending cursor, exponential retry/backoff и старый кэш;
- initial bootstrap также является bounded/resumable window последних `TRUDVSEM_VACANCY_TTL_DAYS` дней;
- backup inventory расширен таблицей `sync_checkpoints`.

**Влияние на код:** `config.py`, `database.py`, `domain/`, `models/`, `repositories/`, `services/trudvsem_provider.py`, `services/trudvsem_sync.py`, `services/vacancy_store.py`, worker/CLI, migration `20260807_0004`, Compose/Render env, CI, tests и docs.

**Влияние на сайт:** Визуальных изменений нет. Search продолжает читать только active PostgreSQL cache. Во время incremental run доступен предыдущий кэш; закрытые/TTL-expired source rows перестают попадать в выдачу. Diagnostics показывают checkpoint, active/closed totals и retry state без raw provider body или credentials.

**Локальные доказательства:** полный доступный pytest — 130 passed, 6 skipped; отдельные SYNC-002 tests проверяют migration/downgrade, bounded provider window, bootstrap и incremental continuation, reconnect persistence, idempotent upsert, exponential retry, TTL cleanup, purge и reactivation. SQLite upgrade/check/downgrade/upgrade и Alembic check пройдены.

**Финальные доказательства 08.08.2026:**

1. GitHub Actions полностью зелёный, включая `Verify SYNC-002 incremental freshness and cleanup controls`, PostgreSQL migration/integration, encrypted backup/restore, container build/smoke и полный pytest.
2. Render `/health/ready` и `/health` вернули `200`; PostgreSQL `persistent=true`; current/expected revision = `20260807_0004`.
3. Diagnostics подтвердили persistent pending window: `pending=true`, `pending_offset=3`, `pending_total=92287`, `watermark_at=1785926683`, `pending_from_at=1785926383`, `pending_to_at=1786195111`; overlap между watermark и `pending_from_at` = 300 секунд.
4. На реальных `opendata.trudvsem.ru: Read timed out` watermark/cursor/cache не изменялись; worker оставался жив и переходил `running -> failed -> idle`; `consecutive_failures` рос, scheduled retry стартовал после `next_retry_at`, backoff наблюдался 120 -> 240 -> 480 секунд и далее вплоть до 1920 секунд.
5. После redeploy checkpoint, `pending_offset=3`, watermark, `cached_total=102` и `active_total=552` сохранились; worker поднялся новым process ID и продолжил retry state.
6. Success-path continuation, lifecycle reactivation и cleanup полностью покрыты contract/unit/migration/CI tests. Реальный successful continuation/cleanup на Render не завершился только из-за длительной недоступности upstream; владелец принял остаточный риск и перенёс повторный provider-smoke в `INFRA-001/OPS-002`.

**Ограничения:** Источник не гарантирует идеальное явное событие закрытия для каждой вакансии, поэтому применяется консервативная комбинация provider lifecycle + publication TTL. Cross-source dedup и единая vacancy contract относятся к SEARCH-001/002.

**Rollback:** установить `TRUDVSEM_SYNC_ENABLED=0`, остановить worker, оставить revision `0004` как additive либо выполнить downgrade до `0003` только после verified backup. Application rollback не должен удалять существующий vacancy cache.

**Зависимости:** SYNC-001 выполнен. SYNC-002 закрыт; следующий пакет — SEARCH-001.

#### SEARCH-001 - Единая схема вакансии и нормализация данных

**Приоритет:** P0  
**Статус:** ВЫПОЛНЕНО

**Цель:** Убрать provider-specific трактовку одинаковых полей и дать HH, SuperJob, Reed и Trudvsem единый typed contract для зарплаты, валюты, даты, формата работы, занятости, опыта и lifecycle.

**Реализация:**

- добавлен frozen typed contract `domain/vacancy_contract.py` с `NormalizedVacancy`, `WorkFormat`, `EmploymentCode`, `ExperienceCode` и `CONTRACT_VERSION=1`;
- добавлен `services/vacancy_normalizer.py` как единственная граница очистки текста, валюты, salary range, UTC dates и provider mapping;
- HH, Reed, SuperJob и Trudvsem adapters возвращают одинаковый contract mapping;
- `services/search_filters.py` применяет единый exact-code filter после provider aggregation; неизвестные значения не угадываются;
- migration `20260808_0005` добавляет nullable `work_format`, `employment_code`, `experience_code` в canonical/source vacancy tables и индексы;
- `VacancyStore` и `VacancyRepository` сохраняют canonical codes, а legacy rows используют ограниченный backward-compatible fallback только при `NULL` canonical column;
- presenter показывает понятные labels, сохраняя provider display text;
- cross-source fuzzy dedup, stable global pagination и UI redesign не входят в пакет.

**Изменённые области:** `domain/`, `models/vacancy.py`, `repositories/vacancies.py`, provider adapters, `services/vacancy_normalizer.py`, `services/search_filters.py`, `services/vacancy_store.py`, `services/vacancy_presenter.py`, `app.py`, migration `0005`, CI, tests и docs.

**Влияние на сайт:** URL и визуальный layout не меняются. Фильтры remote/hybrid/onsite, employment, experience, salary/currency и period получают одинаковую semantics у всех источников. Unknown остаётся unknown; existing cache не обнуляется.

**Доказательства:** локально пройдены `139 passed, 6 skipped`, focused SEARCH-001 suite и migration round-trip до `20260808_0005`. Первый GitHub run выявил только устаревший SEC-001 fixture: запрос `keyword=python` ожидал mock-вакансию без слова Python; fixture исправлен без изменения production-кода. Повторный GitHub Actions полностью зелёный, включая отдельный SEARCH-001 gate, PostgreSQL migration/integration, SEC/OPS/SYNC, encrypted backup/restore, Docker/Compose и полный pytest. Render `/health/ready` подтвердил `backend=postgresql`, `persistent=true`, `current_revision=expected_revision=20260808_0005`, `migrations.ok=true`. Пользовательский production smoke подтвердил штатную выдачу и filters `remote`/`onsite`, `experience=between_1_and_3`, `employment=full`.

**Критерии завершения:**

1. GitHub Actions зелёный, включая `Verify SEARCH-001 vacancy contract and normalization controls`, PostgreSQL migration/integration, SEC/OPS/SYNC, backup/restore, container build/smoke и full pytest.
2. Render `/health/ready` показывает `current_revision=expected_revision=20260808_0005`, PostgreSQL `persistent=true`.
3. Multi-source search smoke сохраняет текущие URL/карточки и не вызывает HTTP 500.
4. Contract tests подтверждают одинаковые keys/types и conservative unknown policy для четырёх providers.
5. Exact canonical filters работают для новых rows; legacy cache остаётся доступным до refresh.
6. Cross-source dedup отсутствует и остаётся SEARCH-002.

**Ограничения:** provider totals остаются source-specific до SEARCH-003; raw labels могут отличаться по языку; legacy textual fallback временный; semantic merge между источниками не выполняется.

**Rollback:** откатить application commit, сохранив additive `0005` columns. Schema downgrade до `0004` выполнять только после verified backup и только если старый код уже развернут; vacancy cache не очищать.

**Зависимости:** DATA-002 и SYNC-002 выполнены. SEARCH-001 закрыт; следующий пакет — SEARCH-002.

#### SEARCH-002 - Дедупликация между источниками

**Приоритет:** P0  
**Статус:** ВЫПОЛНЕНО

**Цель:** Не показывать одну и ту же вакансию несколько раз, когда она опубликована на HH, Reed, SuperJob и/или Trudvsem, при этом не склеивать разные роли и не терять исходные ссылки.

**Реализация:**

- `services/vacancy_deduplication.py` использует versioned fingerprint, hard gates и осторожную similarity;
- same-provider identity duplicates схлопываются только по одинаковому `source + external_id`; разные IDs одного provider не объединяются;
- employer/title/location/work format/employment/experience/seniority/publication date/salary используются как explainable признаки, unknown не превращается в догадку;
- complete-link grouping предотвращает transitive overmerge;
- primary card выбирается детерминированно по completeness, recency и фиксированному source priority;
- объединённая карточка сохраняет `source_records`, provider URLs/IDs, `dedup_group_id`, `dedup_key` и bounded explanation;
- provider links валидируются как безопасные HTTP/HTTPS URL без embedded credentials;
- migration `20260809_0006` добавляет nullable `dedup_key`/`dedup_version` и non-unique indexes в `vacancies`/`vacancy_source_records` без historical backfill;
- доказанные cross-source duplicates могут храниться как одна canonical `Vacancy` и несколько `VacancySourceRecord`; persisted grouping обратим при изменении source;
- UI поддерживает stacked provider logos, число площадок и раскрываемый список исходных публикаций;
- SuperJob vacancy search использует app-level API access и доступен без user OAuth; OAuth сохранён для user-specific функций;
- `/health/search-dedup` показывает только aggregate telemetry последнего завершённого поиска текущего web process и не раскрывает keyword/region/salary/credentials.

**Консервативные запреты merge:** разные seniority, разные onsite locations, конфликтующие canonical codes, разные валюты/несовместимые salary ranges, разные external IDs одного provider, placeholder employer/empty title и generic role без дополнительного evidence.

**Влияние на код:** `app.py`, `observability.py`, `database.py`, `domain/entities.py`, `models/vacancy.py`, `repositories/vacancies.py`, `services/vacancy_deduplication.py`, `services/vacancy_store.py`, `services/vacancy_presenter.py`, `services/superjob_provider.py`, migration `20260809_0006`, template/theme, tests, CI и docs.

**Влияние на сайт:** High-confidence дубли разных площадок отображаются одной карточкой с несколькими исходными ссылками. Неоднозначные пары остаются отдельными. SuperJob участвует в публичном поиске без обязательной авторизации. URL `/vacancies/internal` и фильтры сохранены. Provider-reported global totals остаются source-specific/approximate до SEARCH-003.

**Финальные доказательства 09.08.2026:**

1. GitHub Actions полностью зелёный, включая отдельный SEARCH-002 gate, PostgreSQL migration/integration, SEC/OPS/SYNC/SEARCH-001 regressions, encrypted backup/restore, Docker build/runtime smoke и full pytest.
2. Render `/health/ready` подтвердил PostgreSQL `persistent=true`, `current_revision=expected_revision=20260809_0006`, `migrations.ok=true`, `status=ok`.
3. После SuperJob public-search hotfix источник доступен в обычном поиске без user OAuth; migration не менялась.
4. `/health/search-dedup` подтвердил работу aggregate dedup telemetry. Контрольный реальный поиск: `input_count=164`, `output_count=164`, `hh=20`, `reed=60`, `superjob=24`, `trudvsem=60`, `cross_source_duplicate_count=0`, `cross_source_groups=0`.
5. Дополнительные реальные поиски также дали нулевые cross-source groups: ложных объединений в production не выявлено.
6. Positive merge, multi-source source preservation, negative seniority/location/currency/salary cases, complete-link anti-chain и reversible persisted split подтверждены зелёными CI tests. Отсутствие реальной duplicate-pair в ограниченном current-page candidate set принято как допустимый production negative-smoke, а не как blocker.

**Ограничения:** Similarity работает внутри текущего агрегированного candidate set; embeddings/AI merge и массовый historical backfill не используются. Cross-page stability, global sort и честный post-dedup total относятся к SEARCH-003.

**Rollback:** application revert без очистки vacancy/source cache. Additive columns revision `0006` могут остаться; controlled downgrade до `0005` — только после verified backup и развертывания совместимого старого кода.

**Зависимости:** SEARCH-001 и DATA-002 выполнены. SEARCH-002 закрыт; следующий пакет — SEARCH-003.

#### SEARCH-003 - Стабильная пагинация, сортировка и итоговые счётчики

**Приоритет:** P0  
**Статус:** ВЫПОЛНЕНО

**Цель:** Исключить повторы/пропуски между страницами и перестать выдавать сумму provider totals за точное число unique cards после canonical filters и dedup.

**Реализация:**

- `services/search_aggregation.py` создаёт/reuses bounded persistent search snapshot по SHA-256 fingerprint filters/sources/page-size;
- migration `20260809_0007` добавляет `search_snapshots`, `search_snapshot_sources`, `search_snapshot_candidates`, `search_snapshot_items`;
- per-provider `next_page/fetched_pages/reported_total/exhausted/error` живут в PostgreSQL/SQLite, а не в process memory;
- перед фиксацией global page boundary каждый не-terminal provider обязан покрыть требуемую глубину accepted identities либо стать `exhausted/bounded`, поэтому объёмный источник не скрывает непрочитанный HH/SuperJob;
- SEARCH-001 canonical filter и SEARCH-002 dedup выполняются до stable ordinal/page slicing;
- deterministic sort использует published/salary/provider rank и explicit title/company/source/external-id/hash tie-breakers;
- уже показанные pages образуют committed prefix; поздние более новые items добавляются после него и не переставляют page 0;
- extension lease блокирует дублирующие provider fetches; provider failure сохраняет materialized pages;
- `provider_reported_total`, `known_unique_total`, `total_is_exact`, `bounded` имеют отдельную semantics;
- TTL cleanup каскадно удаляет только ephemeral snapshot state;
- `/health/search-pagination?snapshot=<uuid>` показывает secret-free counters/cursors без keyword/region/salary/credentials;
- defaults: TTL 1800s, 1200 candidates, 8 pages/source, 1 extension round/request, buffer 1, lease 90s.

**Влияние на код:** `app.py`, config/database/domain/models/repositories/services, migration `0007`, template/styles, backup inventory, Render/Compose/VPS env, tests/CI/docs. SEARCH-002 thresholds не меняются.

**Влияние на сайт:** pagination URLs содержат opaque snapshot ID; page 0/page 1 получают стабильные boundaries; summary различает exact unique count, known minimum и approximate provider-reported total. Истёкший/mismatched snapshot начинает новый page 0.

**Финальные доказательства 09.08.2026:**

1. GitHub Actions полностью зелёный, включая `Verify SEARCH-003 stable pagination and totals controls`, PostgreSQL migration/integration, SEC/OPS/SYNC/SEARCH-001/002 regressions, encrypted backup/restore, Docker build/runtime smoke и full pytest.
2. Render `/health/ready` подтвердил PostgreSQL `persistent=true`, `current_revision=expected_revision=20260809_0007`, `migrations.ok=true`, `status=ok`.
3. Production regression: первая реализация создавала чрезмерную latency и визуально бесконечную загрузку. Hotfix ввёл `SEARCH_PAGE_SIZE=20`, `SEARCH_SNAPSHOT_MAX_ROUNDS_PER_REQUEST=1`, batch insert/lookup для candidates/items и запрет повторной полной materialization уже committed pages. После deploy обычный поиск работает штатно.
4. Snapshot `9368cb00-e7fd-4b67-9276-ea3afcf428ff`: `page_size=20`, `committed_count=40`, `known_unique_total=69`, `candidate_count=69`, `provider_reported_total=64027`, `late_arrival_count=19`, `total_is_exact=false`, `bounded=false`.
5. Page 0 сохранил первые вакансии и порядок после перехода на следующую страницу и возврата; late arrivals не переставили committed prefix.
6. После Render restart тот же snapshot продолжил открываться с теми же counters и per-provider cursor state, что подтверждает PostgreSQL persistence, а не process-local memory.
7. Локально до production verification: `182 passed, 6 skipped`, focused SEARCH-003 `18 passed`, migration round-trip и Alembic check пройдены; после hotfix локальный regression suite расширен и GitHub CI повторно зелёный.

**Критерии завершения:** выполнены. CI зелёный; Render revision `20260809_0007`; committed pages стабильны; totals имеют явную known/provider-reported/exact semantics; late arrivals не меняют уже показанную страницу; snapshot и cursors переживают restart; health endpoint secret-free.

**Ограничения:** exact global total не достигается synchronous scan 90k+ upstream results; bounded snapshot может вернуть `total_is_exact=false`; relevance использует deterministic provider rank; route redesign остаётся SEARCH-004.

**Rollback:** application revert без очистки vacancy cache. Additive `0007` может остаться; controlled downgrade до `0006` — только после verified backup и deployment совместимого кода. Downgrade удаляет только snapshot tables.

**Зависимости:** SEARCH-001/002 выполнены. SEARCH-003 закрыт; следующий пакет — SEARCH-004.

#### SEARCH-004 - Основной маршрут /vacancies и честные состояния источников

**Приоритет:** P1
**Статус:** ВЫПОЛНЕНО

**Цель:** Убрать технический public URL `/vacancies/internal`, сделать `/vacancies` единственным canonical route выдачи и показывать безопасное фактическое состояние каждого источника.

**Реализация:**

- `GET /vacancies` обслуживает существующий unified search UI;
- `GET /vacancies/internal` возвращает permanent `308` на `/vacancies`, сохраняя raw query string, repeated `source`, filters, `snapshot` и `page`;
- redirect получает `Cache-Control: no-store` и `X-Robots-Tag: noindex` на verification-окне;
- search forms, compact form, pagination, navbar/footer/home CTA и canonical meta используют `/vacancies`;
- `services/source_status.py` вводит public contract `available | cached | degraded | auth_required | temporarily_unavailable`;
- HH/SuperJob/Reed показывают live success/degraded/unavailable без exception details;
- Trudvsem использует только cache-based states (`cached`, `degraded`, `temporarily_unavailable`) и не выдаётся за live provider;
- явно запрошенный unavailable provider исключается до вызова SEARCH-003 aggregator и получает neutral user notice;
- dedicated SEARCH-004 route/source-state tests и CI gate добавлены;
- database migration отсутствует, revision остаётся `20260809_0007`.

**Влияние на код:** `app.py`, `services/source_status.py`, `templates/base.html`, `templates/vacancies_unified.html`, `static/theme.css`, route/source-state tests, CI и docs.

**Влияние на сайт:** Публичный URL понятен; старые bookmarks не ломаются; source cards и result badges честно различают live, cached, degraded, auth-required и temporarily unavailable; technical `internal`, env names, traceback/body/token в generated UI отсутствуют.

**Локальные доказательства:** compile/Jinja parse пройдены; `tests/test_source_status.py` — `6 passed`; полный доступный pytest — `193 passed, 6 skipped`. Flask/Psycopg/PostgreSQL service scenarios остаются GitHub CI gate.

**Критерии готовности:** `/vacancies` 200; legacy redirect сохраняет query/snapshot/page; generated URL не содержит `/vacancies/internal`; source states secret-free; failure одного provider не ломает общую страницу; GitHub Actions и Render route/search smoke зелёные.

**Ограничения:** redirect использует permanent method-preserving `308` и `Cache-Control: no-store`; подробная admin telemetry остаётся SEARCH-005; source state относится к текущему snapshot/request и не является SLA.

**Rollback:** application revert без schema downgrade. Revision `0007`, vacancy cache и search snapshots не очищаются.

**Финальные доказательства:** GitHub Actions полностью зелёный, включая отдельный `Verify SEARCH-004 canonical route and source-state controls` и все regression/infrastructure gates. Production `/health/ready` на Render подтвердил PostgreSQL `persistent=true`, `current_revision=expected_revision=20260809_0007`, `migrations.ok=true`, `status=ok`. Мобильный production-smoke подтвердил штатный поиск на canonical `/vacancies` с SEARCH-003 snapshot и page=0. Старый `/vacancies/internal?search=1&keyword=Бухгалтер&source=hh&source=superjob` корректно перенаправился на `/vacancies` с сохранением `keyword` и обоих repeated `source`; новый snapshot/page были сформированы уже canonical route. Database migration не добавлялась. SEARCH-004 закрыт как ВЫПОЛНЕНО.

**Зависимости:** SEARCH-001/002/003 выполнены. Следующий обязательный пакет — AUTH-001; SEARCH-005 остаётся после account/profile/privacy foundation.

#### SEARCH-005 - Центр состояния источников для администратора

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Показывать доступность API, latency, импорт и срок интеграций.

**Реализация:** ProviderHealth/SyncRun metrics и защищённая admin page.

**Влияние на код:** models, monitoring service, admin route/template, auth/tests.

**Влияние на сайт:** Пользователь видит краткий статус; администратор - детали без токенов.

**Критерии готовности:** Недоступно без admin role; metrics обновляются; PII/credentials отсутствуют.

**Зависимости:** AUTH-001, OPS-001, SYNC-001.

### Этап 3. Собственный аккаунт и карьерный профиль

#### AUTH-001 - Аккаунт AI Career Agent

**Приоритет:** P0
**Статус:** ВЫПОЛНЕНО

**Цель:** Создать собственную first-party identity; HH/SuperJob становятся независимыми дополнительными подключениями и не привязываются автоматически.

**Реализация:** Существующий `users`; versioned scrypt; additive migration `20260810_0008`; hashed TTL/single-use verification/reset tokens; revocable PostgreSQL sessions; register/verify/login/logout/reset/revoke blueprint; disabled/memory/SMTP STARTTLS or implicit SSL/TLS/Gmail API HTTPS email adapters; enumeration-safe responses и route limits.

**Влияние на код:** `domain/auth.py`, `models/auth.py`, `repositories/auth.py`, `services/auth.py`, `services/passwords.py`, `services/email_delivery.py`, `routes/auth.py`, auth templates, dashboard/navigation, config/backup/CI/tests/docs.

**Влияние на сайт:** Появляются регистрация, подтверждение email, вход, recovery и управление активными устройствами. При не настроенной почте registration/reset fail-closed с честным сообщением.

**Критерии готовности:** Green dedicated CI/PostgreSQL migration; Render revision `0008`; production email backend configured; E2E registration/verification/login/logout/revoke/reset; no plaintext/secret leakage; sessions отзываются и reset закрывает старые sessions.

**Ограничения:** Profile, account deletion/export, MFA и admin roles не входят. AUTH-002 OAuth binding выполнен отдельным следующим пакетом. Gmail API остаётся staging-only; production sender собственного домена обязателен до beta/commercial release.

**Rollback:** Application revert; additive `0008` оставить после появления real users. Downgrade до `0007` — только до account creation либо после verified backup/explicit decision.

**Зависимости:** DATA-002, SEC-001; SEARCH-004 выполнен.

#### AUTH-002 - Привязка OAuth HeadHunter и SuperJob к пользователю сервиса

**Приоритет:** P0
**Статус:** ВЫПОЛНЕНО

**Цель:** Хранить внешние HeadHunter/SuperJob identities как owner-bound подключения конкретного first-party `User`, а не как самостоятельную browser authentication.

**Реализация:** Connect routes требуют first-party login; OAuth state одноразовый, TTL-bound и связан с `user_id`/`auth_session_id`; callback атомарно создаёт, claim-ит legacy unbound row или refresh-ит same-owner connection. Сохраняются unique `(provider, external_user_id)` и новый unique `(user_id, provider)` в migration `20260811_0009`. Email auto-link запрещён. Dashboard/read/refresh/disconnect owner-scoped; legacy provider session keys больше не дают авторизацию; disconnect удаляет unified и rollback-mirror credentials.

**Влияние на код:** `app.py`, `routes/auth.py`, OAuth model/repository/service, migration `0009`, dashboard/navigation/styles, CI и positive/negative tests.

**Влияние на сайт:** Verified пользователь управляет HH и SuperJob из единого кабинета. Подключение другого User не видно и не может быть изменено. Для смены account того же provider сначала требуется disconnect.

**Критерии готовности:** ВЫПОЛНЕНО. Dedicated GitHub gate green; Render revision `20260811_0009`; реальный HH и SuperJob bind/reconnect/disconnect E2E; cross-user claim отклонён для обеих площадок; relogin сохраняет owner connection, а disconnect сохраняется после refresh/relogin; regression smoke и Render logs подтверждены штатными.

**Ограничения:** External APIs по-прежнему mocked в CI, а реальная provider-проверка выполняется production E2E. Remote provider revoke не унифицирован и не входит в AUTH-002; local encrypted credentials удаляются. Admin merge/transfer, phone/social identities и profile import исключены.

**Rollback:** Application revert; additive `0009` можно оставить. Downgrade удаляет только unique `(user_id, provider)` constraint и не удаляет OAuth rows. Legacy provider browser login не восстанавливать.

**Зависимости:** AUTH-001, DATA-002, SEC-001 выполнены.

#### PROF-001 - Структурированный карьерный профиль

**Приоритет:** P1  
**Статус:** НУЖНА ПРОВЕРКА

**Цель:** Создать подтверждённый owner-scoped набор фактов для search, AI и документов, не смешивая его с provider profile snapshots или неподтверждённым импортом резюме.

**Реализация:** `CareerProfile` хранит current structured snapshot по одному на first-party `User`; `CareerProfileVersion` сохраняет immutable full snapshot каждого содержательного ручного сохранения. Секции: positioning, contacts, goals, geography, salary, skills, employment, achievements, education, languages. Validation ограничивает размеры, enum/date/salary semantics, URL schemes и дубли. Optimistic `expected_version` + PostgreSQL row lock + unique constraints блокируют stale overwrite. Migration `20260811_0010` additive и создаёт только profile tables/indexes/constraints.

**Влияние на код:** `domain/profile.py`, `models/profile.py`, `repositories/profiles.py`, `services/profile.py`, `routes/profile.py`, `templates/profile/`, dashboard/navigation/CSS, migration `0010`, backup inventory, CI, tests и package docs.

**Влияние на сайт:** В кабинете появляется карточка заполнения и отдельный раздел `/profile` с просмотром, редактированием, completion indicator и read-only историей версий. Пустые/частичные профили допустимы; сохранение является явным пользовательским подтверждением.

**Критерии готовности:** Dedicated CI и PostgreSQL migration green; Render current/expected `20260811_0010`; profile сохраняется после relogin/restart; второй User не читает/редактирует/просматривает версии первого; stale editor получает conflict без потери новой версии; unchanged save не создаёт дубль; incomplete profile сохраняется; history отражает material changes; AUTH/OAuth/search regressions green.

**Exclusions:** PROF-002 import/review, PROF-003 drafts/autosave, historical restore, PRIV-001 export/delete/retention, AI-generated facts, public profile, provider snapshot auto-copy и обязательность заполнения.

**Rollback:** Application revert может оставить additive `0010`; старый код игнорирует profile tables. Controlled downgrade `0010 -> 0009` удаляет только profile current/version tables и допустим только до реальных profile data либо после verified backup/explicit data decision.

**Зависимости:** AUTH-001, AUTH-002 и DATA-002 выполнены.

#### PROF-002 - Импорт резюме в профиль с проверкой пользователем

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Заменить тупиковый PDF result на извлечение, review и подтверждение.

**Реализация:** Extraction schema, confidence, editable review, save only after confirmation.

**Влияние на код:** resume_parser, extraction service, review template/API, PDF fixtures.

**Влияние на сайт:** После загрузки пользователь исправляет и подтверждает поля.

**Критерии готовности:** Text PDF supported; errors clear; no unconfirmed fact saved.

**Зависимости:** PROF-001.

#### PROF-003 - Серверные черновики и версии резюме

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Убрать зависимость конструктора от localStorage.

**Реализация:** ResumeDraft/Version, object storage for images, autosave API, history/restore.

**Влияние на код:** models, storage service, builder API/JS, migrations/tests.

**Влияние на сайт:** Черновик доступен на другом устройстве и восстанавливается.

**Критерии готовности:** Переживает browser cleanup; доступ только владельцу; export совпадает preview.

**Зависимости:** AUTH-001, PROF-001, DATA-001.

#### PRIV-001 - Экспорт, удаление и сроки хранения персональных данных

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Дать пользователю фактический контроль над данными.

**Реализация:** Export, account deletion, integration revoke, retention and cleanup jobs.

**Влияние на код:** privacy service/routes/templates, audit metadata, migrations/tests.

**Влияние на сайт:** Рабочие кнопки экспорта и удаления.

**Критерии готовности:** Удаление подтверждается; tokens/files очищаются; процесс тестируется.

**Зависимости:** AUTH-001/002, PROF-001/003.

### Этап 4. Реальный AI-контур

#### AI-BENCH-001 - Сравнительное тестирование Yandex AI Studio/Alice AI

**Приоритет:** P0
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Проверить качество, скорость и стоимость выбранных моделей на реальных функциях AI Career Agent до интеграции.

**Реализация:** Golden dataset русских и английских резюме/вакансий; тест JSON-schema, анализа резюме, match explanations, писем и интервью; p50/p95 latency, cost и hallucination rate.

**Влияние на код:** `evals/`, fixtures, benchmark runner, отчёт моделей; production routes не меняются.

**Критерии готовности:** Утверждены пороги качества; выбран набор моделей по задачам; не допускаются придуманные места работы и достижения.

**Зависимости:** OPS-001, тестовый доступ к Yandex AI Studio. Реальный VPS не требуется для quality benchmark; исходящая доступность выбранных AI endpoints с production IP повторно проверяется в INFRA-001.

#### AI-PROVIDER-001 - Стратегия AI-провайдеров

**Приоритет:** P0
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Зафиксировать основной и резервный AI-контур с учётом РФ/РБ, privacy, стоимости и отказоустойчивости.

**Реализация:** Основной кандидат — Yandex AI Studio/Alice AI; OpenAI не используется как обязательный baseline для пользователей РФ/РБ; определяется fallback/local model, data policy, quotas, provider kill switch и routing by task/market.

**Влияние на код:** Архитектурное решение для `AIProvider`, config/secrets, usage accounting и fallback policy.

**Критерии готовности:** Decision record утверждён; география и условия провайдеров проверены; стоимость рассчитана; privacy/retention описаны.

**Зависимости:** AI-BENCH-001.

#### AI-001 - Независимый слой AI-провайдера и контроль стоимости

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Не привязывать бизнес-логику к одной модели.

**Реализация:** Provider interface, structured schemas, versioned prompts, timeout/retry, usage, limits, fallback.

**Влияние на код:** services/ai/, schemas/, prompts/, config, usage models, mock tests.

**Влияние на сайт:** Понятные loading/error/limit states; модель можно сменить без переписывания продукта.

**Критерии готовности:** Все calls идут через interface; JSON валидируется; платные API не вызываются в tests.

**Зависимости:** DATA-002, PROF-001, PRIV-001.

#### AI-002 - Настоящий анализ резюме

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Дать полезный анализ вместо keyword heuristics.

**Реализация:** Structured findings, evidence links, confidence, strengths/gaps/rewrite suggestions.

**Влияние на код:** AI service/schema, route/template, analysis versions, eval fixtures.

**Влияние на сайт:** Рабочий AI-анализ с accept/reject recommendations.

**Критерии готовности:** Каждая рекомендация grounded; нет выдуманного опыта; версии сохраняются.

**Зависимости:** AI-001, PROF-001/002.

#### AI-003 - Адаптивное AI-интервью в конструкторе

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Задавать уточняющие вопросы и превращать обязанности в подтверждённые достижения.

**Реализация:** Conversation state, question goals, metric hints, mandatory confirmation.

**Влияние на код:** interview service/models, AI prompts/schemas, builder API/UI/tests.

**Влияние на сайт:** Статичная анкета становится адаптивной, пользователь контролирует финальный текст.

**Критерии готовности:** Question depends on previous answer; facts not invented; history restores.

**Зависимости:** AI-001, PROF-001/003.

#### AI-004 - Объяснимая оценка соответствия вакансии

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Рассчитывать реальный match вместо демонстрационного процента.

**Реализация:** Deterministic features + AI requirement extraction; versioned algorithm and confidence.

**Влияние на код:** matching service, vacancy/profile features, UI, evaluation dataset.

**Влияние на сайт:** Карточка показывает процент, причины, gaps и uncertainty.

**Критерии готовности:** Оценка воспроизводима; причины соответствуют данным; ручной benchmark.

**Зависимости:** SEARCH-001, PROF-001, AI-001.

#### AI-005 - Генерация и версии сопроводительного письма

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Готовить персонализированный редактируемый черновик.

**Реализация:** Short/full, tone/language, editor, versions/export; send only by explicit user action.

**Влияние на код:** CoverLetter models/service, AI prompt/schema, UI/tests.

**Влияние на сайт:** Письмо хранится рядом с вакансией и редактируется.

**Критерии готовности:** Нет неподтверждённых фактов; versions compare/delete; no auto-send.

**Зависимости:** AI-001, PROF-001, AI-004, JOB-001.

#### AI-006 - Оценка качества AI и защита от галлюцинаций

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Не считать AI готовым только по факту ответа модели.

**Реализация:** Golden scenarios, schema checks, grounding, forbidden claims, manual sample review, metrics.

**Влияние на код:** evals/, fixtures/, CI job, policy checks/dashboard.

**Влияние на сайт:** Меньше ложных рекомендаций; unsafe output блокируется/маркируется.

**Критерии готовности:** Release blocks on metric regression; failure reason clear.

**Зависимости:** AI-001 и конкретная AI-функция.

### Этап 5. Управление вакансиями и откликами

#### JOB-001 - Серверные сохранённые вакансии

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Заменить localStorage серверной snapshot-карточкой.

**Реализация:** SavedVacancy, sources, snapshot, notes, match, stale state.

**Влияние на код:** models/repository/API/UI/migrations/tests.

**Влияние на сайт:** Сохранённые вакансии синхронизируются между устройствами.

**Критерии готовности:** Нет дублей; snapshot остаётся после исчезновения source; owner-only.

**Зависимости:** AUTH-001, DATA-002, SEARCH-001.

#### JOB-002 - Трекер откликов и история действий

**Приоритет:** P1
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Фиксировать этапы поиска, документы, заметки и следующий шаг.

**Реализация:** Application/ApplicationEvent, statuses, immutable history, due date, links to resume/letter.

**Влияние на код:** models/service/board/list UI/tests.

**Влияние на сайт:** Путь от сохранения до интервью/оффера/отказа виден в кабинете.

**Критерии готовности:** Каждый status change создаёт event; history не теряется.

**Зависимости:** JOB-001, PROF-003; AI-005 для letter link.

#### JOB-003 - Добровольные напоминания и уведомления

**Приоритет:** P2
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Возвращать к следующему действию без спама.

**Реализация:** Preferences, channels/frequency, deadlines, saved search alerts, unsubscribe/dedup.

**Влияние на код:** notification models/jobs/email/templates/tests.

**Влияние на сайт:** Управляемые уведомления; marketing off by default.

**Критерии готовности:** Только consent; unsubscribe works; duplicate sends blocked.

**Зависимости:** AUTH-001, JOB-002, OPS-001.

#### JOB-004 - Личная аналитика поиска работы

**Приоритет:** P2
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Показывать conversion и узкие места без ложных выводов.

**Реализация:** Metrics from events, period/source filters, sample-size caveats.

**Влияние на код:** analytics service/queries/dashboard/tests.

**Влияние на сайт:** Понятные показатели прогресса.

**Критерии готовности:** Metrics match events; empty/small samples not misleading.

**Зависимости:** JOB-002.

### Этап 6. Коммерческий запуск, домен и hosting

#### DOMAIN-001 - Собственный домен, DNS, TLS и публичные URL

**Приоритет:** P0 до beta
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Дать продукту постоянный адрес, независимый от Render и конкретного VPS.

**Реализация:** Регистрация домена, DNS, TLS, `PUBLIC_BASE_URL`, `TRUSTED_HOSTS`, CSRF trusted origins, cookie policy, `www` policy и новые HH/SuperJob callback URL.

**Влияние на код:** config, absolute URLs, OAuth provider settings, reverse proxy и deployment documentation.

**Влияние на сайт:** Пользователь всегда видит один коммерческий домен; последующие изменения сервера выполняются через DNS.

**Критерии готовности:** HTTPS и redirects работают; домен доступен из контрольных сетей РФ и РБ; HH/SJ callbacks проходят; старый Render URL не используется как основной.

**Зависимости:** HOST-001, SEC-001, OPS-001; до публичной beta.

#### INFRA-001 - Реальный выбор и полевой тест российского VPS

**Приоритет:** P0 перед beta / production
**Статус:** ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА

**Цель:** После завершения функционального MVP арендовать кандидата на production VPS и проверить его в реальной сетевой среде РФ/РБ, не оплачивая простаивающую инфраструктуру во время продуктовой разработки.

**Что уже готово:** Весь hosting-independent container/probe baseline вынесен в завершённый `INFRA-PREP-001`; повторно писать Docker/Compose слой здесь не требуется.

**Реализация при старте пакета:** Арендовать VPS с public IPv4; развернуть текущий compose stack; подключить временный TLS hostname; проверить доступность минимум из двух сетей РФ и одной сети РБ; выполнить outbound probes к Yandex AI и Reed; провести search/PDF/security smoke; измерить latency; зафиксировать стоимость/backup/SLA; выбрать или отклонить провайдера.

**Влияние на код:** Минимальное и только при выявлении инфраструктурной несовместимости. Бизнес-логика не должна получать provider-specific branches.

**Влияние на сайт:** До DNS switch ничего не меняется. Render продолжает работать как staging/резервная площадка.

**Критерии готовности:** Матрица РФ/РБ зелёная; TLS/health/search/resume работают; Yandex AI transport доступен; Reed transport зафиксирован; provider decision record утверждён; создано окно для `HOST-001` и `REED-COMPAT-001`.

**Зависимости:** `INFRA-PREP-001`; функциональные P0/P1 пакеты MVP должны быть в достаточной готовности для полноценного smoke. Пакет выполняется **до beta**, но не обязан выполняться сейчас.

#### REED-COMPAT-001 - Проверка Reed API с выбранного VPS

**Приоритет:** P0
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Не переносить production на сервер, с которого Reed технически или договорно недоступен.

**Реализация:** Connectivity/API smoke с точного source IP, проверка rate limits и display/redirect rules, обращение в Reed за письменным подтверждением географических и коммерческих условий.

**Влияние на код:** Provider health probe, feature flag и graceful degradation Reed.

**Критерии готовности:** API search/details проходят или Reed отключается без влияния на другие источники; условия использования зафиксированы.

**Зависимости:** INFRA-001.

#### MIG-001 - Перенос production с Render на VPS

**Приоритет:** P0
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Перенести приложение и PostgreSQL без потери данных и с контролируемым rollback.

**Реализация:** Backup Render PostgreSQL, restore на VPS, staging verification, freeze/sync window, DNS switch, post-migration smoke, наблюдение и rollback plan.

**Влияние на код:** Migration scripts, deployment checklist, DNS runbook; бизнес-логика не должна зависеть от хостинга.

**Критерии готовности:** Data counts/checksums совпадают; OAuth/search/resume работают; downtime в пределах окна; rollback протестирован.

**Зависимости:** HOST-001, DOMAIN-001, OPS-002, REED-COMPAT-001.

#### OPS-002 - Эксплуатация собственного VPS

**Приоритет:** P0 при выборе VPS
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Безопасно обслуживать выбранный VPS и выполнить обязательный production backup/restore drill, перенесённый из OPS-001 без ослабления release gate.

**Реализация:** SSH keys, no password/root login, firewall, patches, reverse proxy/TLS, offsite backups, monitoring, log rotation, deploy/rollback; encrypted backup реальной production PostgreSQL, verify manifest/SHA-256 и restore в отдельную isolated test database с совпадением revision/table counts.

**Влияние на код:** server config, Caddy/Nginx, scripts, runbooks, secrets management.

**Влияние на сайт:** Сайт доступен на том же домене; операционные риски переходят владельцу.

**Критерии готовности:** Security checklist; alerting; offsite backup restore; patch/deploy/rollback rehearsal.

**Зависимости:** HOST-001 с решением VPS.

#### PERF-001 - Оптимизация frontend и статических ресурсов

**Приоритет:** P2
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Снизить вес и сложность без новой полной переработки дизайна.

**Реализация:** WebP/AVIF, responsive/lazy images, page CSS, extracted/minified JS, remove unused files/CDN risks.

**Влияние на код:** static, templates, build scripts, performance tests.

**Влияние на сайт:** Быстрее mobile load и cold start.

**Критерии готовности:** Before/after metrics; no visual regression; budgets pass.

**Зависимости:** FND-001.

#### A11Y-001 - Доступность интерфейса

**Приоритет:** P2
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Клавиатура, screen reader, zoom и reduced motion.

**Реализация:** Semantic forms, focus, aria-live, contrast, modal focus, axe/Lighthouse/manual tests.

**Влияние на код:** templates/CSS/JS/tests/checklists.

**Влияние на сайт:** Сервис доступнее и стабильнее.

**Критерии готовности:** Key flows keyboard-only; no critical automated issues; zoom 200%.

**Зависимости:** FND-001.

#### LEGAL-001 - Юридические документы и согласия

**Приоритет:** P0 до публичного AI
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Честно описать резюме, OAuth tokens, AI providers, retention и права.

**Реализация:** Privacy, terms, AI consent, versioned acceptance, export/delete, disclaimer/support.

**Влияние на код:** templates/routes/consent models/tests.

**Влияние на сайт:** Полноценные документы и явное согласие перед AI.

**Критерии готовности:** Текст соответствует фактической архитектуре; legal review владельцем.

**Зависимости:** AUTH/PROF/AI architecture определена.

#### ANL-001 - Продуктовая аналитика без содержимого резюме

**Приоритет:** P2
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Понимать drop-off и ценность функций без утечки пользовательского текста.

**Реализация:** Event schema, consent, exclude resume/letter/token content.

**Влияние на код:** analytics service/frontend instrumentation/privacy config.

**Влияние на сайт:** Интерфейс почти не меняется; решения опираются на данные.

**Критерии готовности:** Events documented; sensitive text never sent; preferences respected.

**Зависимости:** AUTH-001, LEGAL-001.

#### BILL-001 - Тарифы, платежи и лимиты использования

**Приоритет:** P3
**Статус:** ОТЛОЖЕНО

**Цель:** Монетизировать только после доказуемо полезного полного пути.

**Реализация:** Entitlements, quotas, cost accounting, payment webhooks, invoices/cancel/support.

**Влияние на код:** billing models/service/webhooks/pricing/tests.

**Влияние на сайт:** Тарифная страница и subscription management.

**Критерии готовности:** Idempotent webhooks; access matches payment; cancellation/refund supported.

**Зависимости:** Рабочие AI/JOB функции, LEGAL, OPS.

#### SRC-001 - Подключение новых источников вакансий

**Приоритет:** P3
**Статус:** ОТЛОЖЕНО

**Цель:** Расширять охват только после качества core search.

**Реализация:** Проверить official API/license/region/rate limits/storage/attribution; implement contract tests.

**Влияние на код:** new provider/config/health/tests/UI attribution.

**Влияние на сайт:** Больше вакансий без ухудшения качества и юридической неопределённости.

**Критерии готовности:** Permitted access; provider contract passes; failure isolated.

**Зависимости:** SEARCH-001/002/003, OPS-001.

#### REL-001 - Предрелизная проверка MVP 1.0

**Приоритет:** P0 для релиза
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Подтвердить полный путь и эксплуатационную готовность.

**Реализация:** E2E, security review, load, backup restore, browser/mobile matrix, domain/TLS/OAuth, production smoke, rollback/support.

**Влияние на код:** e2e/, CI/CD, runbooks, release docs/tag.

**Влияние на сайт:** Публичный релиз только после ворот качества.

**Критерии готовности:** account -> profile -> AI -> search -> save -> letter -> tracker works; critical issues zero.

**Зависимости:** Все обязательные P0/P1 и выбранные P2.

## 9. DATA-001 - фактическая реализация 04 августа 2026

### 9.1 Что добавлено

- `database.py`: SQLAlchemy Engine/Session, SQLite/PostgreSQL settings, `pool_pre_ping`, health and Alembic helpers.
- `models/`: модели текущих `accounts`, `hh_accounts`, `vacancies`.
- `migrations/`: Alembic environment и revision `20260804_0001`.
- `scripts/manage_db.py`: `upgrade`, `current`, `check`.
- `scripts/import_legacy_sqlite.py`: явный импорт сохранённого `app.db`.
- `app.py`: OAuth account persistence через SQLAlchemy, secret-free DB health.
- `services/vacancy_store.py`: cross-database SQLAlchemy implementation с сохранением API.
- `render.yaml`: migration before Gunicorn на free plan и `healthCheckPath`.
- CI: current GitHub Actions, dependency imports, migrations, `alembic check`, tests.
- `docs/DATABASE_MIGRATION.md`, source audit и актуальная документация.

### 9.2 Совместимость

- Без `DATABASE_URL` приложение использует SQLite `<DATA_DIR>/app.db`.
- `postgres://`/`postgresql://` нормализуются к `postgresql+psycopg://`.
- Первая migration создаёт clean schema или принимает legacy SQLite tables без удаления строк.
- Vacancy cache можно восстановить sync; OAuth accounts переносятся только при наличии реального snapshot и прежнего Fernet key.
- Визуальные templates/static не менялись.

### 9.3 Локальные проверки

```text
compileall: успешно
Alembic upgrade: успешно
Alembic check: No new upgrade operations detected
pytest: 47 passed, 3 skipped
```

Пропущены только Flask/Psycopg-dependent tests из-за отсутствия этих packages в sandbox. В GitHub Actions они должны выполняться после установки `requirements.txt`; DATA-001 не может стать ВЫПОЛНЕНО до зелёного CI.

Первый запуск GitHub Actions для DATA-001 выявил ошибку только в тесте `test_sqlalchemy_account_storage_round_trip`: helper-функции `account()` и `hh_account()` корректно требуют активный Flask request context, а тест вызывал их после закрытия контекста `session_transaction`. Тест исправлен: проверка выполняется внутри `app.test_request_context`. Production-код и схема базы не изменялись. Также workflow DATA-001 должен быть вручную обновлён в `.github/workflows/ci.yml`; старый workflow заметен по отсутствию шагов Alembic/PostgreSQL и по пропуску `test_postgresql_integration.py`. Статус DATA-001 остаётся НУЖНА ПРОВЕРКА до повторного зелёного CI и production persistence-проверки.

Следующий запуск не начался из-за ошибки синтаксической валидации workflow: контекст `${{ runner.temp }}` был указан в `jobs.tests.env`, где GitHub Actions его не разрешает. `DATA_DIR` заменён на абсолютный временный путь `/tmp/ai-career-agent-ci`, а перед checkout добавлен шаг создания каталога. Production-код и миграции не изменялись. Статус DATA-001 оставался НУЖНА ПРОВЕРКА до зелёного CI и production persistence-проверки.

Финальный GitHub Actions успешно выполнил PostgreSQL 17 service, Alembic migration/check, PostgreSQL integration test и полный pytest. На Render создана PostgreSQL 17 в регионе Oregon, сайт подключён через Internal Database URL. `/health` подтвердил `backend=postgresql`, `configured=true`, `persistent=true`, `revision=20260804_0001`. После restart значения `cached_total=24`, `current_offset=100`, `last_saved=100`, `last_started` и `last_finished` сохранились; увеличение `cache_age_seconds` подтверждает продолжение работы с теми же данными. Timeout `opendata.trudvsem.ru` является внешней ошибкой источника и относится к SYNC-001/SEARCH-005, а не к миграции базы.

### 9.4 Production verification

Проверка завершена 04 августа 2026:

1. PostgreSQL 17 создан в регионе Oregon, совпадающем с web service.
2. `DATABASE_URL` настроен через Internal Database URL.
3. Start Command: `python scripts/manage_db.py upgrade && gunicorn app:app`.
4. `/health`: `status=ok`, `backend=postgresql`, `configured=true`, `persistent=true`, `revision=20260804_0001`.
5. GitHub Actions полностью зелёный, включая PostgreSQL migrations и integration test.
6. После restart сохранились `cached_total=24`, `current_offset=100`, `last_saved=100` и временные отметки синхронизации.
7. Повторный запуск Alembic не повредил схему.
8. `/dashboard` существует в текущем коде по точному пути `/dashboard` и без OAuth должен перенаправлять на главную; полученный 404 требует отдельной проверки URL/слэша и не является критерием DATA-001.
9. Ошибка `Read timed out` от Trudvsem не связана с PostgreSQL и будет обрабатываться в пакетах SYNC/SEARCH.

### 9.5 Rollback

- Откатить application commit, но не удалять PostgreSQL.
- Не выполнять Alembic downgrade без backup.
- Для data rollback использовать verified backup/restore или новую DB и переключение DATABASE_URL.
- Удаление DATABASE_URL возвращает SQLite fallback только для диагностики и не считается production solution.

## 10. DATA-002 - фактическая реализация 04 августа 2026

### 10.1 Схема

- `users` - first-party identity skeleton для AUTH-001;
- `oauth_connections` - unified HH/SuperJob connections; `user_id` owner-bound для новых/claimed rows, nullable только для legacy unbound compatibility;
- `vacancies` - canonical vacancy;
- `vacancy_source_records` - source payload/URL/raw JSON;
- `sync_runs` - persistent lifecycle provider sync;
- legacy `accounts`/`hh_accounts` временно сохранены для rollback.

### 10.2 Слои

```text
routes -> services -> repositories -> SQLAlchemy models
```

- app.py импортирует `StorageServices`, но не SQLAlchemy/ORM/concrete repositories;
- repositories возвращают detached User/OAuth/Vacancy/Source/SyncRun records;
- VacancyStore нормализует payload, VacancyRepository выполняет SQL;
- OAuth routes читают unified connections; HH/SJ writes зеркалируются в legacy tables для rollback;
- Trudvsem worker пишет start/finish через SyncRunRepository.

### 10.3 Migration 20260804_0002

- создаёт новые domain tables;
- копирует encrypted legacy OAuth rows без изменения tokens;
- преобразует старую `vacancies` в canonical/source model;
- сохраняет source IDs, raw JSON, search fields и timestamps;
- выравнивает PostgreSQL serial sequence после explicit ID backfill;
- поддерживает SQLite/PostgreSQL и controlled downgrade.

### 10.4 Локальные проверки

```text
compileall: успешно
pytest: 55 passed, 4 skipped (Flask/Psycopg/PostgreSQL недоступны локально)
SQLite upgrade: успешно
SQLite downgrade/upgrade round-trip: успешно
alembic check: No new upgrade operations detected
repository hygiene: успешно
```

### 10.5 Production verification

1. GitHub Actions полностью зелёный, включая PostgreSQL 17, migration metadata, migration `20260804_0002`, integration test и полный pytest.
2. Render deploy применил revision `20260804_0002`; `/health` показывает `backend=postgresql`, `configured=true`, `ok=true`, `persistent=true`.
3. Поиск вакансий запускается без HTTP 500; после запуска `/trudvsem/status` показывает `cached_total=23`, `current_offset=30`, `last_processed=30`, `last_saved=30`.
4. `/trudvsem/status` содержит secret-free `persisted_run` с UUID, source `trudvsem`, trigger `background`, target `300` и status `running`.
5. После restart сохранились `cached_total=23`, `current_offset=30`, `last_processed=30`, `last_saved=30`, `last_started` и тот же persisted run; увеличился только `cache_age_seconds`, что подтверждает продолжение работы с постоянными данными.
6. Пользователь подтвердил, что после перезагрузки сайт и поиск функционируют в штатном режиме.

### 10.6 Ограничения

- User account UI/passwords не входят в DATA-002.
- Legacy provider mirror tables сохраняются для rollback candidate и удаляются только отдельной cleanup migration после production acceptance AUTH-002.
- Исторически DATA-002 создавал one-to-one canonical/source связь; после SEARCH-002 доказанные cross-source duplicates могут иметь несколько source records под одной canonical vacancy.
- Историческое состояние DATA-002: Trudvsem thread оставался в Gunicorn до SYNC-001. В текущей архитектуре thread удалён и заменён внешним worker-процессом.

## 11. SEC-001 - фактическая реализация 05 августа 2026

### 11.1 Сессии и OAuth

- cookie `aca_session`: Secure/HttpOnly/SameSite=Lax, host-only, lifetime 12 часов; production запрещает `Strict`, потому что он ломает возврат из внешнего OAuth;
- production не запускается при явном отключении secure cookie, CSRF, rate limiting или security headers, а OAuth callback URL обязаны быть HTTPS без credentials/fragment;
- OAuth state хранит issued_at, действует 10 минут и consume-ится один раз до обработки success/error/cancel callback;
- после успешного OAuth transient session очищается, provider identities сохраняются;
- `/logout` изменён с GET на POST + CSRF.

### 11.2 CSRF и rate limiting

- global Flask-WTF CSRF для POST/PUT/PATCH/DELETE;
- hidden token во всех POST forms, `X-CSRF-Token` в JavaScript API;
- CSRF exemption только для secret-authenticated machine sync и non-production refresh;
- route limits для OAuth, resume/PDF, university logo, vacancy search, dashboard, status, diagnostics, sync и health;
- controlled 429 с `Retry-After`/rate-limit headers;
- process-local `memory://` storage до OPS/INFRA масштабирования.

### 11.3 Browser headers и errors

- CSP nonce на всех script tags; inline event handlers запрещены tests;
- HSTS на production HTTPS, nosniff, frame deny, referrer/permissions/cross-origin policies;
- non-static responses `Cache-Control: no-store`;
- neutral 400/404/405/413/429/500 pages/JSON;
- upstream OAuth/provider details и response bodies не отражаются пользователю.

### 11.4 Request, PDF и outbound limits

- file upload, multipart field/part, JSON and generic unsafe request limits;
- PDF file size, page count и extracted-text limits;
- filename normalization через `secure_filename`;
- university-logo URLs запрещают credentials/private IP/nonstandard port; redirects проверяются вручную; HTML/image body bounded; SVG запрещён; image signature должна совпадать с MIME.

### 11.5 Technical endpoints

- `/debug/hh`, `/debug/trudvsem`, `/trudvsem/status` требуют diagnostics mode + header secret, иначе 404;
- production `/trudvsem/refresh` возвращает 404;
- `/sync/trudvsem` доступен только с `X-Sync-Secret`;
- public UI status — `/api/sources/trudvsem/status`, без raw error/persisted internal state.

### 11.6 Локальные доказательства

```text
compileall: успешно
pytest: 77 passed, 4 skipped
repository hygiene: будет выполнен на чистом финальном ZIP
workflow YAML parse: успешно
```

Локальные skips относятся к Flask/Psycopg/PostgreSQL, отсутствующим в sandbox. GitHub Actions устанавливает production dependencies и запускает PostgreSQL 17, поэтому route/startup/integration tests не должны быть пропущены.

### 11.7 Исправление первого CI-запуска

Первый полный SEC-001 workflow корректно дошёл до отдельного шага безопасности и выявил две несовместимости:

- `WTF_CSRF_TIME_LIMIT` был передан как `datetime.timedelta`, хотя Flask-WTF 1.3 ожидает целое число секунд; это вызывало `TypeError` при проверке CSRF во всех POST-тестах. Значение исправлено на integer seconds и закреплено config-тестом.
- обработчик недоверенного Host пытался отрисовать общий шаблон до создания Flask URL adapter; вызов `url_for()` из `base.html` завершался `AttributeError: NoneType has no attribute build`. Для `SecurityError` добавлен минимальный нейтральный text response без отражения Host.

Database schema, OAuth data, UI и revision `20260804_0002` не изменялись. После последующего CI и Render smoke пакет был дополнительно исправлен и полностью подтверждён 06 августа 2026.

### 11.8 Production verification status

Подтверждены Render deploy, `/health` с PostgreSQL revision `20260804_0002`, основные страницы, поиск, PDF positive/negative, CSP/HSTS, secure cookie flags, отрицательный CSRF (`400`), закрытые diagnostics, public Trudvsem status и application logs без secrets. Положительный logout/OAuth неприменим до пользовательского аккаунта и не блокирует SEC-001.

После proxy-aware исправления повторный production-тест подтвердил controlled `429` и `Retry-After`; пакет SEC-001 закрыт как ВЫПОЛНЕНО.

### 11.9 SEC-001 rate-limit fix — фактическая реализация 06 августа 2026

Production smoke подтвердил CSP/HSTS, secure cookie, PostgreSQL health/revision, основные страницы, поиск, PDF, закрытые diagnostics, безопасный Trudvsem status, application logs и отрицательный CSRF (`400`). Проверка rate limiting выявила расхождение: декорированный `20 per 5 minutes` маршрут продолжал отвечать `404` после 25 запросов.

Причина: Flask-Limiter использовал `request.remote_addr`, который после `ProxyFix(x_for=1)` представлял меняющийся адрес промежуточного Render proxy. В исправлении:

- real client выбирается из валидного `CF-Connecting-IP`, затем первого IP `X-Forwarded-For`, только при `TRUST_PROXY_HEADERS`;
- без доверенного proxy forwarded headers игнорируются;
- bucket key хранится как HMAC-SHA256 fingerprint;
- `ProxyFix` доверяет только forwarded protocol, но не переписывает client address;
- добавлен secret-free `/api/security/rate-limit-probe` с лимитом `5 per minute`;
- CI получает отдельные regression tests с rotating proxy hops и обязательным `429`/`Retry-After`.

OPS-001 код сохранён. Миграций нет, revision остаётся `20260804_0002`. Повторный production-тест подтвердил `429` и `Retry-After`; SEC-001 переведён в статус ВЫПОЛНЕНО.

### 11.10 Production-доказательства SEC-001 — 06 августа 2026

- CSP, HSTS, frame deny, nosniff, referrer/permissions/cross-origin policies и no-store подтверждены в Response Headers.
- `aca_session` подтверждена как host-only, `HttpOnly`, `Secure`, `SameSite=Lax`; анонимная сессия отображается как session cookie до OAuth.
- `/health` подтвердил PostgreSQL и revision `20260804_0002`.
- Основные страницы, поиск вакансий, положительная и отрицательная PDF-проверка, закрытые technical routes и безопасный Trudvsem status прошли.
- `POST /logout` без CSRF token вернул `400` без traceback.
- Rate-limit тест вернул двадцать ответов `404`, затем `21: 429` с `Retry-After=295`; это подтверждает стабильный bucket за Cloudflare/Render.
- Application logs не показали tokens, cookies, DB URL, PDF content или provider bodies.


## 12. OPS-001 - фактическая реализация и закрытие базового пакета

### 12.1 Что подтверждено

- Production JSON logs и `X-Request-ID` работают; request ID найден и в response, и в structured application log.
- Log sanitizer исключает secrets, Authorization/Cookie, OAuth/API tokens, passwords, URL credentials и query strings; request bodies/resume text/raw provider bodies не логируются.
- `/health/live`, `/health/ready` и `/health` подтверждены на Render; PostgreSQL current/expected revision = `20260804_0002`.
- `/ops/status` закрыт без diagnostics secret и отдаёт bounded telemetry с secret только во временном debug-режиме.
- Sanitised alert webhook доставлен end-to-end реальным `POST application/json`; приложение не зависит от успешности webhook.
- GitHub Actions зелёный, включая `Verify OPS-001 observability controls`, `Verify PostgreSQL encrypted backup and restore` и полный test suite.
- Encrypted PostgreSQL backup/verify/restore toolchain проверен в CI на отдельной PostgreSQL database.
- После redeploy health/readiness восстановились, а persistent PostgreSQL state сохранился.

### 12.2 Изменение границы пакета в 1.4.0

Ранее OPS-001 оставался в статусе НУЖНА ПРОВЕРКА из-за единственного полевого критерия: сделать encrypted backup **реальной production PostgreSQL** и восстановить его в отдельную test database. В новой стратегии этот критерий не удалён и не объявлен выполненным. Он перенесён в `OPS-002`, потому что фактически является эксплуатационным испытанием выбранной production-инфраструктуры, и повторяется как release gate в `REL-001`.

Это изменение позволяет продолжать функциональную разработку без аренды VPS, не снижая требования к коммерческому релизу.

### 12.3 Итоговый статус

```text
OPS-001 = ВЫПОЛНЕНО
production restore drill = ОБЯЗАТЕЛЬНО В OPS-002 + REL-001
Alembic revision = 20260804_0002
```

## 13. INFRA-PREP-001 - фактическая реализация 06 августа 2026

> До PLAN_CURRENT 1.4.0 этот код учитывался как кодовая часть `INFRA-001`. В 1.4.0 он переклассифицирован в отдельный завершённый подготовительный пакет. Код не переписывался и доказательства CI не обнуляются.

### 13.1 Container baseline

- `Dockerfile` target `runtime`: Python 3.11, non-root UID/GID 10001, `/health/live` healthcheck.
- `Dockerfile` target `ops`: PostgreSQL 17 client tools, Python runtime и non-root backup/restore commands.
- `compose.yaml`: private PostgreSQL 17, one-shot migrate, web, optional Caddy TLS, isolated `restore-db` и OPS profile.
- Database host ports не публикуются; backend Docker network имеет `internal: true`.

### 13.2 Probe и отчётность

- `scripts/infra_probe.py` проверяет DNS, TCP, TLS, certificate lifetime и HTTP latency.
- Targets подготовлены для app live/ready/home, Yandex API/AI edge, Reed transport и optional HH/Trudvsem/SuperJob.
- Reports удаляют query string/URL credentials и не записывают API keys.

### 13.3 CI и security gates

- Manifest regression tests проверяют non-root image, private database, one-shot migrations, OPS/restore profiles и secret-free environment template.
- GitHub Actions валидирует Compose, собирает runtime/ops targets и запускает container health smoke.
- Один Gunicorn worker остаётся из-за process-local rate-limit storage; Trudvsem worker уже вынесен из Gunicorn в SYNC-001.

### 13.4 Итог

```text
INFRA-PREP-001 = ВЫПОЛНЕНО
реальная ВМ = НЕ СОЗДАЁТСЯ СЕЙЧАС
INFRA-001 = ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ОКНА
```

Provider shortlist и VPS runbook сохраняются как входные данные будущего `INFRA-001`; окончательный выбор провайдера не зафиксирован до полевого теста.

## 14. Зафиксированная стратегия hosting, AI и Reed

### 14.1 Новый принцип 1.4.0: сначала функциональный MVP, затем оплачиваемая инфраструктура

Render остаётся staging/резервной площадкой на период разработки. Из части сетей РФ существует подтверждённый риск недоступности Render/Cloudflare, поэтому Render не принимается как окончательный production, но это не требует немедленно арендовать VPS.

До предрелизного окна весь новый код обязан оставаться **hosting-independent**:

- config только через `config.py` и environment variables;
- PostgreSQL только через `DATABASE_URL` и Alembic;
- WSGI остаётся `app:app`;
- никаких обязательных `onrender.com` URL в business logic;
- абсолютные публичные URL идут через `PUBLIC_BASE_URL` после DOMAIN-001;
- provider/AI integrations идут через service/adapters и feature flags;
- background sync вынесен из Gunicorn в `SYNC-001`;
- health/readiness и container baseline сохраняются в CI.

### 14.2 AI benchmark не блокируется VPS

`AI-BENCH-001` выполняется на тестовом доступе к Yandex AI Studio/Alice AI и оценивает качество, latency, JSON/schema compliance, cost и hallucination rate на golden dataset. Реальный VPS для этого не нужен. После выбора production VPS `INFRA-001` повторно проверит только transport/access с его source IP.

### 14.3 Reed остаётся привязан к реальному VPS

`REED-COMPAT-001` нельзя честно закрыть без точного source IP будущего VPS. Поэтому real Reed smoke и письменное подтверждение условий выполняются сразу после `INFRA-001`. До этого Reed остаётся feature-flagged и не должен ломать HH/SuperJob/Trudvsem при недоступности.

### 14.4 Что переносится в предрелизный инфраструктурный блок

- аренда и полевой тест VPS (`INFRA-001`);
- real Reed compatibility (`REED-COMPAT-001`);
- hardening/production hosting (`HOST-001`);
- эксплуатационный production backup/restore drill (`OPS-002`);
- домен/DNS/TLS/public URLs/OAuth callbacks (`DOMAIN-001`);
- перенос PostgreSQL и production (`MIG-001`);
- финальный SEC/OPS smoke и `REL-001`.

Эти задачи выполняются **до beta/production**, но не в день публичного запуска: должен оставаться отдельный rollback/observation window.

## 15. Обязательная ближайшая последовательность

### 15.1 Функциональная разработка без аренды VPS

```text
DOC-001 (постоянная синхронизация, не блокирует код)
-> PROF-001
-> PROF-002
-> PROF-003
-> PRIV-001
-> SEARCH-005
-> AI-BENCH-001
-> AI-PROVIDER-001
-> LEGAL-001
-> AI-001
-> AI-002
-> AI-003
-> AI-004
-> AI-005
-> AI-006
-> JOB-001
-> JOB-002
-> JOB-003 / JOB-004
-> PERF-001 / A11Y-001 / ANL-001 по готовности
```

### 15.2 Предрелизный инфраструктурный блок

```text
INFRA-001 real VPS test
-> REED-COMPAT-001
-> HOST-001
-> OPS-002 + production backup/restore drill
-> DOMAIN-001
-> MIG-001
-> final SEC/OPS smoke
-> REL-001
-> commercial release
```

`AI-BENCH-001` не зависит от VPS. Финальная доступность Yandex AI с production source IP повторно подтверждается в `INFRA-001`. Порядок снова меняется только новой MINOR-версией PLAN_CURRENT с объяснением зависимостей.

## 16. Следующий пакет

`PROF-001` — **НУЖНА ПРОВЕРКА**. Candidate построен поверх актуального GitHub `main` после завершённого AUTH-002:

```text
new branch / Pull Request
-> Verify PROF-001 structured career profile controls
-> full CI green
-> merge to main
-> Render upgrade 0009 -> 0010
-> /health/ready current=expected=20260811_0010
-> create partial profile and relogin persistence
-> update -> immutable version 2
-> unchanged save -> no extra version
-> stale/cross-user owner isolation negative smoke
-> restart persistence and AUTH/OAuth/search regression
-> PROF-001 COMPLETE
-> PROF-002 START
```

PROF-001 сохраняет только вручную подтверждённые facts. HH/SuperJob profile snapshots не копируются автоматически; PDF/resume extraction не записывает facts до отдельного PROF-002 review flow. Телефон/OTP, Gmail staging sender и pre-release domain sender gate не меняются.

## 17. Обязательный отчёт после каждого пакета

```text
Пункт: <ID и название>
Статус до: <...>
Статус после: <...>
Изменены файлы: <список>
Что изменено: <кратко>
Проверки: <команды и ручные сценарии>
GitHub/production/API: <подтверждено или требуется>
Ограничения: <если есть>
Версия плана: <новая>
Следующий пункт: <ID>
Приложения: ZIP, PLAN_CURRENT DOCX/PDF/MD, паспорт при необходимости
```

## 18. Журнал версий

| Версия | Дата | Пункт | Изменение |
|---|---|---|---|
| 1.0.0 | 03.08.2026 | PLAN | Первичный единый план. |
| 1.0.1 | 03.08.2026 | FND-001 | Тесты/CI подготовлены, требовалась verification. |
| 1.0.2 | 03.08.2026 | FND-002 | Конфигурационный слой подготовлен. |
| 1.1.0 | 04.08.2026 | INFRA strategy | Согласованы own domain, paid Render first и optional VPS packages. |
| 1.2.0 | 04.08.2026 | SOURCE/DATA-001 | Источники сверены; FND-001/002 подтверждены; DATA-001 реализован и ожидает production verification. |
| 1.2.1 | 04.08.2026 | DOC-SYNC | Исправлена рассинхронизация экспортированных DOCX/PDF: FND-001 и FND-002 отмечены ВЫПОЛНЕНО; DATA-001 остаётся НУЖНА ПРОВЕРКА. |
| 1.2.2 | 04.08.2026 | DOC-CACHE-FIX | Перевыпущены документы с уникальными versioned filenames; FND-001/FND-002 подтверждены как ВЫПОЛНЕНО, DATA-001 остаётся НУЖНА ПРОВЕРКА. |
| 1.2.3 | 04.08.2026 | DATA-001-CI-FIX | Исправлен request-context тест OAuth-хранилища; усилен workflow отдельным PostgreSQL integration step. DATA-001 остаётся НУЖНА ПРОВЕРКА. |
| 1.2.4 | 04.08.2026 | DATA-001-WORKFLOW-FIX | Исправлен недопустимый `${{ runner.temp }}` в job-level env; тестовый DATA_DIR перенесён в `/tmp`. Статус DATA-001 не изменён. |
| 1.2.5 | 04.08.2026 | DATA-001-COMPLETE | Подтверждены зелёный PostgreSQL CI, Render PostgreSQL 17, Alembic revision и сохранность данных после restart; DATA-002 готов к старту. |
| 1.2.6 | 04.08.2026 | DATA-002 | Добавлены domain/repository layers и migration 20260804_0002; DOMAIN-001 подтверждён в этапе 6. DATA-002 ожидает GitHub/Render verification. |
| 1.2.7 | 05.08.2026 | DATA-002-COMPLETE | Подтверждены зелёный CI, Render revision 20260804_0002, штатный поиск и сохранность persisted sync/cache state после restart; SEC-001 готов к старту. |
| 1.2.8 | 05.08.2026 | SEC-001 | Реализованы secure session, CSRF, rate limiting, CSP/headers, request/PDF limits, diagnostics gate, neutral errors и SSRF baseline; пакет ожидает GitHub/Render verification. |
| 1.2.9 | 05.08.2026 | SEC-001-CI-FIX | Исправлены тип `WTF_CSRF_TIME_LIMIT` для Flask-WTF 1.3 и безопасный ответ при недоверенном Host; workflow содержит отдельную SEC-001 проверку, пакет ожидает повторный CI/Render smoke. |
| 1.3.0 | 05.08.2026 | INFRA/AI/REED STRATEGY | После подтверждённой недоступности Render из части сетей РФ перестроена очередь: OPS -> VPS test -> Alice AI benchmark -> Reed compatibility -> provider strategy -> production VPS -> domain -> migration -> AI layer. |
| 1.3.1 | 05.08.2026 | OPS-001 | Добавлены structured JSON logs, correlation ID, provider/HTTP metrics, live/readiness, optional alert webhook и encrypted PostgreSQL/SQLite backup-restore с secret-free manifest; пакет ожидает GitHub/Render/alert/restore verification. |
| 1.3.2 | 06.08.2026 | SEC-001-RATE-LIMIT-FIX | Исправлен нестабильный client key за Cloudflare/Render, добавлен HMAC bucket и безопасный production probe; OPS-001 сохранён. |
| 1.3.3 | 06.08.2026 | SEC-001-COMPLETE / OPS-001-VERIFY | SEC-001 закрыт после production `429` + `Retry-After`. Зафиксированы успешные live/readiness, revision, request ID response, protected ops status, Trudvsem metrics и redeploy persistence; OPS-001 остаётся на проверке до logs correlation, POST alert и production backup/restore. |
| 1.3.4 | 06.08.2026 | OPS-001-VERIFICATION-UPDATE | Подтверждены зелёные OPS/backup GitHub steps, correlation `X-Request-ID` в application JSON log и реальная sanitised POST-доставка alert webhook. OPS-001 остаётся на финальной проверке только до production backup/restore drill. |
| 1.3.5 | 06.08.2026 | INFRA-001 | Добавлены non-root Docker runtime/ops images, Compose stack, Caddy TLS profile, VPS probes, isolated restore database, CI container build/smoke, provider decision record и единый стандарт документов; требуется real VPS verification. |
| 1.4.0 | 07.08.2026 | DEVELOPMENT-SEQUENCE / INFRA-DEFER | Реальный VPS перенесён в предрелизное окно; кодовая container/probe часть выделена в выполненный INFRA-PREP-001; OPS-001 закрыт как базовый пакет с переносом production restore drill в OPS-002/REL-001; следующий кодовый пакет — SYNC-001. |
| 1.4.1 | 07.08.2026 | SYNC-001 | Удалён daemon thread из Gunicorn; добавлены durable queue, external worker/CLI, cross-process locks, worker heartbeat, stale recovery, migration 20260807_0003, Render/Compose integration, tests и verification runbook. Статус - НУЖНА ПРОВЕРКА. |
| 1.4.2 | 07.08.2026 | SYNC-001-COMPLETE | GitHub CI и Render production verification пройдены; исправлен script import-path, подтверждены внешний worker, provider batches, persisted run lifecycle, revision 20260807_0003 и cache persistence после реального restart. SYNC-002 готов к старту. |
| 1.4.3 | 07.08.2026 | SYNC-002 | Добавлены migration 20260807_0004, persistent watermark/cursor, bounded modified windows, idempotent lifecycle upsert, retry/backoff, TTL closure и retention purge; пакет ожидает GitHub/Render verification. |
| 1.4.4 | 08.08.2026 | SYNC-002-COMPLETE / SEARCH-001-PREP | GitHub CI и Render revision 0004 подтверждены; production доказал checkpoint/retry/backoff/cache/restart persistence на реальных Trudvsem timeouts. Остаточный successful provider-smoke принят и перенесён в INFRA-001/OPS-002; SEARCH-001 подготовлен и переведён в ГОТОВО К СТАРТУ. |
| 1.4.5 | 08.08.2026 | SEARCH-001 | Добавлены typed `NormalizedVacancy`, central provider normalization, canonical vacancy codes и migration `20260808_0005`, exact-code filters, compatibility fallback, contract tests и единый документный шаблон v1.1. Статус — НУЖНА ПРОВЕРКА. |
| 1.4.6 | 08.08.2026 | SEARCH-001-COMPLETE | Подтверждены зелёный CI, Render revision `20260808_0005` и production canonical filter smoke; SEARCH-002 готов к старту. |
| 1.4.7 | 09.08.2026 | SEARCH-002 | Добавлены conservative cross-source fingerprint/similarity, complete-link grouping, explainability, multi-source card/persistence integration и отдельный CI gate. Additive migration `20260809_0006` добавляет dedup metadata и reversible grouping; статус — НУЖНА ПРОВЕРКА. |
| 1.4.8 | 09.08.2026 | SEARCH-002-COMPLETE / SEARCH-003-PREP | GitHub CI и Render revision `0006` подтверждены; SuperJob public search включён без user OAuth; production `/health/search-dedup` подтвердил real candidate processing без ложных merge; positive merge semantics подтверждены CI. SEARCH-002 закрыт, SEARCH-003 готов к старту. |
| 1.4.9 | 09.08.2026 | SEARCH-003 | Добавлены persistent bounded snapshots, per-provider cursor state, stable committed ordinals, deterministic global sort, honest totals, migration `20260809_0007`, health verification endpoint и отдельный CI gate. Статус — НУЖНА ПРОВЕРКА. |
| 1.4.10 | 09.08.2026 | SEARCH-003-COMPLETE / SEARCH-004-PREP | CI и Render `0007` подтверждены; исправлена latency regression (`SEARCH_PAGE_SIZE=20`, one extension round, batch persistence); production snapshot подтвердил stable committed pages, honest totals, late arrivals и restart persistence. SEARCH-003 закрыт, SEARCH-004 готов к старту. |
| 1.4.11 | 10.08.2026 | SEARCH-004 | `/vacancies` стал canonical route; legacy query-preserving redirect, safe source-state contract, cached/degraded Trudvsem labels, canonical links/forms/pagination и dedicated tests/CI gate реализованы. Статус — НУЖНА ПРОВЕРКА. |
| 1.4.12 | 10.08.2026 | SEARCH-004-COMPLETE / AUTH-001-PREP | Green CI, Render revision 0007, canonical `/vacancies` mobile search and legacy redirect confirmed; SEARCH-004 closed, AUTH-001 ready. |
| 1.4.13 | 10.08.2026 | AUTH-001-CANDIDATE | First-party account, migration `20260810_0008`, scrypt, verification/reset tokens, revocable sessions, SMTP adapter, UI/tests/CI готовы; требуется GitHub/Render/SMTP E2E. |
| 1.4.14 | 10.08.2026 | AUTH-001-SAFARI-CSRF-HOTFIX | Render `0008` и SMTP readiness подтверждены; Safari register POST выявил missing Referer из-за auth `no-referrer`; policy изменена на `strict-origin`, strict CSRF сохранён; требуется CI/Render E2E. |
| 1.4.15 | 11.08.2026 | AUTH-001-MAILRU-SMTP-SSL | Safari hotfix production-pass подтверждён; Yandex external anti-spam blocker локализован; добавлен Mail.ru-compatible implicit SSL/TLS; GitHub Actions green, Render readiness green. |
| 1.4.16 | 11.08.2026 | AUTH-001-GMAIL-API-STAGING | Render Free SMTP egress blocker подтверждён `OSError`; добавлен Gmail API HTTPS backend с OAuth refresh-token flow, mocked tests и обязательным future domain sender gate. |
| 1.4.17 | 11.08.2026 | AUTH-001-COMPLETE / AUTH-002-PREP | Green CI, Gmail API delivery и полный production E2E подтверждены; AUTH-001 ВЫПОЛНЕНО, AUTH-002 ГОТОВО К СТАРТУ. Gmail API staging-only; domain sender + SPF/DKIM/DMARC — pre-release gate. |
| 1.4.18 | 11.08.2026 | AUTH-002-CANDIDATE | Owner-bound HH/SuperJob identities, state tied to first-party session, migration `20260811_0009`, owner-scoped refresh/disconnect, safe conflicts and dedicated tests/CI gate; требуется GitHub/Render/real provider E2E. |
| 1.4.19 | 11.08.2026 | AUTH-002-COMPLETE / PROF-001-PREP | Green GitHub Actions, Render `0009`, полный HH/SuperJob production ownership E2E и regression smoke подтверждены; AUTH-002 ВЫПОЛНЕНО, следующий пакет — PROF-001. |
| 1.4.20 | 11.08.2026 | PROF-001-CANDIDATE | Owner-scoped structured profile, immutable versions, migration `20260811_0010`, edit/view/history UI, validation, backup inventory and dedicated CI gate; требуется Pull Request/Render/production E2E. |
| 1.4.21 | 12.08.2026 | PROF-001-PARTIAL-PROFILE-HOTFIX | После green CI и Render `0010` production E2E выявил false-required validation из-за default values пустых repeatable rows. Исправлено игнорирование default-only rows, добавлены regression tests; schema без изменений, требуется hotfix CI/redeploy/E2E. |
