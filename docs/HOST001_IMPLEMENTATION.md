# HOST-001 — реализация Yandex Cloud Russia foundation

| Поле | Значение |
|---|---|
| Версия | 1.0 candidate |
| Дата | 24 сентября 2026 |
| Статус | IMPLEMENTED_CANDIDATE |
| Cloud | Yandex Cloud / Russia |
| Schema | `20260922_0021` unchanged |
| Application runtime | unchanged |
| Paid actions | none |

## 1. Topology

Initial beta foundation deliberately uses one application VM because the current
rate limiter remains process-local. The database is separate Managed PostgreSQL
17 with two hosts in different zones. Default zones are `ru-central1-d` and
`ru-central1-b`; the Terraform validation rejects non-Russia zones and same-zone
database placement.

The VM receives a reserved public IPv4. Only 80/443 are public; SSH is restricted
to owner-supplied `admin_cidr`. PostgreSQL has no public IP and accepts 6432 only
from the application security group.

## 2. Secrets

Terraform creates a Lockbox secret container but never creates a secret payload.
The VM service account receives `lockbox.payloadViewer` on that single secret.
`run_with_lockbox.py` requests an IAM token from VM metadata, fetches the payload
over HTTPS and injects values directly into the child process environment. It
does not print or persist secret values.

The Managed PostgreSQL password uses Terraform 1.11+ `password_wo`, supplied
through a protected `TF_VAR_postgresql_app_password` channel rather than tfvars.

## 3. Database/TLS

Managed PostgreSQL uses version 17, private hosts and deletion protection. Current
default class is `s3-c2-m8`, `network-ssd`, 20 GiB per host and seven-day
managed backup retention, all parameterized for later cost review.

Yandex Cloud's PostgreSQL endpoint uses port 6432. The VM downloads the official
Yandex CA. The future Lockbox `DATABASE_URL` must specify `sslmode=verify-full`
and the mounted CA path.

## 4. Application boundary

The Yandex Compose stack runs migrate/web/sync/privacy/gateway and optional ops
against external `DATABASE_URL`. Real-data AI remains fail-closed:
`AI_ENABLED=0`, `AI_KILL_SWITCH=1`, `AI_SYNTHETIC_ACCESS_ENABLED=0`; source
`REAL_DATA_SUPPORTED=False` and LEGAL policy DRAFT are not changed.

No application model, route, schema, consent record, user data or production
database is modified by HOST-001 candidate code.

## 5. Current evidence

Repository/static validation and Terraform CI are the only evidence expected
before merge. Cloud field evidence remains NOT_RUN until the owner separately
authorizes a billable Yandex Cloud deployment.
