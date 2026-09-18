#!/usr/bin/env python3
"""Validate the AI-001 candidate without a database, secret or network request."""
from __future__ import annotations
import ast
import hashlib
import json
import importlib.util
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from domain.ai import REAL_DATA_SUPPORTED, CONTRACT

def _load_source_module(name: str, path: Path):
    """Load an AI-001 source module without importing the parent services package.

    The standalone AI-BENCH package gate intentionally runs before third-party
    dependencies are installed. Importing ``services.ai.*`` normally executes
    ``services/__init__.py``, which pulls the OAuth repository layer and
    SQLAlchemy into that isolated gate. Loading these dependency-free checker
    modules directly preserves the original stdlib-only gate boundary.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load checker module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_policy = _load_source_module("_ai001_policy_for_package_check", ROOT / "services/ai/policy.py")
DEFAULT_POLICY = _policy.DEFAULT_POLICY
validate_policy = _policy.validate_policy
_registry = _load_source_module("_ai001_registry_for_package_check", ROOT / "services/ai/registry.py")
ContractRegistry = _registry.ContractRegistry

# This is an explicit successor scope, NOT permission to change accepted evals.
SUPERSEDED_RUNTIME={
    'app.py','config.py','database.py','infra/vps/.env.example',
    'models/__init__.py','operations/backup.py','repositories/privacy.py','requirements.txt',
    'services/privacy.py','services/storage.py','static/theme.css',
    'templates/ai_career.html','templates/resume_builder.html',
}
DOCUMENTS=('AI001_IMPLEMENTATION','AI001_RUNTIME_REFERENCE','AI001_RUNBOOK',
           'AI001_VERIFICATION_STATUS','AI001_SOURCES','LEGAL001_DEFERRED_DECISION')
TABLES={'ai_runtime_policies','ai_usage_events','ai_budget_buckets','ai_request_leases',
        'ai_provider_states','ai_plan_entitlements','ai_user_plans'}

def hash_matches(data:bytes,expected:str)->bool:
    return expected in {hashlib.sha256(data).hexdigest(),hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()}

def load_boundary(root:Path)->dict:
    data=json.loads((root/'docs/evidence/ai-001/change_boundary.json').read_text())
    old=json.loads((root/'docs/evidence/ai-provider-001/preserved_files_sha256.json').read_text())['files']
    rows=data['reviewed_runtime_changes']
    if data['package']!='AI-001' or data['public_real_data_enabled'] is not False or set(rows)!=SUPERSEDED_RUNTIME:
        raise ValueError('Invalid AI-001 boundary scope')
    successor={}
    if (root/'docs/evidence/ai-002/change_boundary.json').is_file():
        from scripts.check_ai002_package import load_boundary as load_ai002_boundary
        successor=load_ai002_boundary(root)
    effective={}
    for rel,item in rows.items():
        current=successor.get(rel,item)['current_sha256']
        if item['previous_sha256']!=old.get(rel) or not hash_matches((root/rel).read_bytes(),current):
            raise ValueError('Runtime boundary checksum mismatch')
        effective[rel]={**item,'current_sha256':current}
    return {**effective, **successor}

def validate(root:Path=ROOT)->list[str]:
    errors=[]
    try:
        load_boundary(root)
        validate_policy(DEFAULT_POLICY)
        if REAL_DATA_SUPPORTED is not False:errors.append('Real-data execution must remain unavailable')
        if DEFAULT_POLICY['enabled'] or not DEFAULT_POLICY['kill_switch'] or DEFAULT_POLICY['commercial_enforcement_enabled']:
            errors.append('Activation or commercial defaults are unsafe')
        registry=ContractRegistry(root)
        fixtures=sorted((root/'evals/fixtures/cases').glob('*.json'))
        if len(fixtures)!=8:errors.append('Eight accepted fixtures are required')
        for p in fixtures:
            registry.load(p.stem)
            copy=root/f'prompts/ai/{CONTRACT}/{p.name}'
            if copy.read_bytes().replace(b'\r\n',b'\n')!=p.read_bytes().replace(b'\r\n',b'\n'):
                errors.append('Accepted prompt changed: '+p.name)
        for p in (root/'schemas/ai'/CONTRACT).glob('*.json'):
            original=root/'evals/schemas'/p.name
            if p.read_bytes().replace(b'\r\n',b'\n')!=original.read_bytes().replace(b'\r\n',b'\n'):
                errors.append('Accepted schema changed: '+p.name)
        db=(root/'database.py').read_text()
        successor=(root/'docs/evidence/ai-002/change_boundary.json').is_file()
        expected_head='20260917_0020' if (root/'docs/evidence/ai-005/change_boundary.json').is_file() else '20260917_0019' if (root/'docs/evidence/job-001/change_boundary.json').is_file() else '20260916_0018' if (root/'docs/evidence/ai-004/change_boundary.json').is_file() else '20260916_0017' if (root/'docs/evidence/ai-003/change_boundary.json').is_file() else '20260915_0016' if successor else '20260914_0015'
        if f'CURRENT_REVISION = "{expected_head}"' not in db:errors.append('Unexpected schema head')
        if successor:
            from scripts.check_ai002_package import validate as validate_ai002
            errors.extend(validate_ai002(root))
        migration=(root/'migrations/versions/20260914_0015_ai_runtime.py').read_text()
        if "down_revision = '20260819_0014'" not in migration and 'down_revision = "20260819_0014"' not in migration:
            errors.append('Migration must follow deployed 0014')
        tree=ast.parse(migration)
        names=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='create_table' and node.args:
                if isinstance(node.args[0],ast.Constant):names.add(node.args[0].value)
        if names!=TABLES:errors.append('Expected exactly seven additive AI tables')
        route=(root/'routes/ai_status.py').read_text()
        if "@bp.get('/api/ai/status')" not in route or 'bp.post' in route:errors.append('Only read-only AI status is allowed')
        for name in DOCUMENTS:
            text=(root/'docs'/f'{name}.md').read_text()
            if not all(s in text for s in ('# ','## 1.','## 2.','2026-09-14')):errors.append('Document incomplete: '+name)
        status=(root/'docs/AI001_VERIFICATION_STATUS.md').read_text()
        if not all(token in status for token in ('CI #266','20260914_0015','synthetic-only','bc177dd')):
            errors.append('Accepted AI-001 evidence is missing')
        legal=(root/'docs/LEGAL001_DEFERRED_DECISION.md').read_text()
        if '\u041e\u0422\u041b\u041e\u0416\u0415\u041d\u041e \u0414\u041e \u0420\u0415\u0428\u0415\u041d\u0418\u042f \u0412\u041b\u0410\u0414\u0415\u041b\u042c\u0426\u0410' not in legal:
            errors.append('Owner legal deferral is missing')
        workflow=(root/'.github/workflows/ci.yml').read_text()
        if 'python scripts/check_ai001_package.py' not in workflow or 'test_ai001_runtime.py' not in workflow:
            errors.append('Ordinary CI must run AI-001 gate and tests')
        if 'AI_LEGAL_APPROVED' in (root/'services/ai/settings.py').read_text():errors.append('No boolean legal bypass may be added')
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        errors.append('Missing or invalid AI-001 evidence/contract: '+type(exc).__name__)
    return errors

def main():
    errors=validate()
    print(json.dumps({'ok':not errors,'package':'AI-001','scope':'synthetic_only','external_ci':'pending','errors':errors},ensure_ascii=False,indent=2))
    return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
