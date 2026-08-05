# AI Career Agent - Единый план реализации и ведения разработки

**Версия:** 1.2.6  
**Дата:** 04 августа 2026  
**Статус:** ДЕЙСТВУЮЩИЙ  
**Основа:** `ai-career-agent-site-main-14-data-002-domain-repositories-v1.2.6.zip`

> ОБЯЗАТЕЛЬНО ДЛЯ КАЖДОГО НОВОГО ЧАТА: прочитать этот план, новый паспорт и актуальный архив. После завершения любого пункта вернуть обновлённые DOCX/PDF/Markdown, новый ZIP, доказательства проверки и запись в журнале версий.

> КОНТРОЛЬНЫЕ СТАТУСЫ ЭТОЙ ВЕРСИИ: `FND-001 — ВЫПОЛНЕНО`; `FND-002 — ВЫПОЛНЕНО`; `DATA-001 — ВЫПОЛНЕНО`; `DATA-002 — НУЖНА ПРОВЕРКА`; `DOMAIN-001 — ЗАПЛАНИРОВАНО, ЭТАП 6, ОБЯЗАТЕЛЕН ДО BETA`. PDF с версией `1.0.1` или иными статусами является устаревшей копией.

## 1. Источник истины и аудит источников

- GitHub является главным источником актуального кода.
- Если в текущем чате загружен более новый ZIP, он является рабочей основой этого чата.
- Канонический план определяется наибольшей версией и датой; старые дубликаты не должны оставаться действующими.
- Перед DATA-002 проверено, что актуальный код находится в `ai-career-agent-site-main (1).zip` и соответствует завершённому DATA-001.
- Загруженные планы/паспорт были устаревшими: они содержали версии 1.0.0/1.0.1 и раннее состояние HH 403, не отражали подтверждение FND-001/FND-002 и согласованную стратегию собственного домена/VPS.
- Версия 1.2.6 является канонической candidate-версией: FND-001, FND-002 и DATA-001 подтверждены как ВЫПОЛНЕНО; DATA-002 реализован и имеет статус НУЖНА ПРОВЕРКА до GitHub/Render подтверждения. DOMAIN-001 подтверждён как отдельный пакет этапа 6.

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
| Тесты | GitHub Actions, unit/provider/route/config/database/migration tests. |
| Hosting | Render сейчас; собственный домен обязателен до beta; VPS - решение после metrics/readiness. |

### 5.1 Выполнено/частично

- BASE-001: Flask/Gunicorn/Render и публичные страницы - реализовано.
- BASE-002: единый поиск по текущим providers - реализован в текущем объёме.
- BASE-003: HH/SJ OAuth и encryption - частично, нужен User binding/E2E.
- BASE-004: Trudvsem cache - частично, worker ещё внутри web process.
- BASE-005: filters/sort/pagination - реализованы, но cross-source consistency требует SEARCH packages.
- BASE-006: PDF parse - частично, это не AI.
- BASE-007: resume builder/live preview/PDF/mobile - реализовано.
- BASE-008: спокойные homepage transitions/reduced motion - реализовано.
- BASE-009..012: own account, real AI, server saved jobs, tracker/legal/commercial core - впереди.

### 5.2 Ключевые риски

| ID | Уровень | Риск |
|---|---|---|
| R-01 | Закрыт 04.08.2026 | Production переведён на PostgreSQL; restart подтвердил сохранность кэша и служебного состояния. |
| R-02 | Высокий | Trudvsem daemon thread зависит от Gunicorn. |
| R-03 | Высокий | Публичные technical endpoints/forms/sessions требуют SEC-001. |
| R-04 | Высокий | Межисточниковые дубли и нестабильный total/pagination. |
| R-05 | Высокий | Маркетинговые AI promises опережают real implementation. |
| R-06 | Средний | Большие assets и inline JS усложняют performance/support. |
| R-07 | Средний | VPS без operational readiness создаёт single point of failure и security burden. |

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
| DATA-002 | P0 | НУЖНА ПРОВЕРКА | Базовая доменная модель и слой доступа к данным |
| SEC-001 | P0 | ЗАПЛАНИРОВАНО | Базовое усиление безопасности |
| OPS-001 | P0 | ЗАПЛАНИРОВАНО | Наблюдаемость, безопасные логи и резервное восстановление |
| DOC-001 | P0 | ЗАПЛАНИРОВАНО | Синхронизация README, ROADMAP, CHANGELOG и фактического кода |

### Этап 2. Надёжный поиск и обновление вакансий

| ID | Приоритет | Статус | Пункт |
|---|---|---|---|
| SYNC-001 | P0 | ЗАПЛАНИРОВАНО | Вынести синхронизацию Trudvsem из web-процесса |
| SYNC-002 | P1 | ЗАПЛАНИРОВАНО | Инкрементальная загрузка и очистка устаревших вакансий |
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

