# LEGAL-OPS-01: privacy worker heartbeat correction

Status at preparation: **IMPLEMENTED / LOCAL_ISOLATED_CHECKS_PASS / NEEDS_CI_AND_PRODUCTION_VERIFICATION**.

## Source and evidence boundaries

- Current GitHub main checked before editing: `97944ef2efb4d81f9e416868aabff234fdc7dc70`.
- Exact baseline tree: `6f9311e16a57af144ea1644a579de29585bccb5e`.
- The locally reconstructed snapshot matched this complete Git tree before editing.
- Owner supplied `LEGAL001_consolidated_QA_2026-09-23(1).md`, completed 12:05 UTC.
  It reports FileNotFoundError for `privacy_cleanup_heartbeat.tmp`, exit code 1,
  automatic restart and successful cleanup on startup and again after waking.
  Data loss or a permanent cleanup outage was not established by that report.
- This correction does not turn historical source/CI/browser observations into
  a new production PASS. The rendered layout fix is already accepted only at
  the sizes actually inspected by QA; other QA limitations remain separate.

## Reproduction and cause found in source

The PostgreSQL advisory-lock branch returns without creating DATA_DIR. The SQLite
file-lock branch creates it, and the web application may create it later. The old
heartbeat writer assumed that the parent already existed. Running its exact
baseline function with a fresh nested DATA_DIR reproduces FileNotFoundError.

The old exception handler then attempted an error-heartbeat on the same missing
path. That second failure escaped the loop and terminated the process. Restart
could appear to fix the symptom after another process had created the directory.
This is a reproducible source-level failure consistent with the observed startup
symptom, not a claim to have inspected a new complete production traceback.

A shared fixed `.tmp` name was also unsafe for concurrent publishers: even a
worker that did not acquire the cleanup lock writes a lock-busy heartbeat.

## Narrow correction

Only `scripts/privacy_cleanup_worker.py` changes application execution:

1. Create the heartbeat parent directory on every publication, safely when it
   already exists. Do not depend on web or sync workers creating it first.
2. Use `NamedTemporaryFile` in that same directory, with unique names and private
   permissions, close it and atomically replace the existing JSON. Remove only
   this publication's temporary file, including on failure.
3. Publish outside the retention exception block. An OSError becomes the distinct
   `privacy_retention_heartbeat_failed` error event with only `error_type`, not
   an exception message, traceback, path or payload. Do not make another failing
   error-heartbeat attempt or misreport a successful cleanup as failed.
4. Continue the existing scheduled loop. A real cleanup failure still produces
   its existing cleanup-failed log and error-status heartbeat when storage works.
   No immediate retry, shortened interval or artificial success is introduced.

The last valid heartbeat remains on failed replacement. Its timestamp does not
advance until a later successful publication; operators must not interpret a
stale file as a healthy worker. Persistent I/O faults remain visible error events
and require investigation, not silent suppression.

The final filename, JSON fields and statuses are unchanged. PostgreSQL advisory
lock and SQLite lock code, retention rules, supervisor, configured interval,
Render environment, health routes and all consent/admission code are unchanged.
Schema remains `20260922_0021`. Policy remains DRAFT / NOT_ACTIVE. Real-data Alice
remains CLOSED. Paid provider calls: **0**.

## Tests and actual local results

`tests/test_privacy_cleanup_worker.py` contains 12 cases:
- Three statuses writing to a missing nested directory, wire shape and permissions.
- Two synchronized concurrent writers, complete JSON and distinct temporary paths.
- Failed replacement preserving the prior JSON and another writer's temp file.
- Cold PostgreSQL-lock path and two simulated scheduled cycles for success,
  lock-busy and genuine cleanup failure, including unlock and dispose.
- Heartbeat I/O failure on those three paths: loop survives, one attempt per cycle,
  no immediate retention retry, and separate safe error events.
- Transient heartbeat failure followed by successful publication on the next cycle.

Local isolated run: **12 passed**. The real worker module was exercised with a
substituted observability logging initializer at import time because Flask is
not installed in this execution environment. DB, service, clock and logging setup
in these unit tests are intentionally synthetic. This does not attest production
imports, real PostgreSQL or the deployed process. No live network/provider call
was made. The focused `Privacy heartbeat regression` workflow uses the installed application
dependencies; the existing full CI also collects these regression tests.

Dependency installation using the repository's pinned requirements was attempted
but the local package source offered no matching Flask distribution. Requirements
were not changed and tests were not skipped to conceal the limitation. Full local
installed-environment pytest: **NOT RUN**. GitHub CI must supply that evidence.

Dependency-free canonical/package preflight: **8 tests OK**, exercising all nine
inherited package guards without changing or disabling them. Counts from these
checks must not be added to overlapping later full-suite results.

Baseline missing-directory reproduction, Python compile and whitespace checks
also completed. Exact candidate/merge SHAs and CI run IDs must be recorded in the
PR after they exist; CI314 applies only to the baseline, not this correction.

## Production retest after green CI and deployment

Confirm the corrected SHA is Live. No new migration or environment change is
required. With read-only logs verify a cold start completes cleanup without the
FileNotFoundError/exit-code-1 loop. If the instance later naturally sleeps/wakes,
check that startup again; do not force repeated production restarts as a test.

A genuine periodic cycle must be recorded separately. The existing code/manifest
interval is 86400 seconds; effective process configuration must be verified.
A short or interrupted observation window cannot establish a 24-hour cycle.
The unit test's controlled clock proves loop behavior, not 24-hour production
uptime. Do not reduce the production interval or promise unexecuted monitoring.

Keep the QA owner's consent and all personal data unchanged. The previous report's
withdrawn/cycle-4/revision-2 is historical QA evidence, not a fresh server read.
Do not repeat export or acceptance actions just to check worker logs.

## Other QA gaps remain tracked, not manufactured away

HTTP/headers, controlled mobile viewports, ZIP/TXT downloads and real PostgreSQL
QA need a capable permitted environment. The old baseline record ID was never
captured and cannot be reconstructed by a new export. The viewed Neon recovery
window did not cover the original migration; a new backup cannot prove an old
backup existed. No production DB access or backup alteration is part of this fix.
