# INFRA-001 - предварительное решение по кандидатам VPS

| Поле | Значение |
|---|---|
| Документ | ADR-INFRA-001 |
| Версия | 1.0 |
| Дата | 06 августа 2026 |
| Статус | ПРЕДВАРИТЕЛЬНОЕ РЕШЕНИЕ, НУЖЕН РЕАЛЬНЫЙ ТЕСТ |
| Основной кандидат | Timeweb Cloud |
| Резервные кандидаты | Yandex Cloud, Beget Cloud, Selectel |

> Итоговый выбор запрещено делать только по маркетинговым характеристикам. Таблица ниже определяет порядок теста, а не объявляет провайдера победителем.

## 1. Критерии

| Критерий | Вес |
|---|---:|
| Доступность без VPN из РФ и РБ | 25% |
| Постоянный публичный IPv4 и сетевой контроль | 15% |
| Backups/snapshots и восстановление | 15% |
| Простота Docker/VPS эксплуатации | 15% |
| Исходящий HTTPS к Yandex AI и Reed | 10% |
| Масштабирование и API/IaC | 10% |
| Стоимость теста и beta | 10% |

## 2. Предварительный shortlist

| Провайдер | Предварительный вывод | Сильные стороны по официальным материалам | Что проверить |
|---|---|---|---|
| Timeweb Cloud | Кандидат №1 для первого теста | Российские площадки, SLA 99.98%, public IP, firewall, backups/snapshots, API/CLI/Terraform/cloud-init, безлимитный трафик | Реальная доступность из РФ/РБ, стабильность IPv4, Reed/Yandex egress, support response |
| Yandex Cloud | Кандидат №2 | Compute Cloud, public IP, snapshots, DDoS-компоненты, близость к Yandex AI Studio | Итоговая стоимость, сложность настройки, backup/restore, доступность из целевых сетей |
| Beget Cloud | Бюджетный кандидат | РФ/Европа/Казахстан, public IPv4, автоматические backups, monitoring, private networks | Производительность 2-4 ГБ RAM, качество network route, limits, API/automation |
| Selectel | Enterprise fallback | Cloud servers, public networking, firewall, snapshots, API/Terraform, развитые network services | Стоимость beta, backup не включён по умолчанию, сложность эксплуатации |

## 3. Проектная рекомендация

Первым развернуть тестовый стенд в Timeweb Cloud в российском регионе. Причины:

1. Низкий порог входа для владельца проекта.
2. Наличие public IP, firewall и встроенных backup/snapshot инструментов.
3. Поддержка API, Terraform, CLI и cloud-init для последующей автоматизации.
4. Возможность теста без немедленной миграции production.

Yandex Cloud держать вторым кандидатом. Он особенно интересен, если AI-BENCH-001 подтвердит Yandex AI Studio и совместное размещение снизит latency/операционную сложность.

## 4. Минимальная конфигурация теста

```text
2 vCPU
4 GB RAM
40 GB NVMe/SSD
1 public IPv4
Ubuntu 24.04 LTS
Russian region
Snapshots/backups enabled
```

## 5. Фактическая оценка после теста

| Критерий | Timeweb | Yandex | Beget | Selectel |
|---|:---:|:---:|:---:|:---:|
| РФ ISP №1 |  |  |  |  |
| РФ ISP №2 |  |  |  |  |
| РФ mobile |  |  |  |  |
| РБ wired/mobile |  |  |  |  |
| TLS and certificate |  |  |  |  |
| Yandex AI egress |  |  |  |  |
| Reed transport |  |  |  |  |
| Backup/restore |  |  |  |  |
| Cost/month |  |  |  |  |
| Support |  |  |  |  |
| Итог |  |  |  |  |

## 6. Официальные источники, проверенные 06.08.2026

- Timeweb Cloud servers: https://timeweb.cloud/services/cloud-servers
- Timeweb Cloud documentation and public IP: https://timeweb.cloud/docs/ and https://timeweb.cloud/docs/public-ip/create-public-ip
- Timeweb Cloud backup: https://timeweb.cloud/services/backup
- Yandex Compute Cloud: https://yandex.cloud/ru/services/compute
- Yandex Compute pricing: https://yandex.cloud/ru/docs/compute/pricing
- Yandex API endpoints: https://yandex.cloud/ru/docs/api-design-guide/concepts/endpoints
- Beget Cloud: https://beget.com/ru/cloud
- Selectel cloud server documentation: https://docs.selectel.ru/cloud/servers/volumes/snapshots/
- Selectel backup methods: https://docs.selectel.ru/cloud-servers/backups/backup-methods/

## 7. Решение

```text
STATUS: PENDING REAL VPS TEST
PRIMARY TEST: TIMEWEB CLOUD
PRODUCTION SWITCH: FORBIDDEN UNTIL HOST-001, DOMAIN-001 AND MIG-001
```

## 8. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 06.08.2026 | Сформирован shortlist и выбран первый кандидат для теста |