### Этап 6. Коммерческий запуск, домен и hosting

| ID | Приоритет | Статус | Пункт |
|---|---|---|---|
| DOMAIN-001 | P0 до beta | ЗАПЛАНИРОВАНО | Собственный домен, DNS, TLS и публичные URL |
| INFRA-001 | P1 | ЗАПЛАНИРОВАНО | Платформонезависимая упаковка и контейнеризация |
| HOST-001 | P1 перед коммерческим запуском | ЗАПЛАНИРОВАНО | Выбор production-площадки и миграция с Render |
| OPS-002 | P0 при выборе VPS | ЗАПЛАНИРОВАНО | Эксплуатация собственного VPS |
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
**Статус:** НУЖНА ПРОВЕРКА

**Цель:** Отделить persistence от Flask routes и подготовить данные для аккаунта, профиля, вакансий и синхронизаций.

**Реализация:** Добавлены User, unified OAuthConnection, canonical Vacancy, VacancySourceRecord, SyncRun, immutable User/OAuth/Vacancy/Source/SyncRun records, repositories и StorageServices. Migration `20260804_0002` копирует legacy OAuth rows, преобразует source-only vacancies без потери raw data и выравнивает PostgreSQL sequence. app.py больше не импортирует SQLAlchemy/ORM/concrete repositories; OAuth writes временно dual-write в legacy tables; VacancyStore делегирует SQL; Trudvsem сохраняет sync lifecycle.

**Влияние на код:** domain/, models/, repositories/, services/storage.py, services/vacancy_store.py, app.py, migration 0002, legacy importer, CI, tests и документация.

**Влияние на сайт:** Визуально ничего не меняется. Existing OAuth/session/templates и search payload совместимы. `/trudvsem/status` после sync может показать persisted_run.

**Критерии готовности:** Локально migration/rollback/alembic check и 55 tests пройдены; требуется зелёный GitHub Actions, PostgreSQL legacy migration/integration без skip, Render `/health` revision `20260804_0002`, OAuth/search smoke и restart persistence.

**Зависимости:** DATA-001.

#### SEC-001 - Базовое усиление безопасности

**Приоритет:** P0  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Защитить формы, сессии, загрузки и технические endpoints до появления реальных аккаунтов.

**Реализация:** Secure/HttpOnly/SameSite cookies, CSRF, rate limiting, security headers, нейтральные ошибки, ограничения PDF, закрытие debug/refresh.

**Влияние на код:** config.py, app.py, security middleware, templates/forms, requirements, tests.

**Влияние на сайт:** Технические URL закрываются; пользователь видит аккуратные ошибки без внутренних деталей.

**Критерии готовности:** CSRF и rate limits работают; cookie flags подтверждены; секреты не попадают в ответы/логи.

**Зависимости:** FND-002; желательно DATA-001.

#### OPS-001 - Наблюдаемость, безопасные логи и резервное восстановление

**Приоритет:** P0  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Быстро обнаруживать сбои и иметь проверяемую процедуру восстановления.

**Реализация:** Структурированные логи, correlation ID, error monitoring, provider metrics, health/readiness, backup/restore runbook.

**Влияние на код:** logging config, app.py, providers, DB scripts, docs, hosting settings.

**Влияние на сайт:** Меньше необъяснимых ошибок; администратор видит источник сбоя без персональных данных.

**Критерии готовности:** Health не раскрывает секреты; backup восстановлен на тестовой базе; alert доставлен.

**Зависимости:** DATA-001.

#### DOC-001 - Синхронизация README, ROADMAP, CHANGELOG и фактического кода

**Приоритет:** P0  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Исключить противоречивые источники и повторение уже выполненных задач.

**Реализация:** После каждого пакета сверять docs, паспорт, PLAN_CURRENT и актуальный архив.

