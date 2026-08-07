# AI Career Agent - Единый план реализации и ведения разработки

| Поле | Значение |
|---|---|
| Документ | PLAN_CURRENT |
| Версия | 1.4.1 |
| Дата | 07 августа 2026 |
| Статус | ДЕЙСТВУЮЩИЙ |
| Основа кода | `ai-career-agent-site-main (4).zip` — актуальный GitHub snapshot после merge INFRA-PREP-001; поверх него реализован SYNC-001 candidate |
| Следующий gate | GitHub Actions + Render verification `SYNC-001`; после подтверждения — `SYNC-002` |

> ОБЯЗАТЕЛЬНО ДЛЯ КАЖДОГО НОВОГО ЧАТА: прочитать этот план, новый паспорт и актуальный архив. После завершения любого пункта вернуть обновлённые DOCX/PDF/Markdown, новый ZIP, доказательства проверки и запись в журнале версий.

> КОНТРОЛЬНЫЕ СТАТУСЫ ЭТОЙ ВЕРСИИ: `FND-001`, `FND-002`, `DATA-001`, `DATA-002`, `SEC-001`, `OPS-001` и `INFRA-PREP-001` — **ВЫПОЛНЕНО**; `DOC-001` — **В РАБОТЕ как постоянный процесс**; `SYNC-001` — **НУЖНА ПРОВЕРКА НА GITHUB/RENDER**; `SYNC-002` — **СЛЕДУЮЩИЙ КОДОВЫЙ ПАКЕТ ПОСЛЕ ПОДТВЕРЖДЕНИЯ SYNC-001**; `INFRA-001` — **ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ЭТАПА**. Документы с версией ниже `1.4.1` считаются устаревшими для текущего статуса и очереди разработки.

## 1. Источник истины и аудит источников

- GitHub является главным источником актуального кода.
- Если в текущем чате загружен более новый ZIP, он является рабочей основой этого чата.
- Канонический план определяется наибольшей версией и датой; старые дубликаты не должны оставаться действующими.
- Перед DATA-002 проверено, что актуальный код находится в `ai-career-agent-site-main (1).zip` и соответствует завершённому DATA-001.
- Загруженные планы/паспорт были устаревшими: они содержали версии 1.0.0/1.0.1 и раннее состояние HH 403, не отражали подтверждение FND-001/FND-002 и согласованную стратегию собственного домена/VPS.
- Версия 1.4.1 продолжает стратегию 1.4.0 и фиксирует реализацию `SYNC-001` поверх актуального GitHub snapshot. Repository docs версии 1.3.5/2.13 во входном ZIP были устаревшими относительно загруженных канонических PLAN_CURRENT 1.4.0 и паспорта 2.14; в этом package они синхронизированы.
- Версия 1.4.0 является канонической стратегической редакцией. Она не отменяет ни одной ранее выполненной проверки: SEC-001 подтверждён в production, а OPS-001 имеет подтверждённые health/readiness, correlation ID, structured logs, provider metrics, sanitised alert webhook и encrypted PostgreSQL backup/restore в CI. Незакрытый ранее production restore drill **не удалён**, а перенесён в обязательный предрелизный `OPS-002/REL-001` gate, когда будет существовать выбранный VPS и отдельная restore database. Кодовая часть прежнего INFRA-001 (Docker/Compose, non-root runtime, migrations, Caddy test TLS, probes, isolated restore DB и CI container smoke) выделена в завершённый `INFRA-PREP-001`. Реальный `INFRA-001` теперь означает только аренду и полевую проверку VPS и выполняется после функционального MVP, но до публичной beta/production migration. Это позволяет не оплачивать простаивающую ВМ во время разработки, сохраняя требование hosting-independent architecture.

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
| OAuth | HeadHunter и SuperJob, Fernet encryption, пока не привязаны к собственному User. |
| Вакансии | Trudvsem cache, HH, Reed, conditional SuperJob; остаются dedup/pagination задачи. |
| Резюме | PDF extraction на pypdf и browser resume builder; LLM пока нет. |
| Тесты | GitHub Actions, unit/provider/route/config/database/migration/security/observability/backup tests. |
| Hosting | Render временно используется как staging/резервная площадка. Для production требуется проверенный VPS с доступностью из РФ/РБ, собственный домен и план миграции. |

