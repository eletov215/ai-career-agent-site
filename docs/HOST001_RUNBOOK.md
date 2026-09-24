# HOST-001 — runbook Yandex Cloud Russia

| Поле | Значение |
|---|---|
| Версия | 1.0 candidate |
| Дата | 24 сентября 2026 |
| Статус | PREPARED / APPLY_FORBIDDEN_WITHOUT_OWNER_AUTHORIZATION |

## 1. Preflight

Confirm GitHub main/approved HOST candidate, current Yandex Cloud prices and a
dedicated Russia-region folder. Do not paste cloud tokens, DB passwords, private
SSH keys or Lockbox values into chat/GitHub.

Run package/Terraform validation first. A green validation run is not proof that
resources exist.

## 2. Billable boundary

`terraform apply` creates a VM, reserved public IPv4 and a two-host Managed
PostgreSQL cluster and therefore may incur charges. Provider selection does not
itself authorize that spend. Obtain a separate owner instruction before apply.

## 3. Field-test sequence after authorization

1. Configure Yandex authentication locally or in a protected deployment runner.
2. Supply non-secret tfvars and protected `TF_VAR_postgresql_app_password`.
3. Review `terraform plan`; reject any non-Russia zone, public PostgreSQL host,
   unrestricted SSH or unexpected resource.
4. Apply.
5. Populate the created Lockbox secret outside Terraform.
6. Deploy repository code to `/opt/ai-career-agent` without copying credentials.
7. Start the Yandex Compose stack through `run_with_lockbox.py`.
8. Verify `/health/live`, `/health/ready`, revision `20260922_0021`, worker
   heartbeats and PostgreSQL reconnect behavior.
9. Run only synthetic/owner-controlled smoke before DOMAIN-001/MIG-001.
10. OPS-002 must create/verify encrypted backup and restore into an isolated
    target before any production migration.
11. Record actual public IP, zone placement, DB hosts, CI/field evidence and cost.

## 4. Domain transition

Before DOMAIN-001 the Caddy default is `:80` for controlled smoke only. Once a
commercial domain is chosen, point its A record at the reserved IPv4, change
`SITE_ADDRESS` to the hostname, update OAuth redirect URIs/TRUSTED_HOSTS/email
sender and verify automatic TLS before public traffic.

## 5. Rollback

Before MIG-001, rollback is simply stopping the Yandex stack; Render remains the
existing staging/runtime path. Do not delete a Managed PostgreSQL cluster or
reserved IP merely to test rollback. Deletion protection is enabled.

After MIG-001, rollback rules must come from MIG-001 and verified backups; HOST-001
does not invent a reverse migration.

## 6. Prohibited shortcuts

No database public IP, no SSH `0.0.0.0/0`, no secret payload in Terraform or
cloud-init, no Alice credential/real data, no legal policy activation, no
commercial launch and no claim that Terraform validate proves 152-FZ compliance.
