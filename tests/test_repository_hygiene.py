from __future__ import annotations

from pathlib import Path

from scripts.check_repository_hygiene import find_violations


def test_visible_ai_bench_artifact_policy_is_allowed(tmp_path: Path) -> None:
    policy = tmp_path / "evals" / "artifacts" / "README.md"
    policy.parent.mkdir(parents=True)
    policy.write_text("runtime output is not committed", encoding="utf-8")

    assert find_violations(tmp_path) == []


def test_generated_ai_bench_artifact_is_rejected(tmp_path: Path) -> None:
    generated = tmp_path / "evals" / "artifacts" / "run.json"
    generated.parent.mkdir(parents=True)
    generated.write_text("{}", encoding="utf-8")

    assert find_violations(tmp_path) == ["evals/artifacts/run.json"]