### 5.1 Выполнено/частично

- BASE-001: Flask/Gunicorn/Render и публичные страницы - реализовано.
- BASE-002: единый поиск по текущим providers - реализован в текущем объёме.
- BASE-003: HH/SJ OAuth и encryption - частично, нужен User binding/E2E.
- BASE-004: Trudvsem cache - код `SYNC-001` вынес provider I/O из Gunicorn в durable external worker; требуется GitHub/Render verification.
- BASE-005: filters/sort/pagination - реализованы, но cross-source consistency требует SEARCH packages.
- BASE-006: PDF parse - частично, это не AI.
- BASE-007: resume builder/live preview/PDF/mobile - реализовано.
- BASE-008: спокойные homepage transitions/reduced motion - реализовано.
- BASE-009..012: own account, real AI, server saved jobs, tracker/legal/commercial core - впереди.

### 5.2 Ключевые риски

| ID | Уровень | Риск |
|---|---|---|
| R-01 | Закрыт 04.08.2026 | Production переведён на PostgreSQL; restart подтвердил сохранность кэша и служебного состояния. |
| R-02 | Снижен, нужна проверка | In-process daemon удалён; durable queue/external worker реализованы, требуется подтверждение migration `20260807_0003` и worker heartbeat на Render. |
| R-03 | Закрыт 06.08.2026 | SEC-001 подтверждён в production: headers/cookies/CSRF, diagnostics, безопасные ответы и `429` с `Retry-After`. |
| R-04 | Высокий | Межисточниковые дубли и нестабильный total/pagination. |
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
| SYNC-001 | P0 | НУЖНА ПРОВЕРКА | Durable queue, external worker/CLI, process lock и migration `20260807_0003` реализованы; требуется GitHub/Render verification |
| SYNC-002 | P1 | ЗАПЛАНИРОВАНО | Следующий пакет после подтверждения SYNC-001: расширенная incremental policy и очистка устаревших вакансий |
| SEARCH-001 | P0 | ЗАПЛАНИРОВАНО | Единая схема вакансии и нормализация данных |
| SEARCH-002 | P0 | ЗАПЛАНИРОВАНО | Дедупликация между источниками |
| SEARCH-003 | P0 | ЗАПЛАНИРОВАНО | Стабильная пагинация, сортировка и итоговые счётчики |
| SEARCH-004 | P1 | ЗАПЛАНИРОВАНО | Основной маршрут /vacancies и честные состояния источников |
| SEARCH-005 | P1 | ЗАПЛАНИРОВАНО | Центр состояния источников для администратора |

### Этап 3. Собственный аккаунт и карьерный профиль

| ID | Приоритет | Статус | Пункт |
|---|---|---|---|
| AUTH-001 | P0 | ЗАПЛАНИРОВАНО | Аккаунт AI Career Agent |
| AUTH-002 | P0 | ЗАПЛАНИРОВАНО | Привязка OAuth HeadHunter и SuperJob к пользователю сервиса |
| PROF-001 | P1 | ЗАПЛАНИРОВАНО | Структурированный карьерный профиль |
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

**Текущее состояние:** PLAN_CURRENT 1.4.0 и паспорт 2.14 фиксируют новую стратегию без аренды VPS до предрелизного окна. Repository docs должны быть приведены к этой версии при реализации следующего code package.

**Влияние на сайт:** Нет.

**Критерии готовности:** Это постоянный процесс, а не блокирующий одноразовый gate. Для каждого package release source docs, канонические документы и changelog должны совпадать.

