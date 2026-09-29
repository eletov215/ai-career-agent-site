# AI-006 implementation

`ai_quality.ai006` builds six versioned synthetic golden cases, calls the unchanged production contract builder and validator, and executes 18 isolated mutation regressions. The layer reuses the production schema/evidence validation and its fixed reason allowlist; it performs no Flask, database, runtime, or network import.

The hard gate compares every metric to an exact threshold. It never derives acceptance from an average score. Any positive validator error, accepted mutation, wrong rule-level reason, or safety counter makes the run fail.

The historical AI-BENCH remains an inherited independent gate. Its schema/scoring/reporting concepts are reused (versioned inputs, machine JSON, Markdown report, sanitized/manual-review artifact) without editing protected AI-BENCH evidence.

Runtime output (`run.json`, `report.md`, `manual_review_template.json`) is written only to a caller-selected temporary directory. Repository evidence contains fingerprints, thresholds, and a deterministic summary, not provider responses or user data.
