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
    "evals/artifacts/README.md",
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
]
REQUIRED = [*REQUIRED_VISIBLE, *REQUIRED_REPOSITORY]
SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+(?!\[REDACTED\])\S+"),
    re.compile(r"(?i)(?:api[_-]?key|secret|token)\s*[:=]\s*(?!\[REDACTED\]|\"?AI_BENCH_)[A-Za-z0-9_-]{16,}"),
]


def fail(message: str) -> None:
    raise SystemExit(f"AI-BENCH-001 gate failed: {message}")


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
    if version != "1.1.2":
        fail(f"unexpected evals version: {version}")

    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
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
    ]
    missing_workflow_fragments = [
        fragment for fragment in required_workflow_fragments if fragment not in workflow
    ]
    if missing_workflow_fragments:
        fail(
            "integrated live workflow controls are incomplete: "
            f"{missing_workflow_fragments}"
        )

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
        if not run_path.is_file() or not report_path.is_file():
            fail("runner did not create run.json and report.md")
        run = json.loads(run_path.read_text(encoding="utf-8"))
        if run.get("status") != "passed":
            fail("deterministic reference run did not pass")
        if run.get("execution_mode") != "deterministic_reference":
            fail("reference run must be labeled deterministic_reference")
        if run.get("quality_gate", {}).get("passed_count") != len(cases):
            fail("not all reference cases passed")
        combined = run_path.read_text(encoding="utf-8") + report_path.read_text(encoding="utf-8")
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
