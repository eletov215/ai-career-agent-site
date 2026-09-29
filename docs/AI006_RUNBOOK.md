# AI-006 runbook

Run the package guard and deterministic gate:

```bash
python scripts/check_ai006_package.py
python -m ai_quality --output-dir /tmp/ai006-quality
python -m pytest -q tests/test_ai006_*.py
```

Inspect `/tmp/ai006-quality/run.json` and `report.md`. A valid machine run has `status=passed`, all exact hard thresholds satisfied, 6/6 golden cases passed, and 18/18 mutations rejected for their expected fixed reason.

Copy `manual_review_template.json` to a review workspace and record a named review of sampled synthetic outputs. Do not commit runtime output, raw provider responses, credentials, or real data. A human pass cannot override machine failure.

No provider credential is read and no live call is needed or allowed by this runbook.