**Зависимости:** Постоянный процесс; не блокирует `SYNC-001`.

### Этап 2. Надёжный поиск и обновление вакансий

#### SYNC-001 - Вынести синхронизацию Trudvsem из web-процесса

**Приоритет:** P0  
**Статус:** НУЖНА ПРОВЕРКА НА GITHUB/RENDER

**Цель:** Не связывать актуальность кэша с жизненным циклом Gunicorn и исключить provider I/O из web-request/web-worker lifecycle.

**Реализация:**

- удалены `threading.Thread`, process-local event/state и `before_request` worker startup из `app.py`;
- создан hosting-independent `TrudvsemSyncService`;
- создана durable idempotent queue на `sync_runs` со статусами `queued/running/succeeded/failed`;
- partial unique index гарантирует не более одного активного run на source;
- PostgreSQL advisory lock и SQLite lockfile блокируют параллельное выполнение;
- создана external worker command `scripts/trudvsem_sync_worker.py` и one-shot CLI `scripts/sync_trudvsem.py`;
- создана таблица `sync_workers` для heartbeat/liveness;
- Render free staging использует supervisor `scripts/start_runtime.py`: Gunicorn и worker являются соседними OS processes, а не thread внутри Flask;
- Docker Compose запускает worker отдельным service в profile `sync`;
- cache-miss, refresh и machine endpoint только ставят durable job в очередь;
- ошибки worker фиксируются в `SyncRun`, но существующий cache не удаляется;
- migration `20260807_0003` закрывает legacy abandoned `running` rows, создаёт active-run constraint и `sync_workers`;
- добавлены unit/migration/config/manifest/route tests и отдельный CI step `Verify SYNC-001 external worker controls`.

**Влияние на код:** `app.py`, `config.py`, `database.py`, `domain/`, `models/`, `repositories/`, `services/trudvsem_sync.py`, `services/sync_lock.py`, `scripts/sync_trudvsem.py`, `scripts/trudvsem_sync_worker.py`, `scripts/start_runtime.py`, migration `20260807_0003`, `render.yaml`, `Dockerfile`, `compose.yaml`, CI, tests и docs.

**Влияние на сайт:** Дизайн и search payload не меняются. Trudvsem по-прежнему читается из PostgreSQL cache; если cache пуст или устарел, web быстро ставит job в очередь и не ждёт внешний API. Пользователь получает нейтральное сообщение о фоновом обновлении.

**Критерии готовности:**

1. GitHub Actions полностью зелёный, включая PostgreSQL migration/integration, `Verify SYNC-001 external worker controls`, Docker build и runtime smoke.
2. Render применил revision `20260807_0003`; `/health/ready` возвращает `200`.
3. Start Command использует `python scripts/start_runtime.py`; application logs показывают отдельные `runtime_supervisor`, Gunicorn и `trudvsem_sync_worker` процессы.
4. Diagnostics status показывает `worker_mode=external_process`, `worker_alive=true` и heartbeat.
5. `/sync/trudvsem` с secret возвращает `202`, `run_id`, status `queued`; persisted run переходит в `running`, затем `succeeded` или контролируемый `failed`.
6. Поиск и public Trudvsem status работают без HTTP 500; provider timeout не удаляет старый cache.
7. После redeploy stale/abandoned run закрывается и новый worker продолжает работу без параллельного запуска.

**Совместимость и rollback:** Search/UI/OAuth payload совместимы. Rollback приложения возможен без downgrade, но queued rows перед возвратом старого кода следует закрыть; schema downgrade допускается только после backup. PostgreSQL revision после deploy — `20260807_0003`.

**Зависимости:** DATA-001, DATA-002, OPS-001, INFRA-PREP-001. После production verification разрешён `SYNC-002`.

#### SYNC-002 - Инкрементальная загрузка и очистка устаревших вакансий

**Приоритет:** P1  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Увеличить полноту каталога и убирать закрытые записи.

