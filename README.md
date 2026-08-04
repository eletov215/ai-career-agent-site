# AI Career Agent

Flask-приложение с OAuth-интеграциями SuperJob и HeadHunter, единым поиском вакансий, локальным кэшем «Работы России», загрузкой PDF-резюме и конструктором резюме.

## Запуск

Production-команда остаётся неизменной:

```bash
gunicorn app:app
```

Главный рабочий файл — `app.py`. Файлы наподобие `app_fixed.py` не используются.

## Конфигурация приложения

Настройки централизованы в `config.py`. Режим выбирается переменной `APP_ENV`:

| Режим | Значение | Назначение |
|---|---|---|
| Production | `production` | Render и публичный сервис. Это значение используется по умолчанию для обратной совместимости. |
| Development | `development` | Локальная разработка. Debug включён по умолчанию, но секреты всё равно задаются явно. |
| Test | `test` | Автоматические тесты. Только в этом режиме используются безопасные фиктивные OAuth-настройки; фоновая синхронизация отключена. |

`render.yaml` явно задаёт `APP_ENV=production`.

### Обязательные переменные для production и development

```text
FLASK_SECRET_KEY
TOKEN_ENCRYPTION_KEY
SUPERJOB_CLIENT_ID
SUPERJOB_CLIENT_SECRET
SUPERJOB_REDIRECT_URI
HH_CLIENT_ID
HH_CLIENT_SECRET
HH_REDIRECT_URI
HH_USER_AGENT
```

При отсутствии обязательной переменной приложение завершает запуск с понятным сообщением, в котором перечислены недостающие имена. Значения секретов в ошибку не выводятся.

### Необязательные интеграции и технические настройки

```text
HH_APP_TOKEN
REED_API_KEY
SYNC_SECRET
DATA_DIR
VACANCY_CACHE_TTL
VACANCY_PAGE_SIZE
TRUDVSEM_SYNC_ENABLED
TRUDVSEM_SYNC_INTERVAL
TRUDVSEM_SYNC_ITEMS
TRUDVSEM_SYNC_BATCH
TRUDVSEM_REQUEST_ATTEMPTS
TRUDVSEM_RETRY_BACKOFF
HH_CURRENCY_SCAN_PAGES
DEBUG_HH
MAX_RESUME_UPLOAD_MB
FLASK_DEBUG
PORT
```

Все числовые и логические значения проверяются в `config.py`. Некорректное значение останавливает запуск до deploy, а не приводит к случайной ошибке во время пользовательского запроса.

### Локальный development

Перед запуском задайте `APP_ENV=development` и все обязательные переменные в локальном окружении. Встроенных development-секретов нет.

Пример запуска после настройки окружения:

```bash
python app.py
```

Не сохраняйте `.env`, OAuth-токены и реальные ключи в репозитории.

## Кэш и синхронизация «Работы России»

Страница вакансий читает данные «Работы России» из локальной SQLite-базы. Текущая версия всё ещё запускает daemon-поток синхронизации внутри веб-процесса; перенос в отдельный Render Cron Job или worker запланирован пакетом `SYNC-001`.

Защищённый технический endpoint:

```text
POST /sync/trudvsem
X-Sync-Secret: <SYNC_SECRET>
```

Если `SYNC_SECRET` не настроен или заголовок неверен, endpoint отвечает `401`.

## Локальная проверка и CI

Установка зависимостей:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Проверки перед push:

```bash
python scripts/check_repository_hygiene.py .
python -m compileall -q app.py config.py services tests scripts
python -m pytest
```

GitHub Actions выполняет те же проверки на Python 3.11. Внешняя сеть в тестах запрещена: HeadHunter, SuperJob, Reed и Trudvsem проверяются mock-ответами.

Тестовое окружение задаёт `APP_ENV=test`, отдельный временный `DATA_DIR` и технические значения, которые отключают фоновую синхронизацию и ускоряют повторные попытки. Реальные OAuth-настройки, API-ключи и Fernet-ключ тестам не требуются: безопасные фиктивные значения создаются только внутри режима `test`.

## Статус пакетов

- `FND-001` — **ВЫПОЛНЕНО**: GitHub Actions проверен зелёным запуском, намеренно красным тестом и повторным зелёным запуском; Render smoke-проверка подтверждена.
- `FND-002` — **НУЖНА ПРОВЕРКА**: централизованная конфигурация и режимы окружения подготовлены локально; требуется зелёный CI и deploy на Render.
