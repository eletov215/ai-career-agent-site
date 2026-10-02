# JOB-004 implementation

JOB-004 adds request-time, owner-scoped personal job-search analytics without persistence or migration. The cohort is distinct saved vacancies selected only by `saved_vacancies.created_at`; complete accepted event history supplies milestone evidence, while the tracker row supplies current state and a missing row means `saved`.

The repository performs two bounded queries: one distinct owner source list and one aggregate cohort query using owner-qualified `EXISTS` predicates. It never reads `snapshot_json`. The service applies rolling 7/30/90/all-time periods, fail-closed source validation, the two approved conversion formulas, and independent sample-size disclosure rules.

`GET /analytics` is limited to authenticated active verified owners and returns no-store/noindex headers. No provider, notification, AI, telemetry, cache, migration, or production configuration is added.
