---
name: aca-pr-review
description: Review a pull request before merge or inspect its post-merge result. Use when validating exact revisions, scope, safeguards, checks, operational boundaries, and merge readiness without making the merge decision.
---

# Review a pull request

Check and report:

- exact base SHA and head SHA;
- changed-file scope;
- unexpected runtime, data, or legal changes;
- historical guards;
- required tests and workflows;
- skipped and `NOT_RUN` checks;
- billable provider-call status;
- production-change status;
- mergeability;
- post-merge CI, when applicable.

Do not merge without explicit owner authorization. If GitHub is unavailable, distinguish locally verified facts from inaccessible remote state.
