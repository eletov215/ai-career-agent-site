from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .errors import BenchmarkError
from .reporting import write_markdown_report
from .runner import BenchmarkRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m evals.ai_bench", description="AI Career Agent benchmark harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate configuration, schemas, fixtures, and adapters")
    validate.add_argument("--config", required=True, type=Path)
    validate.add_argument("--check-credentials", action="store_true")

    run = subparsers.add_parser("run", help="Execute benchmark cases")
    run.add_argument("--config", required=True, type=Path)
    run.add_argument("--output-dir", required=True, type=Path)
    run.add_argument("--provider", action="append", default=[])
    run.add_argument("--case", action="append", default=[])
    run.add_argument("--fail-on-gate", action="store_true")

    report = subparsers.add_parser("report", help="Regenerate a Markdown report from run.json")
    report.add_argument("--input", required=True, type=Path)
    report.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            result = BenchmarkRunner(args.config).validate(check_credentials=args.check_credentials)
            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        if args.command == "run":
            run = BenchmarkRunner(args.config).run(
                args.output_dir,
                provider_ids=set(args.provider) or None,
                case_ids=set(args.case) or None,
            )
            print(json.dumps({"run_id": run["run_id"], "status": run["status"], "output_dir": str(args.output_dir)}, ensure_ascii=False))
            return 3 if args.fail_on_gate and run["status"] != "passed" else 0
        if args.command == "report":
            run = json.loads(args.input.read_text(encoding="utf-8"))
            write_markdown_report(run, args.output)
            return 0
    except BenchmarkError as exc:
        print(f"AI-BENCH error: {exc}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(f"AI-BENCH I/O error: {exc}", file=sys.stderr)
        return 2
    return 2
