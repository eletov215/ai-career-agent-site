# Repository operating rules

- Treat GitHub as the source of truth. Verify the current remote `main` baseline before work, and never claim remote GitHub state when GitHub access is unavailable.
- Never edit or commit directly on `main`. Use: branch -> inspect -> minimal change -> tests -> PR -> CI -> report.
- Do not weaken historical package, hash, or evidence guards. Investigate actual CI logs before fixing; for likely transient external failures, safely rerun before editing.
- Explicitly report every `NOT_RUN` check. Keep these states distinct: `IMPLEMENTED`, `CI_PASS`, `DEPLOYED`, `SITE_QA_PASS`, `LIVE_PROVIDER_PASS`, `QUALITY_PASS`, `LEGAL_PASS`, and `COMPLETE`.
- Make 0 billable Alice/Yandex calls unless the owner explicitly approves them.
- Preserve `REAL_DATA_SUPPORTED=False` and the legal policy's `DRAFT` state. Do not make Render, Neon, or Yandex production changes; DB schema or migration changes; or run `terraform apply`.
- Do not start AI-006 implicitly.
