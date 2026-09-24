# AI-005 SITE QA — verification status

| Status | Current value |
|---|---|
| IMPLEMENTED | CANDIDATE |
| CI_PASS | NOT RUN |
| DEPLOYED | NOT RUN |
| SITE_QA_PASS | NOT RUN |
| LIVE_PROVIDER_PASS | NOT RUN |
| QUALITY_PASS | NOT RUN |
| LEGAL_PASS | NO / LEGAL_PENDING |
| COMPLETE | NO |
| Paid Alice calls in implementation | 0 |
| Terraform apply | NOT RUN |
| Production consent mutations | 0 |

## Evidence already inherited

The package intentionally reuses accepted/current AI-005 r2 source-bound runtime controls: provider adapter, strict schema, validation, ledger reservation/settlement, idempotency, no automatic unknown-result retry, proposal workflow and version/TXT behavior. Inherited automated evidence remains distinct from this package's SITE QA evidence.

## Candidate-specific evidence to obtain

- dedicated package guard;
- focused SITE QA runtime/HTTP tests;
- full CI regression;
- predecessor/successor hash-chain checks;
- deploy confirmation;
- zero-cost manual preview smoke;
- separately authorized real Alice synthetic browser call;
- human quality review of the returned proposal.

No live/provider/site status is marked PASS until that exact evidence exists.