**Реализация:** Cursor/offset, upsert, active/closed, last-success watermark, retries, TTL cleanup.

**Влияние на код:** sync command, repositories, models, fixtures/tests.

**Влияние на сайт:** Больше актуальных вакансий, меньше закрытых карточек.

**Критерии готовности:** Повторный sync не создаёт дублей; закрытые скрываются; прогресс измерим.

**Зависимости:** SYNC-001.

#### SEARCH-001 - Единая схема вакансии и нормализация данных

**Приоритет:** P0  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Одинаково трактовать валюту, регион, формат, опыт, занятость, даты и зарплату.

**Реализация:** Канонический contract/schema и явные adapters каждого источника.

**Влияние на код:** base_provider.py, provider files, schemas, filters, presenter, models/tests.

**Влияние на сайт:** Фильтры и карточки становятся последовательными; неизвестные значения не маскируются.

**Критерии готовности:** Все providers проходят contract tests; значения документированы.

**Зависимости:** DATA-002 желательно.

#### SEARCH-002 - Дедупликация между источниками

**Приоритет:** P0  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Не показывать одну вакансию несколько раз из разных площадок.

**Реализация:** Fingerprint по нормализованным полям и осторожная similarity; хранить несколько source records.

**Влияние на код:** deduplication service, Vacancy/SourceRecord, search service, presenter, tests.

**Влияние на сайт:** Выдача короче и чище; карточка может показать несколько источников.

**Критерии готовности:** Known duplicates объединяются, разные роли не склеиваются, решение объяснимо.

**Зависимости:** SEARCH-001, DATA-002.

#### SEARCH-003 - Стабильная пагинация, сортировка и итоговые счётчики

**Приоритет:** P0  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Убрать пропуски/повторы между страницами и неверный total.

**Реализация:** Единая серверная пагинация по нормализованному кэшу или управляемые cursors; total после filters/dedup.

**Влияние на код:** search service, repositories, route, pagination template/tests.

**Влияние на сайт:** Кнопки и счётчик соответствуют реальным карточкам.

**Критерии готовности:** Соседние страницы не повторяются; одинаковый запрос воспроизводим.

**Зависимости:** SEARCH-001, SEARCH-002.

#### SEARCH-004 - Основной маршрут /vacancies и честные состояния источников

**Приоритет:** P1  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Убрать технический /vacancies/internal и отделить AI Career от реальной выдачи.

**Реализация:** Сделать /vacancies canonical, старый URL redirect, обновить ссылки/status copy.

**Влияние на код:** app.py, base/index/ai_career/vacancies templates, tests.

**Влияние на сайт:** Навигация понятнее, URL пригоден для аналитики и SEO.

**Критерии готовности:** Все кнопки ведут на /vacancies; старые ссылки не ломаются.

**Зависимости:** FND-001.

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
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Создать собственную identity; HH/SuperJob становятся дополнительными подключениями.

**Реализация:** Email/password или passwordless, verification, reset, sessions, logout/revoke.

**Влияние на код:** User/AuthToken/Session, auth service, routes/templates, email provider, migrations/tests.

**Влияние на сайт:** Появляются регистрация, вход и единый кабинет между устройствами.

**Критерии готовности:** E2E registration/reset; пароль не хранится открыто; sessions отзываются; rate limit.

**Зависимости:** DATA-002, SEC-001.

#### AUTH-002 - Привязка OAuth HeadHunter и SuperJob к пользователю сервиса

**Приоритет:** P0  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Хранить внешние подключения как сущности конкретного пользователя.

**Реализация:** OAuthConnection, uniqueness, encryption, refresh/revoke, connections page, migration current rows.

**Влияние на код:** OAuth routes, repositories, dashboard, migrations/tests.

**Влияние на сайт:** Пользователь управляет всеми подключениями в одном месте.

**Критерии готовности:** Чужое подключение недоступно; токены зашифрованы; disconnect очищает данные.

