# AI-006 runbook

Run the package guard and deterministic gate:

```bash
python scripts/check_ai006_package.py
python -m ai_quality --output-dir /tmp/ai006-quality
python -m pytest -q tests/test_ai006_*.py
```

Inspect `/tmp/ai006-quality/run.json` and `report.md`. The current deterministic reference run has `status=passed`: all six golden cases validate against the accepted title-free framing contract and all 18 negative mutations are rejected with their expected reasons.

Copy `manual_review_template.json` to a review workspace and record a named review of sampled synthetic outputs. Do not commit runtime output, raw provider responses, credentials, or real data. A human pass cannot override machine failure.

No provider credential is read and no live call is needed or allowed by this runbook.
