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
        f"- Benchmark contract: `{safe.get('benchmark_version')}`",
        f"- Execution mode: `{safe['execution_mode']}`",
        f"- Quality gate: **{safe['status'].upper()}**",
        "",
        "## Provider summary",
        "",
        "| Provider | Cases | Passed | Errors | Retries | Quality | Grounding | Language | Scenario provenance | Scenario repairs | Kind repairs | Marker cleanup | Clean text | Match consistency | Safety violations | p50 ms | p95 ms | Est. cost USD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for provider in safe["providers"]:
        summary = provider["summary"]
        safety_violations = (
            int(summary.get("forbidden_claim_count") or 0)
            + int(summary.get("unsupported_number_count") or 0)
            + int(summary.get("user_facing_technical_token_count") or 0)
            + int(summary.get("claim_evidence_violation_count") or 0)
            + int(summary.get("unsupported_impact_claim_count") or 0)
            + int(summary.get("cover_letter_presentation_violation_count") or 0)
            + int(summary.get("language_consistency_violation_count") or 0)
            + int(summary.get("scenario_provenance_violation_count") or 0)
            + int(summary.get("match_consistency_violation_count") or 0)
        )
        lines.append(
            "| {id} | {cases} | {passed} | {errors} | {retries} | {quality} | {grounding} | {language} | {scenario} | {scenario_repairs} | {kind_repairs} | {cleanup} | {clean} | {match} | {safety} | {p50} | {p95} | {cost} |".format(
                id=provider["id"],
                cases=summary["case_count"],
                passed=summary["passed_count"],
                errors=summary["error_count"],
                retries=summary.get("retry_count", 0),
                quality=_fmt(summary["mean_quality_score"]),
                grounding=_fmt(summary["mean_grounding_score"]),
                language=_fmt(1.0 if not summary.get("language_consistency_violation_count") else 0.0),
                scenario=_fmt(1.0 if not summary.get("scenario_provenance_violation_count") else 0.0),
                scenario_repairs=summary.get("scenario_provenance_repair_count", 0),
                kind_repairs=summary.get("cover_letter_kind_repair_count", 0),
                cleanup=summary.get("user_facing_marker_cleanup_count", 0),
                clean=_fmt(summary.get("mean_user_facing_cleanliness")),
                match=_fmt(summary.get("mean_match_consistency_score")),
                safety=safety_violations,
                p50=_fmt(summary["p50_latency_ms"], 2),
                p95=_fmt(summary["p95_latency_ms"], 2),
                cost=_fmt(summary["estimated_cost_usd"], 6),
            )
        )

    lines.extend([
        "",
        "## Case results",
        "",
        "| Provider | Case | Result | Retries | Quality | Grounding | Language | Scenario | Scenario repairs | Kind repairs | Marker cleanup | Clean text | Invalid evidence | Impact | Match violations | Derived match | Latency ms |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for result in safe["results"]:
        score = result.get("score") or {}
        match = score.get("match_evaluation") or {}
        lines.append(
            "| {provider} | {case} | {status} | {retries} | {quality} | {grounding} | {language} | {scenario} | {scenario_repairs} | {kind_repairs} | {cleanup} | {clean} | {invalid} | {impact} | {match_v} | {derived} | {latency} |".format(
                provider=result["provider_id"],
                case=result["case_id"],
                status="PASS" if result.get("passed") else "FAIL",
                retries=int((result.get("metadata") or {}).get("provider_diagnostics", {}).get("retry_count") or 0),
                quality=_fmt(score.get("quality_score")),
                grounding=_fmt(score.get("grounding_score")),
                language=_fmt(score.get("language_consistency_score")),
                scenario=_fmt(score.get("scenario_provenance_score")),
                scenario_repairs=int((result.get("normalization") or {}).get("scenario_provenance_repair_count") or 0),
                kind_repairs=int((result.get("normalization") or {}).get("cover_letter_kind_repair_count") or 0),
                cleanup=int((result.get("normalization") or {}).get("user_facing_marker_cleanup_count") or 0),
                clean=_fmt(score.get("user_facing_cleanliness")),
                invalid=len(score.get("invalid_evidence_ids") or []),
                impact=score.get("unsupported_impact_claim_count", 0),
                match_v=len(match.get("violations") or []),
                derived=_fmt(match.get("deterministic_match_score"), 0),
                latency=_fmt(result.get("latency_ms"), 2),
            )
        )

    lines.extend([
        "",
        "## Grounded-v2.6.1 contract interpretation",
        "",
        "- Evidence identifiers must be exact raw IDs. Simple decorated markers such as `(s1)`/`[s1]` are removed by deterministic display normalization; serialized metadata labels remain hard failures.",
        "- Resume `facts_not_verified` and cover-letter `caveats` are structured machine/audit objects with their own evidence references; cover-letter caveats are omitted from the presentation copy.",
        "- Cover-letter candidate-fit paragraphs must cite candidate facts; causal/outcome language is allowed only when a cited candidate fact explicitly contains the corresponding impact. Grounded-v2.6.1 additionally instructs English generation to use atomic first-person restatements rather than inferred purpose/benefit clauses.",
        "- Vacancy requirements are classified exactly once by requirement ID. Duplicate, missing, contradictory, or weakly evidenced classifications are hard failures.",
        "- Vacancy numeric match scores are derived deterministically from weighted requirement classifications; the LLM no longer authors a percentage.",
        "- Interview factual/scenario numbers are accepted only when grounded in source facts. A narrowly scoped answer-cardinality instruction such as 'give 2 examples' is treated as formatting rather than a factual claim.",
        "- When an interview question uses an exact scenario number that maps to exactly one scenario fact, the machine layer may deterministically append that scenario ID to the structured `evidence_ids`. Repairs are audited and unresolved or ambiguous provenance remains a hard failure.",
        "- Percent formatting is Unicode-normalized, so 20%, 20 % and 20\u202f% represent the same grounded number.",
        "- RU/EN user-facing language consistency is a separate hard gate.",
        "- Cover letters distinguish candidate_fit from vacancy-grounded motivation paragraphs; unverified candidate gaps must remain internal caveats and may not be disclosed in visible paragraphs. Motivation must not invent prior familiarity with the employer/team when source evidence does not establish it.",
        "- Unicode hyphen/dash variants are normalized for lexical grounding only; evidence semantics are unchanged.",
        "- Vacancy-only candidate_fit paragraphs are reclassified to motivation only for explicit future-intent/motivation wording, with an audit record; gap-bearing candidate evidence is never repaired into visible motivation.",
        "- Live provider diagnostics record only safe envelope shape/status metadata; raw provider bodies and refusal text are never persisted.",
        "- Human writing-quality rubrics remain pending; the runner never fabricates manual-review scores.",
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
