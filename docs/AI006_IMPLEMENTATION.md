# AI-006 implementation

`quality/ai006/golden_suite_v1.json` stores the complete source, selected fact IDs, and expected output for six synthetic golden cases. `ai_quality.ai006` loads those immutable inputs, calls the unchanged production contract builder and validator, and executes 18 isolated mutation regressions. Full cases contain an additional grounded candidate fact and candidate-fit paragraph; they are not short outputs evaluated under a larger limit.

The adapter directly reuses AI-BENCH's dependency-free JSON-schema validator, canonical JSON and SHA-256 helpers, and recursive artifact redaction. Historical AI-BENCH reporting cannot be called safely because `render_markdown_report` requires the fixed AI-BENCH-001 provider/run/result schema and emits AI-BENCH-001 contract claims; adapting AI-006 into that shape would misrepresent the evidence. AI-006 therefore has a narrow package-specific Markdown summary while retaining AI-BENCH sanitization and validation primitives. No historical `evals/` source, dataset, regression, or accepted artifact is changed.

The hard gate compares every metric to an exact threshold. Schema, structure and grounding rates are calculated from each executed fixture; safety counters and critical failures are derived from production validation outcomes. It never derives acceptance from an average score. Any positive validator error, accepted mutation, wrong rule-level reason, or safety counter makes the run fail.

## Accepted production grounding contract

The accepted #61 successor requires candidate-fit prose to equal its complete cited fact and restricts subject, opening, motivation, and closing text to fixed title-free templates. AI-006 is rebased on that accepted contract: the six golden outputs use its framing, and the `invented-skill` mutation is rejected with `validation_candidate_claim_grounding`.

The oversized-evidence regression uses eight preflight-valid facts and adds schema-valid caveats only after contract construction. It therefore reaches the validator's persisted-evidence limit deterministically instead of failing contract construction with `input_limit`.

The historical AI-BENCH remains an inherited independent gate. Its schema/scoring/reporting concepts are reused (versioned inputs, machine JSON, Markdown report, sanitized/manual-review artifact) without editing protected AI-BENCH evidence.

Runtime output (`run.json`, `report.md`, `manual_review_template.json`) is written only to a caller-selected temporary directory. Repository evidence contains fingerprints, thresholds, and a deterministic summary, not provider responses or user data.