**Зависимости:** AUTH-001, DATA-002, SEC-001.

#### PROF-001 - Структурированный карьерный профиль

**Приоритет:** P1  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Создать подтверждённый набор фактов для search, AI и документов.

**Реализация:** Contacts, employment, achievements, skills, education, languages, goals, geography, salary.

**Влияние на код:** profile models/service/routes/templates/migrations/tests.

**Влияние на сайт:** В кабинете появляется редактируемый профиль.

**Критерии готовности:** Доступ только владельцу; неполные данные допустимы; ключевые изменения versioned.

**Зависимости:** AUTH-001, DATA-002.

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
- `oauth_connections` - unified HH/SuperJob connections, `user_id` nullable до AUTH-002;
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
- Legacy account tables удаляются только отдельной cleanup migration после AUTH-002.
- Canonical vacancy пока one-to-one с source record; actual cross-source merge относится к SEARCH-002.
- Trudvsem thread оставался в Gunicorn до SYNC-001; в candidate 1.4.1 он удалён и заменён external worker process.

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
- Один Gunicorn worker остаётся до shared rate-limit storage и отдельного Trudvsem worker.

### 13.4 Итог

```text
INFRA-PREP-001 = ВЫПОЛНЕНО
реальная ВМ = НЕ СОЗДАЁТСЯ СЕЙЧАС
INFRA-001 = ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО ОКНА
```

Provider shortlist и VPS runbook сохраняются как входные данные будущего `INFRA-001`; окончательный выбор провайдера не зафиксирован до полевого теста.

## 14. SYNC-001 - фактическая реализация 07 августа 2026

### 14.1 Изменение lifecycle

До пакета Flask/Gunicorn создавал daemon thread из `before_request`, а progress/queue state частично находились в памяти процесса. После пакета web process только читает cache и создаёт durable queued run. Provider HTTP выполняет external worker process.

```text
Browser/search request
        -> PostgreSQL vacancy cache
        -> enqueue sync_runs(status=queued), если cache пуст/устарел

External worker process
        -> claim queued run
        -> PostgreSQL advisory lock / SQLite lockfile
        -> Trudvsem API batches
        -> vacancy upsert
        -> SyncRun heartbeat/result
```

### 14.2 Persisted coordination

- migration `20260807_0003`;
- `sync_workers` heartbeat table;
- unique partial index `uq_sync_runs_active_source`;
- abandoned legacy `running` rows закрываются migration как `failed/WorkerRestarted`;
- runtime stale recovery по `TRUDVSEM_SYNC_STALE_SECONDS`;
- queue enqueue идемпотентен и безопасен при нескольких web requests/instances.

### 14.3 Staging и будущий VPS

Текущий Render free web service не требует отдельной платной worker service: `scripts/start_runtime.py` запускает Gunicorn и worker как sibling OS processes. Это временная staging-компоновка. На VPS/Compose worker запускается отдельным service через profile `sync`; бизнес-логика при этом не меняется.

### 14.4 Локальные доказательства

```text
pytest: 115 passed, 6 skipped до финальной документации
SYNC-001 tests: durable queue, active-run constraint, migration cleanup,
external execution, incremental cursor, failure cache preservation,
process lock, stale recovery и worker heartbeat — пройдены
SQLite upgrade 0001 -> 0002 -> 0003 — пройден
Alembic check — No new upgrade operations detected
SQLite downgrade/upgrade 0003 round-trip — пройден
infra manifest validator — пройден
```

Локальные skips относятся к Flask/Psycopg/PostgreSQL service, отсутствующим в изолированном окружении. Они обязательны и не должны быть skipped в GitHub Actions.

### 14.5 Production verification, которое ещё требуется

Полная последовательность приведена в `docs/SYNC001_VERIFICATION_STATUS.md`. До зелёного GitHub Actions и Render worker heartbeat пакет остаётся **НУЖНА ПРОВЕРКА**.

