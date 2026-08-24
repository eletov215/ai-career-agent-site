from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import redact_secrets


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown_report(run: dict[str, Any]) -> str:
    safe = redact_secrets(run)
    lines: list[str] = [
        "# AI-BENCH-001 benchmark report",
        "",
        f"- Run ID: `{safe['run_id']}`",
        f"- Started: `{safe['started_at']}`",
        f"- Finished: `{safe['finished_at']}`",
        f"- Dataset: `{safe['dataset']['id']}` v{safe['dataset']['version']}",
        f"- Dataset fingerprint: `{safe['dataset']['fingerprint']}`",
        f"- Execution mode: `{safe['execution_mode']}`",
        f"- Quality gate: **{safe['status'].upper()}**",
        "",
        "## Provider summary",
        "",
        "| Provider | Adapter | Cases | Passed | Error rate | Quality | Schema | Grounding | p50 latency, ms | p95 latency, ms | Estimated cost, USD |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for provider in safe["providers"]:
        summary = provider["summary"]
        lines.append(
            "| {id} | {adapter} | {cases} | {passed} | {error_rate} | {quality} | {schema} | {grounding} | {p50} | {p95} | {cost} |".format(
                id=provider["id"],
                adapter=provider["adapter"],
                cases=summary["case_count"],
                passed=summary["passed_count"],
                error_rate=_fmt(summary["error_rate"]),
                quality=_fmt(summary["mean_quality_score"]),
                schema=_fmt(summary["schema_pass_rate"]),
                grounding=_fmt(summary["mean_grounding_score"]),
                p50=_fmt(summary["p50_latency_ms"], 2),
                p95=_fmt(summary["p95_latency_ms"], 2),
                cost=_fmt(summary["estimated_cost_usd"], 6),
            )
        )

    lines.extend([
        "",
        "## Case results",
        "",
        "| Provider | Case | Task | Language | Result | Quality | Grounding | Forbidden claims | Unsupported numbers | Latency, ms |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|",
    ])
    for result in safe["results"]:
        score = result.get("score") or {}
        lines.append(
            "| {provider} | {case} | {task} | {language} | {status} | {quality} | {grounding} | {forbidden} | {numbers} | {latency} |".format(
                provider=result["provider_id"],
                case=result["case_id"],
                task=result["task"],
                language=result["language"],
                status="PASS" if result.get("passed") else "FAIL",
                quality=_fmt(score.get("quality_score")),
                grounding=_fmt(score.get("grounding_score")),
                forbidden=_fmt(score.get("forbidden_claim_count")),
                numbers=_fmt(score.get("unsupported_number_count")),
                latency=_fmt(result.get("latency_ms"), 2),
            )
        )

    lines.extend([
        "",
        "## Quality-gate interpretation",
        "",
        "- Schema compliance is machine-checked against the versioned JSON schemas in `evals/schemas/`.",
        "- Grounding combines valid evidence references, required evidence recall, and fixture-specific grounding terms.",
        "- Forbidden claims and unsupported numeric claims are hard safety gates in the CI configuration.",
        "- Human writing-quality rubrics are recorded as pending; the runner never fabricates manual-review scores.",
        "",
        "## Limitations",
        "",
    ])
    for limitation in safe.get("limitations", []):
        lines.append(f"- {limitation}")
    lines.extend([
        "",
        "## Decision status",
        "",
        safe.get("decision_status", "No provider decision was recorded."),
        "",
    ])
    return "\n".join(lines)


def write_markdown_report(run: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(run), encoding="utf-8", newline="\n")
