"""Dependency-free assertions do not substitute for route/runtime QA."""
from pathlib import Path
import shutil

from scripts.check_ai005_site_qa_package import PROTECTED, RUNTIME, validate

ROOT=Path(__file__).resolve().parents[1]


def test_site_qa_package_boundary():
    assert validate(ROOT)==[]


def test_site_qa_guard_rejects_changed_legal_source(tmp_path):
    paths=set(PROTECTED)|RUNTIME|{'routes/admin_sources.py', '.github/workflows/ai005-site-qa.yml',
                                'docs/evidence/ai-005-site-qa/change_boundary.json'}
    for rel in paths:
        dest=tmp_path/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,dest)
    assert validate(tmp_path)==[]
    p=tmp_path/'domain/ai.py';p.write_text(p.read_text().replace('REAL_DATA_SUPPORTED = False','REAL_DATA_SUPPORTED = True'))
    assert any('Protected predecessor changed: domain/ai.py' in e for e in validate(tmp_path))
