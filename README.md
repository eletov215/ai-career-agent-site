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
- `TRUDVSEM_SYNC_BATCH` - API batch size, default `10`; values above 10 are safely limited to 10 because large responses time out on Render.

The existing "Обновить данные" link only schedules a background refresh and
returns immediately.
