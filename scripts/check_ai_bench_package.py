#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_VISIBLE = [
    "evals/README.md",
    "evals/VERSION",
    "evals/config/ci.json",
    "evals/config/benchmark.example.json",
    "evals/config/yandex-live.json",
    "evals/config/yandex-alice-final.json",
    "evals/artifacts/README.md",
    "evals/regressions/live-run-1.json",
    "evals/regressions/live-run-2.json",
    "evals/regressions/live-run-3.json",
    "evals/regressions/live-run-4.json",
    "evals/regressions/alice-final-run-1.json",
    "evals/regressions/alice-final-run-2.json",
    "evals/fixtures/manifest.json",
    "evals/schemas/resume_analysis.schema.json",
    "evals/schemas/vacancy_match.schema.json",
    "evals/schemas/cover_letter.schema.json",
    "evals/schemas/interview_questions.schema.json",
    "evals/ai_bench/cli.py",
    "evals/ai_bench/runner.py",
    "evals/ai_bench/scoring.py",
]
REQUIRED_REPOSITORY = [
    ".github/workflows/ci.yml",
    "scripts/check_ai_bench_live_result.py",
    "scripts/check_ai_bench_alice_final_result.py",
]
REQUIRED = [*REQUIRED_VISIBLE, *REQUIRED_REPOSITORY]
EXPRESSION_RE = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
CONTEXT_REF_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_-]*)\.")
JOB_ENV_ALLOWED_CONTEXTS = {"github", "needs", "strategy", "matrix", "vars", "secrets", "inputs"}

SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+(?!\[REDACTED\])\S+"),
    re.compile(r"(?i)(?:api[_-]?key|secret|token)\s*[:=]\s*(?!\[REDACTED\]|\"?AI_BENCH_)[A-Za-z0-9_-]{16,}"),
]


def fail(message: str) -> None:
    raise SystemExit(f"AI-BENCH-001 gate failed: {message}")


