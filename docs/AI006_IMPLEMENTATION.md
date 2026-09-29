# AI-006 implementation

`quality/ai006/golden_suite_v1.json` stores the complete source, selected fact IDs, and expected output for six synthetic golden cases. `ai_quality.ai006` loads those immutable inputs, calls the unchanged production contract builder and validator, and executes 18 isolated mutation regressions. Full cases contain an additional grounded candidate fact and candidate-fit paragraph; they are not short outputs evaluated under a larger limit.

The adapter directly reuses AI-BENCH's dependency-free JSON-schema validator, canonical JSON and SHA-256 helpers, and recursive artifact redaction. Historical AI-BENCH reporting cannot be called safely because `render_markdown_report` requires the fixed AI-BENCH-001 provider/run/result schema and emits AI-BENCH-001 contract claims; adapting AI-006 into that shape would misrepresent the evidence. AI-006 therefore has a narrow package-specific Markdown summary while retaining AI-BENCH sanitization and validation primitives. No historical `evals/` source, dataset, regression, or accepted artifact is changed.

The hard gate compares every metric to an exact threshold. Schema, structure and grounding rates are calculated from each executed fixture; safety counters and critical failures are derived from production validation outcomes. It never derives acceptance from an average score. Any positive validator error, accepted mutation, wrong rule-level reason, or safety counter makes the run fail.

## Blocking production grounding gap

AI-006's `invented-skill` mutation changes visible prose to `I design Kubernetes clusters.` while retaining the valid verbatim source quote `I maintain Python APIs and write SQL queries.` The unchanged production validator accepts that response because it proves quote integrity but does not establish semantic entailment between prose and quote. AI-006 records the accepted mutation as one unsupported candidate claim and fails closed with `BLOCKED_BY_PRODUCTION_GAP` package status; it does not disguise the gap with a different expected reason.

The required separate successor change should add a reviewed semantic-grounding rule to `services/ai/letter_contract.py`, assign a fixed allowlisted validation reason, add isolated contract/runtime tests, and extend the existing AI-005 successor hash chain. That production change requires architecture review and is intentionally not part of PR #59.

The historical AI-BENCH remains an inherited independent gate. Its schema/scoring/reporting concepts are reused (versioned inputs, machine JSON, Markdown report, sanitized/manual-review artifact) without editing protected AI-BENCH evidence.

Runtime output (`run.json`, `report.md`, `manual_review_template.json`) is written only to a caller-selected temporary directory. Repository evidence contains fingerprints, thresholds, and a deterministic summary, not provider responses or user data.
