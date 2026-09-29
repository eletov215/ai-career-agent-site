# AI-006 runbook

Run the package guard and deterministic gate:

```bash
python scripts/check_ai006_package.py
python -m ai_quality --output-dir /tmp/ai006-quality
python -m pytest -q tests/test_ai006_*.py
```

Inspect `/tmp/ai006-quality/run.json` and `report.md`. The current reference run intentionally has `status=failed`: 6/6 golden cases pass, but the production validator accepts the `invented-skill` mutation backed by a valid unrelated quote. Until a separately reviewed production successor closes that semantic-grounding gap, AI-006 remains `BLOCKED_BY_PRODUCTION_GAP` and must not be reported as QUALITY_PASS.

Copy `manual_review_template.json` to a review workspace and record a named review of sampled synthetic outputs. Do not commit runtime output, raw provider responses, credentials, or real data. A human pass cannot override machine failure.

No provider credential is read and no live call is needed or allowed by this runbook.
