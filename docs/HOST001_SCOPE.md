# HOST-001 — Yandex Cloud Russia foundation

| Поле | Значение |
|---|---|
| Версия | 1.0 candidate |
| Дата | 24 сентября 2026 |
| Baseline | `b25c1491cc418e79917fcd21325f807315b9c559` |
| Owner decision | Yandex Cloud; Russia-only initial launch; 18+ |
| Статус | IMPLEMENTED_CANDIDATE / NO_APPLY / NEEDS_CI_AND_FIELD_TEST |
| Real-data Alice | CLOSED |
| Paid provider calls | 0 |

## 1. Цель

Подготовить воспроизводимую production-foundation инфраструктуру в Yandex Cloud
Russia без аренды ресурсов в рамках этого commit. HOST-001 заменяет исторический
Timeweb-first shortlist для текущего owner-approved направления, не переписывая
старые evidence-файлы.

## 2. Входит в пакет

- Terraform для российского VPC, двух subnets, SG, reserved IPv4 и одной app VM.
- Managed PostgreSQL 17 с двумя private hosts в разных российских zones.
- Lockbox metadata + least-privilege VM service account; secret payload вне Terraform.
- Yandex-specific Compose stack без локального PostgreSQL.
- HTTPS-ready Caddy, но pre-domain smoke по HTTP допустим только на synthetic data.
- Static package guard, unit checks и dedicated no-apply CI.
- Owner decision record 18+/Russia/Yandex Cloud.

## 3. Не входит

Реальный `terraform apply`, оплата Yandex Cloud, перенос Render/Neon данных,
commercial domain, production TLS identity, offsite backup/restore acceptance,
payment integration, final legal documents, policy activation и Alice real-data
credentials/calls.

## 4. Acceptance boundary

Candidate становится HOST-001 field-test PASS только после отдельно разрешённого
создания ресурсов, проверки network/database/readiness, encrypted backup/restore
drill и rollback procedure. Коммерческий production switch всё равно требует
DOMAIN-001, MIG-001 и оставшиеся legal gates.
