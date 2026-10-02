# JOB-003 implementation

JOB-003 adds opt-in, owner-scoped calendar-date reminders. It is in-app only: no scheduler, worker, email, push, provider, or network dispatch is present. A missing preference means OFF; preference and reminder writes use optimistic revisions. One reminder is constrained per owned saved vacancy and ownership is enforced by a composite cascading foreign key.

Migration `20261002_0023_in_app_reminders` succeeds `20261001_0022` without backfill. Privacy export and account/saved-vacancy cascades cover both new tables. `REAL_DATA_SUPPORTED=False` and the legal DRAFT boundary are unchanged.
