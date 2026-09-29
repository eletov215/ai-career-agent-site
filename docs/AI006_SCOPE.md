# AI-006 scope

AI-006 adds a deterministic, offline quality gate for AI-authored cover letters. It uses only versioned synthetic RU/EN inputs and makes **zero provider calls**.

## Boundaries

- `REAL_DATA_SUPPORTED=False`; real-data Alice remains closed.
- Legal policy remains `DRAFT / NOT_ACTIVE`; consent state is unchanged.
- No production runtime, database schema, migration, infrastructure, provider configuration, key, budget, or employer auto-send change is in scope.
- Historical AI-BENCH 1.6.1 / benchmark 1.4 / dataset 1.3.6 / `grounded-v2.6.1` artifacts remain byte-preserved.
- The production `cover-letter-draft-v1` builder and validator are imported as pure functions and are not copied or weakened.

The package is an additive quality layer under `ai_quality/` and `quality/ai006/`. Machine safety is fail-closed; manual writing review is separate and cannot override a machine failure.
