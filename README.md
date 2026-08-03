# AI Career Agent

Flask-приложение с OAuth-интеграциями SuperJob и HeadHunter и единым поиском вакансий.

## Что добавлено

- локальная таблица `vacancies` в SQLite;
- кэш вакансий «Работы России» на 30 минут;
- повторные попытки и резервный HTTP/HTTPS адрес API;
- выдача из локальной базы, если внешний API временно недоступен;
- защищённый endpoint фоновой синхронизации `POST /sync/trudvsem`;
- дедупликация вакансий по источнику и внешнему ID.

## Переменные окружения

Существующие переменные OAuth остаются без изменений.

Дополнительно:

- `VACANCY_CACHE_TTL` — время кэша в секундах, по умолчанию `1800`;
- `SYNC_SECRET` — секрет для запуска фоновой синхронизации.

## Фоновая синхронизация

Пример запроса:

```bash
curl -X POST \
  -H "X-Sync-Secret: YOUR_SECRET" \
  "https://YOUR-SITE.onrender.com/sync/trudvsem?keyword=инженер-конструктор&pages=3"
```

Этот endpoint можно вызывать внешним cron-сервисом раз в 30–60 минут. На бесплатном Render встроенный постоянный фоновый процесс ненадёжен, поэтому синхронизация вынесена в отдельный HTTP endpoint.

## Background cache for Работа России

The vacancies page never calls opendata.trudvsem.ru directly. A daemon thread
updates the SQLite cache in small batches, while user searches read only local
data. This prevents slow API responses from blocking navigation on Render.

Optional environment variables:

- `TRUDVSEM_SYNC_INTERVAL` - refresh interval in seconds, default `1800`.
- `TRUDVSEM_SYNC_ITEMS` - maximum vacancies loaded per cycle, default `100`.
- `TRUDVSEM_SYNC_BATCH` - API batch size, default `1` (most reliable on Render).

The existing "Обновить данные" link only schedules a background refresh and
returns immediately.

## Локальная проверка и CI

Тестовые зависимости устанавливаются отдельно от production-зависимостей:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Перед отправкой изменений в GitHub выполнить:

```bash
python scripts/check_repository_hygiene.py .
python -m compileall -q app.py services tests scripts
python -m pytest
```

Файл `.github/workflows/ci.yml` повторяет эти проверки в GitHub Actions на Python 3.12 и 3.13. В тестах запрещены непреднамеренные внешние HTTP-запросы: ответы HeadHunter, SuperJob, Reed и Trudvsem подменяются mock-объектами.

`render.yaml` использует `autoDeployTrigger: checksPass`, поэтому Blueprint-конфигурация запрашивает развёртывание только после успешных CI-проверок. Для уже созданного сервиса дополнительно проверьте в Render: **Settings -> Auto-Deploy -> After CI Checks Pass**.

Тестовая среда использует временный `DATA_DIR`, тестовую SQLite-базу и `TRUDVSEM_SYNC_ENABLED=0`, поэтому не должна запускать фоновую синхронизацию и затрагивать production-данные.

## Статус проверки FND-001

Тестовая инфраструктура подготовлена локально. Пункт считается полностью выполненным только после зелёного GitHub Actions и smoke-проверки развёрнутой версии на Render.