**Влияние на код:** README, docs/*, PLAN_CURRENT, паспорт.

**Влияние на сайт:** Прямого изменения сайта нет; снижается риск неверных правок и обещаний.

**Критерии готовности:** Один канонический план; статусы подтверждаемы; устаревшие дубликаты удалены.

**Зависимости:** Постоянный процесс.

### Этап 2. Надёжный поиск и обновление вакансий

#### SYNC-001 - Вынести синхронизацию Trudvsem из web-процесса

**Приоритет:** P0  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Не связывать актуальность кэша с жизненным циклом Gunicorn.

**Реализация:** Создать отдельную CLI/worker command; хранить SyncRun; блокировать параллельные запуски; запускать scheduler платформы или cron/VPS.

**Влияние на код:** app.py, trudvsem_provider.py, commands/, models/repositories, hosting config, tests.

**Влияние на сайт:** Поиск стабильнее, web-request не запускает daemon thread, статус синхронизации становится реальным.

**Критерии готовности:** Web не создаёт фоновые потоки; job повторяем; ошибки сохраняют старый кэш.

**Зависимости:** DATA-001, DATA-002, OPS-001.

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

**Цель:** Дать продукту постоянный адрес, независимый от Render/VPS.

**Трассировка:** Пакет не потерян и не интегрирован в DATA-002. Он добавлен в версии 1.1.0, остаётся отдельным пунктом этапа 6 и выполняется после SEC-001/OPS-001 до публичной beta.

**Реализация:** Register domain, DNS, TLS, PUBLIC_BASE_URL, OAuth callbacks, cookie/CSRF trusted origins, email DNS.

**Влияние на код:** config, routes generating absolute URLs, hosting/DNS docs, OAuth provider settings.

**Влияние на сайт:** Пользователи видят коммерческий домен; переход между хостингами не меняет адрес.

**Критерии готовности:** HTTPS works; www/app policy fixed; HH/SJ callbacks pass; old URL redirects intentionally.

**Зависимости:** SEC-001; до публичных accounts/OAuth beta.

#### INFRA-001 - Платформонезависимая упаковка и контейнеризация

**Приоритет:** P1  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Подготовить одинаковый запуск на Render, VPS и CI.

**Реализация:** Dockerfile, .dockerignore, Compose web/db/worker/migrations, non-root, healthcheck.

**Влияние на код:** Docker/Compose, deploy/render, deploy/vps, CI image build.

**Влияние на сайт:** Пользователь не замечает; команда получает воспроизводимый deploy.

**Критерии готовности:** Image builds; migrations one-shot; secrets not baked; same tests pass.

**Зависимости:** DATA-001, SYNC-001 желательно.

#### HOST-001 - Выбор production-площадки и миграция с Render

**Приоритет:** P1 перед коммерческим запуском  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Выбрать paid Render или VPS на основании метрик, а не предположений.

**Реализация:** Сравнить cost, CPU/RAM, DB/worker/backup, data region, ops readiness; perform staging migration and rollback drill.

**Влияние на код:** Hosting docs/config, deployment scripts, DNS switch plan.

**Влияние на сайт:** При сохранении собственного домена смена площадки прозрачна.

**Критерии готовности:** Decision record approved; load test; backup restore; rollback; no unplanned downtime.

**Зависимости:** DOMAIN-001, INFRA-001, OPS-001.

#### OPS-002 - Эксплуатация собственного VPS

**Приоритет:** P0 при выборе VPS  
**Статус:** ЗАПЛАНИРОВАНО

**Цель:** Безопасно обслуживать VPS, если он выбран.

**Реализация:** SSH keys, no password/root login, firewall, patches, reverse proxy/TLS, offsite backups, restore, monitoring, log rotation, deploy/rollback.

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

### 10.5 Требуемая verification

1. GitHub Actions зелёный, включая seeded legacy PostgreSQL migration, sequence и integration test.
2. Render deploy применяет revision `20260804_0002`.
3. `/health` показывает postgresql/persistent/configured и revision 0002.
4. OAuth/search/resume smoke без HTTP 500.
5. Existing connections/cache остаются после migration/restart.
6. `/trudvsem/status` после run содержит secret-free `persisted_run`.

### 10.6 Ограничения

- User account UI/passwords не входят в DATA-002.
- Legacy account tables удаляются только отдельной cleanup migration после AUTH-002.
- Canonical vacancy пока one-to-one с source record; actual cross-source merge относится к SEARCH-002.
- Trudvsem thread остаётся в Gunicorn до SYNC-001.

## 11. Стратегия домена и hosting

- Собственный домен обязателен к коммерческой beta и может сначала указывать на Render.
- Первая beta: paid Render + own domain + managed PostgreSQL - минимальный operational risk.
- VPS не является обязательным заранее. Решение принимается после реальных 30-дневных metrics, load test, backup restore и operational readiness.
- Архитектура строится portability-first: DATABASE_URL, stdout logs, separate worker commands, object storage, Docker/Compose later.
- При миграции users продолжают видеть один домен; DNS переключается с Render на VPS после staging/data sync/rollback rehearsal.

## 12. Ближайшая последовательность

```text
DATA-002 verification
-> SEC-001
-> OPS-001
-> DOMAIN-001
-> SYNC-001/SEARCH core
-> AUTH/PROFILE
-> AI
-> JOB tracker
-> commercial release gates
```

## 13. Следующий пакет

DATA-002 имеет статус **НУЖНА ПРОВЕРКА**. После зелёного CI, Render revision `20260804_0002` и smoke/persistence-проверки он перейдёт в ВЫПОЛНЕНО, а `SEC-001 - Базовое усиление безопасности` станет ГОТОВО К СТАРТУ. DOMAIN-001 остаётся следующим инфраструктурным пакетом после SEC-001 и OPS-001.

## 14. Обязательный отчёт после каждого пакета

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

## 15. Журнал версий

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
