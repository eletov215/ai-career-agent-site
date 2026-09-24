# HOST-001 — verification status

| Поле | Статус |
|---|---|
| Package | HOST-001 |
| Candidate baseline | `b25c1491cc418e79917fcd21325f807315b9c559` |
| Owner cloud decision | Yandex Cloud |
| Initial market | Russia |
| Minimum age | 18+ |
| IaC implementation | IMPLEMENTED |
| Terraform fmt/validate | PENDING_CI |
| Package guard/tests | PENDING_CI |
| Cloud resources created | NO |
| Billable cloud actions | 0 |
| Field network test | NOT_RUN |
| Managed PostgreSQL field test | NOT_RUN |
| OPS-002 restore drill | NOT_RUN |
| DOMAIN-001 | PENDING |
| MIG-001 | PENDING |
| Legal activation | PENDING |
| Real-data Alice | CLOSED |
| Acceptance | NOT_YET |

## 1. Candidate criteria

The candidate must pass Terraform formatting/validation and package/unit guards
without Yandex credentials. Guarding must prove Russia-only default zones,
two-zone private PostgreSQL, SG-only 6432, restricted SSH, Lockbox/no-secret-state
design and fail-closed AI defaults.

## 2. Field criteria

A later billable field test must verify the exact created resources, network
reachability, Managed PostgreSQL TLS/reconnect, app readiness, workers, backup
and isolated restore. Results must be recorded from the actual Yandex environment.

## 3. Separation from legal acceptance

HOST-001 can pass technically while LEGAL-001 remains LEGAL_PENDING. Operator
identity, domain, final legal documents and policy activation remain independent
gates. No infrastructure PASS enables real-data AI by itself.
