# INFRA-001 - инструкция по тестированию российского VPS

| Поле | Значение |
|---|---|
| Документ | INFRA001-VPS-TEST |
| Версия | 1.1 |
| Дата | 07 августа 2026 |
| Статус | ОТЛОЖЕНО ДО ПРЕДРЕЛИЗНОГО INFRA-001 |
| Результат | Заполняется после создания VPS |

## 1. Рекомендуемая тестовая конфигурация

| Ресурс | Минимум для теста | Рекомендуется для beta |
|---|---:|---:|
| vCPU | 2 | 2-4 |
| RAM | 4 ГБ | 4-8 ГБ |
| NVMe/SSD | 40 ГБ | 60-80 ГБ |
| Public IPv4 | 1 постоянный | 1 постоянный |
| ОС | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS |
| Канал | от 100 Мбит/с | от 100 Мбит/с |
| Snapshots/backups | обязательно | обязательно + offsite |

## 2. Подготовка сервера

1. Создать VPS и добавить SSH public key.
2. Зафиксировать provider, region, tariff, public IPv4 и стоимость.
3. Обновить ОС.
4. Установить Docker Engine и Docker Compose v2 из официального репозитория Docker.
5. Клонировать репозиторий в каталог `/opt/ai-career-agent`.
6. Скопировать `infra/vps/.env.example` в `.env` и заполнить только на сервере.
7. Ограничить права:

```bash
chmod 600 .env
```

## 3. Проверка manifest до запуска

```bash
python3 scripts/infra_manifest_check.py
docker compose --env-file .env config > /tmp/aca-compose.yml
test -s /tmp/aca-compose.yml
```

Ожидается `ok: true` и отсутствие ошибок Compose.

## 4. Direct IPv4 test без TLS

Для краткого первичного теста:

```text
WEB_BIND_ADDRESS=0.0.0.0
WEB_PUBLISH_PORT=8000
TRUDVSEM_SYNC_ENABLED=0
```

Запуск:

```bash
docker compose --env-file .env build web ops
docker compose --env-file .env up -d db
docker compose --env-file .env run --rm migrate
docker compose --env-file .env up -d web
docker compose --env-file .env --profile sync up -d sync-worker
```

Проверка на VPS:

```bash
curl -fsS http://127.0.0.1:8000/health/live
curl -fsS http://127.0.0.1:8000/health/ready
```

Проверка извне:

```text
http://<PUBLIC_IPV4>:8000/health/ready
```

После direct test порт 8000 необходимо закрыть firewall и переключить `WEB_BIND_ADDRESS=127.0.0.1`.

## 5. TLS test через временный hostname

1. Создать временную DNS A-запись на public IPv4.
2. Указать:

```text
VPS_TEST_HOST=infra-test.example.com
TRUSTED_HOSTS=infra-test.example.com
WEB_BIND_ADDRESS=127.0.0.1
```

3. Запустить gateway:

```bash
docker compose --env-file .env --profile tls up -d gateway
```

4. Проверить:

```bash
curl -fsS https://infra-test.example.com/health/ready
```

## 6. Автоматический probe

```bash
python scripts/infra_probe.py \
  --base-url https://infra-test.example.com \
  --timeout 15 \
  --strict \
  --json-output infra/reports/vps-probe.json \
  --markdown-output infra/reports/vps-probe.md
```

Required checks:

- application live/ready/home;
- Yandex Cloud endpoint catalogue;
- Yandex AI edge TLS/HTTPS;
- Reed API transport reachability.

Optional checks:

- HeadHunter;
- Trudvsem;
- SuperJob.

## 7. Матрица доступности

Заполнить без VPN:

| Страна | Сеть | Устройство | DNS | TCP 443 | TLS | Главная | Search | PDF | Результат |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| РФ | Проводной ISP №1 | ПК |  |  |  |  |  |  |  |
| РФ | Проводной ISP №2 | ПК/ноутбук |  |  |  |  |  |  |  |
| РФ | Мобильная сеть №1 | iPhone |  |  |  |  |  |  |  |
| РФ | Мобильная сеть №2 | Android/iPhone |  |  |  |  |  |  |  |
| РБ | Проводная сеть | ПК |  |  |  |  |  |  |  |
| РБ | Мобильная сеть | Телефон |  |  |  |  |  |  |  |

## 8. Ручной smoke сайта

Проверить:

```text
/
/privacy
/ai-career
/resume-builder
/vacancies/internal
/health/live
/health/ready
/api/sources/trudvsem/status
```

Сценарии:

- обычный поиск вакансий;
- загрузка корректного PDF;
- отклонение некорректного PDF;
- security headers;
- CSRF `400`;
- rate limit `429`;
- request ID в structured logs.

## 9. Завершение OPS-001 на VPS

### 9.1 Создать encrypted backup Render PostgreSQL

Использовать External Database URL Render только как временную переменную shell. Не сохранять URL в Git, issue, screenshot или отчёт.

```bash
docker compose --env-file .env --profile ops run --rm --no-deps \
  -e APP_ENV=production \
  -e DATABASE_URL="$RENDER_DATABASE_URL" \
  ops python scripts/backup_database.py \
  --output-dir /var/backups/ai-career-agent \
  --name render-production.dump
```

### 9.2 Проверить manifest и SHA-256

```bash
docker compose --env-file .env --profile ops run --rm --no-deps \
  ops python scripts/verify_backup.py \
  --backup /var/backups/ai-career-agent/render-production.dump.enc
```

### 9.3 Создать isolated restore database

```bash
docker compose --env-file .env --profile restore-test up -d restore-db
```

### 9.4 Восстановить копию

```bash
docker compose --env-file .env --profile ops --profile restore-test run --rm --no-deps \
  -e APP_ENV=development \
  -e RESTORE_DATABASE_URL="$RESTORE_DATABASE_URL" \
  ops python scripts/restore_database.py \
  --backup /var/backups/ai-career-agent/render-production.dump.enc \
  --clean
```

Подтвердить:

- `database_revision=20260807_0004`;
- table counts совпадают с manifest;
- production database не была целью restore.

## 10. Нагрузочный sanity check

Пакет не заменяет полноценный load test. Для первичной оценки записать:

| Метрика | Порог |
|---|---:|
| `/health/live` p95 | <= 500 мс |
| `/health/ready` p95 | <= 1500 мс |
| Главная p95 | <= 2500 мс |
| Ошибки 5xx в 10 мин | 0 |
| RAM после smoke | < 80% |
| Disk after build | < 70% |

## 11. Завершение теста

1. Скачать probe report и backup manifest в защищённое offsite storage.
2. Удалить временные diagnostics/webhook secrets.
3. Закрыть port 8000.
4. Остановить test stack, если провайдер отклонён.
5. Заполнить `docs/INFRA001_PROVIDER_DECISION.md` фактическими результатами.
