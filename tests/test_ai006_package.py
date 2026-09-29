import json
import shutil
from pathlib import Path

from scripts.check_ai006_package import validate

ROOT = Path(__file__).resolve().parents[1]


def _copy(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    return root


def test_package_boundary_passes():
    assert validate(ROOT) == []


def test_both_live_jobs_require_ai006(tmp_path):
    for job in ("ai-bench-yandex-live", "ai-bench-yandex-alice-final"):
        root = _copy(tmp_path / job)
        workflow = root / ".github/workflows/ci.yml"
        text = workflow.read_text()
        start = text.index(f"  {job}:")
        marker = text.index("      - ai-006", start)
        workflow.write_text(text[:marker] + text[marker + len("      - ai-006\n"):])
        assert validate(root)


def test_tampered_fixture_fails_closed(tmp_path):
    root = _copy(tmp_path)
    path = root / "quality/ai006/golden_suite_v1.json"
    path.write_text(path.read_text() + " ")
    assert validate(root)


def test_tampered_evidence_or_safety_metadata_fails_closed(tmp_path):
    for relative, mutate in (
        ("docs/evidence/ai-006/acceptance.json", lambda value: {**value, "provider_calls": 1}),
        ("quality/ai006/human_review_rubric_v1.json", lambda value: {**value, "human_pass_cannot_override_machine_fail": False}),
    ):
        root = _copy(tmp_path / relative.replace("/", "_"))
        path = root / relative
        value = json.loads(path.read_text())
        path.write_text(json.dumps(mutate(value)))
        assert validate(root)
