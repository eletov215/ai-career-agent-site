#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED_PROVIDER = "yandex-alice-ai-llm"


def fail(message: str) -> int:
    print(f"AI-BENCH Alice final gate failed: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if len(sys.argv) != 2:
        return fail("usage: check_ai_bench_alice_final_result.py <run.json>")
    path = Path(sys.argv[1])
    try:
        run = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"cannot read run evidence: {exc}")
    if run.get("execution_mode") != "live_or_mixed":
        return fail(f"unexpected execution_mode={run.get('execution_mode')!r}")
    if run.get("schema_version") != "1.4" or run.get("benchmark_version") != "1.4":
        return fail(
            f"unexpected benchmark contract schema={run.get('schema_version')!r} "
            f"benchmark={run.get('benchmark_version')!r}"
        )
    dataset = run.get("dataset") or {}
    if dataset.get("version") != "1.3.6":
        return fail(f"unexpected dataset version={dataset.get('version')!r}")
    providers = run.get("providers") or []
    if len(providers) != 1 or providers[0].get("id") != EXPECTED_PROVIDER:
        return fail("final verification must contain only yandex-alice-ai-llm")
    summary = providers[0].get("summary") or {}
    case_count = int(summary.get("case_count") or 0)
    passed_count = int(summary.get("passed_count") or 0)
    error_count = int(summary.get("error_count") or 0)
    dataset_count = int((run.get("dataset") or {}).get("case_count") or 0)
    if case_count <= 0 or case_count != dataset_count:
        return fail(f"case_count mismatch provider={case_count} dataset={dataset_count}")
    if error_count:
        return fail(f"provider error_count={error_count}")
    if passed_count != case_count or run.get("status") != "passed":
        return fail(f"machine safety gate not fully passed: {passed_count}/{case_count}, status={run.get('status')}")
    safety_keys = (
        "forbidden_claim_count",
        "unsupported_number_count",
        "user_facing_technical_token_count",
        "claim_evidence_violation_count",
        "unsupported_impact_claim_count",
        "cover_letter_presentation_violation_count",
        "language_consistency_violation_count",
        "scenario_provenance_violation_count",
        "match_consistency_violation_count",
    )
    nonzero = {key: int(summary.get(key) or 0) for key in safety_keys if int(summary.get(key) or 0)}
    if nonzero:
        return fail(f"non-zero safety counters: {nonzero}")
    print("AI-BENCH Alice final machine gate passed")
    print(
        f"{EXPECTED_PROVIDER}: passed={passed_count}/{case_count} "
        f"quality={summary.get('mean_quality_score')} grounding={summary.get('mean_grounding_score')} "
        f"scenario_repairs={summary.get('scenario_provenance_repair_count', 0)} "
        f"retries={summary.get('retry_count')} p95_ms={summary.get('p95_latency_ms')} "
        f"cost_usd={summary.get('estimated_cost_usd')}"
    )
    print("Named human writing-quality review is still required before AI-BENCH-001 closure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