## 15. Зафиксированная стратегия hosting, AI и Reed

### 15.1 Новый принцип 1.4.0: сначала функциональный MVP, затем оплачиваемая инфраструктура

Render остаётся staging/резервной площадкой на период разработки. Из части сетей РФ существует подтверждённый риск недоступности Render/Cloudflare, поэтому Render не принимается как окончательный production, но это не требует немедленно арендовать VPS.

До предрелизного окна весь новый код обязан оставаться **hosting-independent**:

- config только через `config.py` и environment variables;
- PostgreSQL только через `DATABASE_URL` и Alembic;
- WSGI остаётся `app:app`;
- никаких обязательных `onrender.com` URL в business logic;
- абсолютные публичные URL идут через `PUBLIC_BASE_URL` после DOMAIN-001;
- provider/AI integrations идут через service/adapters и feature flags;
- background sync вынесен из Gunicorn в `SYNC-001` и ожидает production verification;
- health/readiness и container baseline сохраняются в CI.

### 15.2 AI benchmark не блокируется VPS

`AI-BENCH-001` выполняется на тестовом доступе к Yandex AI Studio/Alice AI и оценивает качество, latency, JSON/schema compliance, cost и hallucination rate на golden dataset. Реальный VPS для этого не нужен. После выбора production VPS `INFRA-001` повторно проверит только transport/access с его source IP.

### 15.3 Reed остаётся привязан к реальному VPS

`REED-COMPAT-001` нельзя честно закрыть без точного source IP будущего VPS. Поэтому real Reed smoke и письменное подтверждение условий выполняются сразу после `INFRA-001`. До этого Reed остаётся feature-flagged и не должен ломать HH/SuperJob/Trudvsem при недоступности.

### 15.4 Что переносится в предрелизный инфраструктурный блок

- аренда и полевой тест VPS (`INFRA-001`);
- real Reed compatibility (`REED-COMPAT-001`);
- hardening/production hosting (`HOST-001`);
- эксплуатационный production backup/restore drill (`OPS-002`);
- домен/DNS/TLS/public URLs/OAuth callbacks (`DOMAIN-001`);
- перенос PostgreSQL и production (`MIG-001`);
- финальный SEC/OPS smoke и `REL-001`.

Эти задачи выполняются **до beta/production**, но не в день публичного запуска: должен оставаться отдельный rollback/observation window.

## 16. Обязательная ближайшая последовательность

### 16.1 Функциональная разработка без аренды VPS

```text
DOC-001 (постоянная синхронизация, не блокирует код)
-> SYNC-001 GitHub/Render verification
-> SYNC-002
-> SEARCH-001
-> SEARCH-002
-> SEARCH-003
-> SEARCH-004
-> AUTH-001
-> AUTH-002
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

### 16.2 Предрелизный инфраструктурный блок

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

## 17. Следующий пакет

Текущий package `SYNC-001` имеет статус **НУЖНА ПРОВЕРКА НА GITHUB/RENDER**. Сначала должны пройти migration `20260807_0003`, новый CI step, Render deploy, external worker heartbeat и queue-to-completion smoke.

После подтверждения следующим кодовым пакетом становится `SYNC-002 — Инкрементальная загрузка и очистка устаревших вакансий`. Он расширит уже созданный worker contract: watermark/cursor policy, закрытие устаревших вакансий, retry/backoff policy и измеримые freshness criteria.

`DOC-001` остаётся постоянным процессом и синхронизируется вместе с каждым code package.

## 18. Обязательный отчёт после каждого пакета

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

## 19. Журнал версий

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
| 1.4.1 | 07.08.2026 | SYNC-001 | Удалён daemon thread из Gunicorn; добавлены durable queue, external worker/CLI, cross-process lock, worker heartbeat, migration `20260807_0003`, Render supervisor, Compose worker service, tests и structured verification runbook. Пакет ожидает GitHub/Render verification. |

