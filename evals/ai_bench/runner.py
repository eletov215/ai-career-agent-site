from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Iterable

from .config import load_config, resolve_repo_path
from .dataset import load_dataset
from .errors import BenchmarkError
from .providers import create_provider
from .reporting import write_markdown_report
from .scoring import score_case
from .util import canonical_json, redact_secrets, sha256_text, utc_now_iso


class BenchmarkRunner:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path.resolve()
        self.config, self.repo_root, self.provider_specs = load_config(self.config_path)
        manifest_path = resolve_repo_path(self.repo_root, self.config.get("fixtures_manifest", ""), "fixtures_manifest")
        self.manifest, self.cases, self.dataset_fingerprint = load_dataset(manifest_path)
        self.thresholds = dict(self.config.get("thresholds") or {})
        self.timeout_seconds = float(self.config.get("timeout_seconds", 60))

    def validate(self, *, check_credentials: bool = False) -> dict[str, Any]:
        enabled = [spec for spec in self.provider_specs if spec.enabled]
        if not enabled:
            raise BenchmarkError("At least one provider must be enabled")
        adapters = []
        for spec in enabled:
            adapter = create_provider(spec, self.repo_root, self.timeout_seconds)
            if check_credentials and spec.adapter == "openai_compatible":
                import os

                key_env = str(spec.options.get("api_key_env", ""))
                if not key_env or not os.environ.get(key_env):
                    raise BenchmarkError(f"{spec.provider_id}: credential environment variable is not set")
            adapters.append({"id": spec.provider_id, "adapter": spec.adapter})
        return {
            "status": "valid",
            "dataset_id": self.manifest.get("dataset_id"),
            "dataset_version": self.manifest.get("version"),
            "dataset_fingerprint": self.dataset_fingerprint,
            "case_count": len(self.cases),
            "providers": adapters,
        }

    def run(
        self,
        output_dir: Path,
        *,
        provider_ids: set[str] | None = None,
        case_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        response_dir = output_dir / "responses"
        response_dir.mkdir(parents=True, exist_ok=True)

        selected_specs = [
            spec
            for spec in self.provider_specs
            if spec.enabled and (provider_ids is None or spec.provider_id in provider_ids)
        ]
        selected_cases = [case for case in self.cases if case_ids is None or case.case_id in case_ids]
        if not selected_specs:
            raise BenchmarkError("No enabled providers match the selection")
        if not selected_cases:
            raise BenchmarkError("No benchmark cases match the selection")

        started_at = utc_now_iso()
        run_seed = {
            "dataset_fingerprint": self.dataset_fingerprint,
            "providers": [spec.provider_id for spec in selected_specs],
            "cases": [case.case_id for case in selected_cases],
            "started_at": started_at,
        }
        run_id = f"ai-bench-{started_at.replace(':', '').replace('-', '')}-{sha256_text(canonical_json(run_seed))[:8]}"
        results: list[dict[str, Any]] = []
        execution_modes: set[str] = set()

        for spec in selected_specs:
            provider = create_provider(spec, self.repo_root, self.timeout_seconds)
            pricing = dict(spec.options.get("pricing_usd_per_million") or {})
            for case in selected_cases:
                schema = json.loads(case.schema_path.read_text(encoding="utf-8"))
                result: dict[str, Any] = {
                    "provider_id": spec.provider_id,
                    "adapter": spec.adapter,
                    "case_id": case.case_id,
                    "task": case.task,
                    "language": case.language,
                    "started_at": utc_now_iso(),
                }
                try:
                    response = provider.invoke(case, schema)
                    score = score_case(case, response.content, self.thresholds)
                    cost = _estimate_cost(response.input_tokens, response.output_tokens, pricing)
                    result.update(
                        {
                            "finished_at": utc_now_iso(),
                            "passed": bool(score["passed"]),
                            "latency_ms": round(response.latency_ms, 3),
                            "usage": {
                                "input_tokens": response.input_tokens,
                                "output_tokens": response.output_tokens,
                                "estimated_cost_usd": cost,
                            },
                            "metadata": redact_secrets(response.metadata),
                            "score": score,
                            "error": None,
                            "response_sha256": sha256_text(canonical_json(response.content)),
                        }
                    )
                    execution_modes.add(str(response.metadata.get("mode", "live")))
                    response_path = response_dir / spec.provider_id / f"{case.case_id}.json"
                    response_path.parent.mkdir(parents=True, exist_ok=True)
                    response_path.write_text(
                        json.dumps(redact_secrets(response.content), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                except Exception as exc:  # execution errors are evidence, not a runner crash
                    result.update(
                        {
                            "finished_at": utc_now_iso(),
                            "passed": False,
                            "latency_ms": None,
                            "usage": {"input_tokens": None, "output_tokens": None, "estimated_cost_usd": None},
                            "metadata": {},
                            "score": None,
                            "error": {
                                "category": type(exc).__name__,
                                "message": str(redact_secrets(str(exc)))[:800],
                            },
                            "response_sha256": None,
                        }
                    )
                results.append(result)

        provider_records = []
        for spec in selected_specs:
            provider_results = [result for result in results if result["provider_id"] == spec.provider_id]
            provider_records.append(
                {
                    "id": spec.provider_id,
                    "adapter": spec.adapter,
                    "summary": _summarize_provider(provider_results),
                }
            )

        error_count = sum(1 for result in results if result.get("error"))
        passed_count = sum(1 for result in results if result.get("passed"))
        max_error_rate = float(self.thresholds.get("max_error_rate", 0.0))
        overall_error_rate = error_count / len(results)
        all_cases_passed = passed_count == len(results)
        status = "passed" if all_cases_passed and overall_error_rate <= max_error_rate else "failed"
        finished_at = utc_now_iso()
        fixture_only = execution_modes == {"deterministic_fixture"}
        execution_mode = "deterministic_reference" if fixture_only else "live_or_mixed"
        limitations = [
            "The included dataset is synthetic and intentionally excludes production user PII.",
            "Human writing-quality rubrics remain pending until a named reviewer records scores.",
            "Vacancy numeric match scores are derived deterministically from requirement classifications; models do not author the score field.",
            "Live run v2 uses the grounded-v2 output contract, so its quality scores are not directly comparable to the earlier grounded-v1 run.",
        ]
        if fixture_only:
            limitations.append(
                "This run validates the harness, schemas, scoring, safety gates, and report generation; it is not a comparative result for external AI vendors."
            )
        decision_status = (
            "No external model/provider decision is allowed from a deterministic reference run. Run the approved live candidates and complete manual review before AI-PROVIDER-001."
            if fixture_only
            else "Provider selection remains pending until the live evidence is reviewed and the named manual writing rubric is completed; rejected candidates may fail machine gates, but any selected production candidate must satisfy the accepted safety/grounding criteria."
        )

        run = {
            "schema_version": "1.1",
            "run_id": run_id,
            "benchmark_version": self.config.get("benchmark_version"),
            "started_at": started_at,
            "finished_at": finished_at,
            "execution_mode": execution_mode,
            "status": status,
            "config_fingerprint": sha256_text(canonical_json(redact_secrets(self.config))),
            "dataset": {
                "id": self.manifest.get("dataset_id"),
                "version": self.manifest.get("version"),
                "synthetic": True,
                "fingerprint": self.dataset_fingerprint,
                "case_count": len(selected_cases),
            },
            "quality_gate": {
                "thresholds": self.thresholds,
                "result_count": len(results),
                "passed_count": passed_count,
                "error_count": error_count,
                "error_rate": round(overall_error_rate, 6),
            },
            "providers": provider_records,
            "results": results,
            "limitations": limitations,
            "decision_status": decision_status,
        }
        run["manual_review_template"] = "manual_review_template.json"
        run_path = output_dir / "run.json"
        run_path.write_text(
            json.dumps(redact_secrets(run), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manual_review = {
            "schema_version": "1.1",
            "run_id": run_id,
            "status": "pending",
            "score_scale": {
                "min": 1,
                "max": 5,
                "anchors": {
                    "1": "unacceptable",
                    "2": "major_revision_needed",
                    "3": "usable_with_revision",
                    "4": "good",
                    "5": "excellent",
                },
            },
            "instructions": "A named human reviewer scores only writing quality, clarity and usefulness on the 1-5 scale. Machine safety/grounding gates remain authoritative and cannot be overridden by manual scores.",
            "entries": [
                {
                    "provider_id": result["provider_id"],
                    "case_id": result["case_id"],
                    "task": result["task"],
                    "language": result["language"],
                    "reviewer": None,
                    "criteria": [
                        {"criterion": item, "score": None, "notes": None}
                        for item in next(case.manual_rubric for case in selected_cases if case.case_id == result["case_id"])
                    ],
                    "overall_notes": None,
                }
                for result in results
                if not result.get("error")
            ],
        }
        (output_dir / "manual_review_template.json").write_text(
            json.dumps(manual_review, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_markdown_report(run, output_dir / "report.md")
        return run


def _estimate_cost(input_tokens: int | None, output_tokens: int | None, pricing: dict[str, Any]) -> float | None:
    if input_tokens is None and output_tokens is None:
        return None
    try:
        input_rate = float(pricing.get("input", 0.0))
        output_rate = float(pricing.get("output", 0.0))
    except (TypeError, ValueError):
        return None
    return round(((input_tokens or 0) * input_rate + (output_tokens or 0) * output_rate) / 1_000_000.0, 9)


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _summarize_provider(results: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [result["score"] for result in results if result.get("score")]
    latencies = [float(result["latency_ms"]) for result in results if result.get("latency_ms") is not None]
    costs = [result["usage"]["estimated_cost_usd"] for result in results if result.get("usage", {}).get("estimated_cost_usd") is not None]
    errors = sum(1 for result in results if result.get("error"))
    deterministic_match_scores = [
        score["match_evaluation"]["deterministic_match_score"]
        for score in scores
        if score.get("match_evaluation", {}).get("deterministic_match_score") is not None
    ]
    return {
        "case_count": len(results),
        "passed_count": sum(1 for result in results if result.get("passed")),
        "error_count": errors,
        "error_rate": round(errors / len(results), 6) if results else 0.0,
        "mean_quality_score": round(statistics.fmean(score["quality_score"] for score in scores), 6) if scores else None,
        "schema_pass_rate": round(statistics.fmean(score["schema_compliance"] for score in scores), 6) if scores else None,
        "mean_grounding_score": round(statistics.fmean(score["grounding_score"] for score in scores), 6) if scores else None,
        "mean_user_facing_cleanliness": round(statistics.fmean(score["user_facing_cleanliness"] for score in scores), 6) if scores else None,
        "mean_match_consistency_score": round(statistics.fmean(score["match_consistency_score"] for score in scores), 6) if scores else None,
        "forbidden_claim_count": sum(score["forbidden_claim_count"] for score in scores),
        "unsupported_number_count": sum(score["unsupported_number_count"] for score in scores),
        "user_facing_technical_token_count": sum(score["user_facing_technical_token_count"] for score in scores),
        "claim_evidence_violation_count": sum(score["claim_evidence_violation_count"] for score in scores),
        "unsupported_impact_claim_count": sum(score["unsupported_impact_claim_count"] for score in scores),
        "match_consistency_violation_count": sum(len(score.get("match_evaluation", {}).get("violations", [])) for score in scores),
        "mean_deterministic_match_score": round(statistics.fmean(deterministic_match_scores), 3) if deterministic_match_scores else None,
        "p50_latency_ms": round(_percentile(latencies, 0.50), 3) if latencies else None,
        "p95_latency_ms": round(_percentile(latencies, 0.95), 3) if latencies else None,
        "estimated_cost_usd": round(sum(float(cost) for cost in costs), 9) if costs else None,
    }