def validate_job_level_env_contexts(workflow_path: Path) -> None:
    """Reject contexts unavailable in jobs.<job_id>.env using stdlib only.

    The dedicated AI-BENCH job intentionally installs no dependencies before
    running this checker. GitHub job-level ``env`` is indented four spaces
    under a two-space job key, while step/container env blocks are deeper.
    """
    lines = workflow_path.read_text(encoding="utf-8").splitlines()
    in_jobs = False
    current_job: str | None = None
    in_job_env = False
    violations: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))

        if indent == 0 and stripped == "jobs:":
            in_jobs = True
            current_job = None
            in_job_env = False
            continue
        if in_jobs and indent == 0:
            in_jobs = False
            current_job = None
            in_job_env = False

        if not in_jobs:
            continue

        job_match = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if job_match:
            current_job = job_match.group(1)
            in_job_env = False
            continue

        if current_job and indent == 4 and stripped == "env:":
            in_job_env = True
            continue

        if in_job_env and indent <= 4:
            in_job_env = False

        if not in_job_env or indent < 6:
            continue

        env_match = re.match(r"^\s{6}([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not env_match:
            continue
        env_name, value = env_match.groups()
        for expression in EXPRESSION_RE.findall(value):
            roots = set(CONTEXT_REF_RE.findall(expression))
            disallowed = sorted(roots - JOB_ENV_ALLOWED_CONTEXTS)
            if disallowed:
                violations.append(
                    f"jobs.{current_job}.env.{env_name}: unsupported contexts {disallowed}"
                )

    if violations:
        fail("invalid job-level env context usage: " + "; ".join(violations))


def main() -> int:
    hidden_required = [
        path
        for path in REQUIRED_VISIBLE
        if any(part.startswith(".") for part in Path(path).parts)
    ]
    if hidden_required:
        fail(
            "visible package files must be safe for browser uploads: "
            f"{hidden_required}"
        )
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        fail(f"missing required files: {missing}")

    version = (ROOT / "evals/VERSION").read_text(encoding="utf-8").strip()
    if version != "1.5.1":
        fail(f"unexpected evals version: {version}")

    workflow_path = ROOT / ".github/workflows/ci.yml"
    validate_job_level_env_contexts(workflow_path)
    workflow = workflow_path.read_text(encoding="utf-8")
    required_workflow_fragments = [
        "workflow_dispatch:",
        "run_ai_bench_live:",
        "type: boolean",
        "default: false",
        "ai-bench-yandex-live:",
        "name: AI-BENCH-001 Live Yandex",
        "github.event_name == 'workflow_dispatch'",
        "inputs.run_ai_bench_live == true",
        "      - tests\n      - ai-bench-001",
        "AI_BENCH_YANDEX_API_KEY: ${{ secrets.AI_BENCH_YANDEX_API_KEY }}",
        "AI_BENCH_YANDEX_FOLDER_ID: ${{ secrets.AI_BENCH_YANDEX_FOLDER_ID }}",
        "uses: actions/upload-artifact@v7",
        "timeout-minutes: 45",
        "group: ai-bench-001-yandex-live",
        "AI_BENCH_OUTPUT_DIR: /tmp/ai-bench-yandex-live",
        "run_ai_bench_alice_final:",
        "ai-bench-yandex-alice-final:",
        "name: AI-BENCH-001 Alice Final",
        "inputs.run_ai_bench_alice_final == true",
        "AI_BENCH_ALICE_FINAL_OUTPUT_DIR: /tmp/ai-bench-yandex-alice-final",
        "--config evals/config/yandex-alice-final.json",
        "scripts/check_ai_bench_alice_final_result.py",
        "grounded-v2.4",
        "scenario_provenance_repair_count",
    ]
    missing_workflow_fragments = [
        fragment for fragment in required_workflow_fragments if fragment not in workflow
    ]
    if missing_workflow_fragments:
        fail(
            "integrated live workflow controls are incomplete: "
            f"{missing_workflow_fragments}"
        )

    alice_final = json.loads((ROOT / "evals/config/yandex-alice-final.json").read_text(encoding="utf-8"))
    alice_providers = alice_final.get("providers") or []
    if [item.get("id") for item in alice_providers] != ["yandex-alice-ai-llm"]:
        fail("Alice final config must enable exactly yandex-alice-ai-llm")
    if float((alice_final.get("thresholds") or {}).get("max_error_rate", 1.0)) != 0.0:
        fail("Alice final config must require max_error_rate=0.0")
    if alice_final.get("verification_scope") != "alice_ai_llm_final_candidate_v2":
        fail("Alice final config must use verification_scope=alice_ai_llm_final_candidate_v2")

    legacy_workflow = ROOT / ".github/workflows/ai-bench-live"
    if legacy_workflow.is_file():
        print(
            "AI-BENCH-001 gate warning: ignoring legacy extensionless workflow file; "
            "the executable manual job is integrated into .github/workflows/ci.yml",
            file=sys.stderr,
        )

    manifest = json.loads((ROOT / "evals/fixtures/manifest.json").read_text(encoding="utf-8"))
    if manifest.get("synthetic") is not True:
        fail("manifest must declare synthetic=true")
    if manifest.get("version") != "1.3.3" or manifest.get("contract") != "grounded-v2.4":
        fail("manifest must declare version=1.3.3 and contract=grounded-v2.4")
    cases = manifest.get("cases") or []
    if len(cases) < 8:
        fail("golden dataset must contain at least eight bilingual/task-diverse cases")
    languages: set[str] = set()
    tasks: set[str] = set()
    for relative in cases:
        case_path = ROOT / "evals/fixtures" / relative
        if not case_path.is_file():
            fail(f"case is missing: {relative}")
        case = json.loads(case_path.read_text(encoding="utf-8"))
        if case.get("synthetic") is not True:
            fail(f"case is not synthetic: {case.get('case_id')}")
        facts = case.get("source_facts") or []
        if not facts or any(fact.get("kind") not in {"candidate", "vacancy", "scenario"} for fact in facts):
            fail(f"case source_facts must carry candidate/vacancy/scenario kind: {case.get('case_id')}")
        if case.get("task") == "vacancy_match" and not case.get("match_requirements"):
            fail(f"vacancy match case lacks deterministic match requirements: {case.get('case_id')}")
        languages.add(str(case.get("language")))
        tasks.add(str(case.get("task")))
        expected = ROOT / "evals/expected/reference" / f"{case['case_id']}.json"
        if not expected.is_file():
            fail(f"reference output is missing: {case['case_id']}")
    if languages != {"ru", "en"}:
        fail(f"expected ru/en coverage, got {sorted(languages)}")
    required_tasks = {"resume_analysis", "vacancy_match", "cover_letter", "interview_questions"}
    if not required_tasks.issubset(tasks):
        fail(f"task coverage is incomplete: {sorted(tasks)}")

    regression3 = json.loads((ROOT / "evals/regressions/live-run-3.json").read_text(encoding="utf-8"))
    impact_samples = (regression3.get("patterns") or {}).get("unsupported_impact_claims") or []
    cleanup_samples = (regression3.get("patterns") or {}).get("simple_marker_cleanup") or []
    if len(impact_samples) < 2 or len(cleanup_samples) < 2:
        fail("live-run-3 impact/marker regressions are incomplete")

    regression4 = json.loads((ROOT / "evals/regressions/live-run-4.json").read_text(encoding="utf-8"))
    patterns4 = regression4.get("patterns") or {}
    if len(patterns4.get("alice_unsupported_impact_claims") or []) < 3:
        fail("live-run-4 Alice impact regressions are incomplete")
    if not (patterns4.get("alice_missing_scenario_provenance") or {}).get("required_evidence_id"):
        fail("live-run-4 Alice scenario provenance regression is incomplete")
    if len(patterns4.get("safe_literal_rewrites") or []) < 2:
        fail("live-run-4 safe literal rewrite regressions are incomplete")

    alice_final_regression = json.loads((ROOT / "evals/regressions/alice-final-run-1.json").read_text(encoding="utf-8"))
    alice_final_regression_2 = json.loads((ROOT / "evals/regressions/alice-final-run-2.json").read_text(encoding="utf-8"))
    if alice_final_regression_2.get("source_run_id") != "ai-bench-20260827T112440Z-243eaaeb":
        fail("Alice Final run #2 regression provenance is missing")
    alice_patterns = alice_final_regression.get("patterns") or {}
    if len(alice_patterns.get("repairable_scenario_provenance") or []) < 3:
        fail("Alice final run-1 scenario-provenance regressions are incomplete")
    if not (alice_patterns.get("safe_response_cardinality") or {}).get("text"):
        fail("Alice final run-1 response-cardinality regression is missing")
    if not (alice_patterns.get("unsafe_unsourced_duration") or {}).get("number"):
        fail("Alice final run-1 unsupported-duration regression is missing")

    with tempfile.TemporaryDirectory(prefix="ai-bench-gate-") as temporary:
        out = Path(temporary)
        commands = [
            [sys.executable, "-m", "evals.ai_bench", "validate", "--config", "evals/config/ci.json"],
            [
                sys.executable,
                "-m",
                "evals.ai_bench",
                "run",
                "--config",
                "evals/config/ci.json",
                "--output-dir",
                str(out),
                "--fail-on-gate",
            ],
        ]
        clean_env = os.environ.copy()
        clean_env.pop("AI_BENCH_CANDIDATE_API_KEY", None)
        for command in commands:
            completed = subprocess.run(command, cwd=ROOT, env=clean_env, text=True, capture_output=True, check=False)
            if completed.returncode != 0:
                fail(f"command failed ({completed.returncode}): {' '.join(command)}\n{completed.stdout}\n{completed.stderr}")
        run_path = out / "run.json"
        report_path = out / "report.md"
        manual_review_path = out / "manual_review_template.json"
        if not run_path.is_file() or not report_path.is_file() or not manual_review_path.is_file():
            fail("runner did not create run.json, report.md and manual_review_template.json")
        run = json.loads(run_path.read_text(encoding="utf-8"))
        if run.get("status") != "passed":
            fail("deterministic reference run did not pass")
        if run.get("execution_mode") != "deterministic_reference":
            fail("reference run must be labeled deterministic_reference")
        if run.get("schema_version") != "1.4" or run.get("benchmark_version") != "1.4":
            fail("reference run must use grounded-v2.4 benchmark/run schema version 1.4")
        if run.get("quality_gate", {}).get("passed_count") != len(cases):
            fail("not all reference cases passed")
        machine_dir = out / "machine" / "reference"
        if not machine_dir.is_dir() or len(list(machine_dir.glob("*.json"))) != len(cases):
            fail("deterministic run must persist machine-normalized evidence for every case")
        provider_summary = ((run.get("providers") or [{}])[0].get("summary") or {})
        if int(provider_summary.get("scenario_provenance_repair_count") or 0) != 0:
            fail("reference outputs must not require scenario provenance repair")
        vacancy_schema = json.loads((ROOT / "evals/schemas/vacancy_match.schema.json").read_text(encoding="utf-8"))
        if "match_score" in (vacancy_schema.get("properties") or {}):
            fail("vacancy model schema must not ask the LLM to author match_score")
        cover_schema = json.loads((ROOT / "evals/schemas/cover_letter.schema.json").read_text(encoding="utf-8"))
        paragraph_kinds = cover_schema.get("properties", {}).get("paragraphs", {}).get("items", {}).get("properties", {}).get("kind", {}).get("enum", [])
        if "motivation" not in paragraph_kinds:
            fail("cover-letter schema must support vacancy-grounded motivation paragraphs")
        required_thresholds = {"max_language_consistency_violations", "max_scenario_provenance_violations"}
        if not required_thresholds.issubset(set((run.get("quality_gate", {}).get("thresholds") or {}).keys())):
            fail("grounded-v2.4 language/scenario thresholds are missing")
        for schema_name in (
            "resume_analysis.schema.json",
            "vacancy_match.schema.json",
            "cover_letter.schema.json",
            "interview_questions.schema.json",
        ):
            schema_text = (ROOT / "evals/schemas" / schema_name).read_text(encoding="utf-8")
            if "^[a-z][0-9]+$" not in schema_text:
                fail(f"schema does not enforce raw evidence ID format: {schema_name}")
        combined = run_path.read_text(encoding="utf-8") + report_path.read_text(encoding="utf-8") + manual_review_path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            if pattern.search(combined):
                fail(f"possible secret leaked into evidence: {pattern.pattern}")

    # This package must not create a new migration or production AI route.
    migration_paths = sorted((ROOT / "migrations/versions").glob("*.py")) if (ROOT / "migrations/versions").exists() else []
    if migration_paths and not any("20260819_0014" in path.name for path in migration_paths):
        fail("expected production schema baseline 20260819_0014 is missing")
    if (ROOT / "services/ai").exists() or (ROOT / "routes/ai.py").exists():
        fail("AI-BENCH-001 must remain isolated from production AI integration")

    print("AI-BENCH-001 package gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
