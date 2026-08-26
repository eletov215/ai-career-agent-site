#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def fail(message: str) -> int:
    print(f"AI-BENCH live transport gate failed: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if len(sys.argv) != 2:
        return fail("usage: check_ai_bench_live_result.py <run.json>")
    path = Path(sys.argv[1])
    try:
        run = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"cannot read run evidence: {exc}")
    if run.get("execution_mode") != "live_or_mixed":
        return fail(f"unexpected execution_mode={run.get('execution_mode')!r}")
    providers = run.get("providers") or []
    if len(providers) < 2:
        return fail("comparative run must contain at least two live providers")
    transport_failures: list[str] = []
    for provider in providers:
        summary = provider.get("summary") or {}
        if int(summary.get("case_count") or 0) <= 0:
            transport_failures.append(f"{provider.get('id')}: no cases")
        if int(summary.get("error_count") or 0) > 0:
            transport_failures.append(f"{provider.get('id')}: error_count={summary.get('error_count')}")
    if transport_failures:
        return fail("; ".join(transport_failures))
    print("AI-BENCH live transport gate passed")
    for provider in providers:
        summary = provider.get("summary") or {}
        print(
            f"{provider.get('id')}: passed={summary.get('passed_count')}/{summary.get('case_count')} "
            f"quality={summary.get('mean_quality_score')} grounding={summary.get('mean_grounding_score')} "
            f"retries={summary.get('retry_count')} language_violations={summary.get('language_consistency_violation_count')} "
            f"scenario_violations={summary.get('scenario_provenance_violation_count')} "
            f"p95_ms={summary.get('p95_latency_ms')} cost_usd={summary.get('estimated_cost_usd')}"
        )
    print("Machine quality failures are benchmark evidence and do not fail this transport gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
