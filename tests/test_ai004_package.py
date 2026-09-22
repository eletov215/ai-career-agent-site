"""Dependency-free package protection and actual Jinja templates, not HTTP mocks."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4
import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, StrictUndefined, select_autoescape
from scripts.check_ai004_package import ROOT, CHANGES, load_boundary, validate
from services.ai.match_labels import UI
from tests.test_ai004_service import env, req


def test_package_contract_and_dependency_free_entrypoints():
    assert validate() == []
    for name in ('check_ai004_package','check_ai003_package','check_ai002_package','check_ai001_package','check_ai_provider_package','check_ai_bench_package'):
        result=subprocess.run([sys.executable,'-S',str(ROOT/'scripts'/f'{name}.py')],cwd=ROOT,capture_output=True,text=True,timeout=45)
        assert result.returncode==0,(name,result.stdout,result.stderr)


def test_missing_boundary_fails_closed(tmp_path):
    assert validate(tmp_path)


@pytest.mark.parametrize('change',['public','baseline','parent','runtime','scope'])
def test_explicit_hash_chain_cannot_allow_unreviewed_source(tmp_path,change):
    files=CHANGES|{'docs/evidence/ai-003/change_boundary.json','docs/evidence/ai-004/change_boundary.json','docs/evidence/ai-004/baseline_files_sha256.json'}
    for rel in files:
        path=tmp_path/rel;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/rel,path)
    from tests.job001_boundary_helper import copy_job001_boundary
    copy_job001_boundary(ROOT, tmp_path)
    assert load_boundary(tmp_path)
    path=tmp_path/'docs/evidence/ai-004/change_boundary.json';data=json.loads(path.read_text())
    if change=='public':data['public_real_data_enabled']=True
    if change=='baseline':data['source_commit']='0'*40
    if change=='parent':data['reviewed_runtime_changes']['app.py']['previous_sha256']='0'*64
    if change=='runtime':(tmp_path/'app.py').write_text('unexpected code')
    if change=='scope':data['reviewed_runtime_changes']['config.py']={'previous_sha256':'a','current_sha256':'b'}
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):load_boundary(tmp_path)


def test_existing_prompt_policy_dependency_and_frontend_bytes_preserved():
    baseline=json.loads((ROOT/'docs/evidence/ai-004/baseline_files_sha256.json').read_text())['files']
    for rel,sha in baseline.items():
        if rel.startswith(('evals/','prompts/','schemas/','templates/','static/','docs/policies/','services/ai/')) or rel in {'config.py','render.yaml','requirements.txt','requirements-dev.txt','domain/ai.py'}:
            from scripts.check_job001_package import load_boundary as job_boundary
            successor = job_boundary(ROOT)
            current_sha = sha
            if rel in successor:
                assert successor[rel]['previous_sha256'] == current_sha, rel
                current_sha = successor[rel]['current_sha256']
            if (ROOT/'docs/evidence/legal-001/change_boundary.json').is_file():
                from scripts.legal001_boundary import EXPECTED_EXISTING, PREVIOUS_EXISTING
                if rel in EXPECTED_EXISTING:
                    assert PREVIOUS_EXISTING[rel] == current_sha, rel
                    current_sha = EXPECTED_EXISTING[rel]
            assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==current_sha,rel


def render_page(name,**values):
    environment=Environment(loader=ChoiceLoader([DictLoader({'base.html':'<!doctype html><html><head>{% block head_extra %}{% endblock %}</head><body>{% block content %}{% endblock %}</body></html>'}),FileSystemLoader(ROOT/'templates')]),undefined=StrictUndefined,autoescape=select_autoescape(['html']))
    environment.globals.update(url_for=lambda endpoint,**values:'/'+endpoint,csrf_token=lambda:'test-csrf')
    return environment.get_template(name).render(**values)


@pytest.mark.parametrize('language,expected',[('ru',67),('en',71)])
def test_score_evidence_warning_history_and_escaped_sources_render(env,language,expected):
    svc=env[-1];record=svc.create_reference(req(env,language));report=svc.get(env[1],record['id'])
    html=render_page('matching/detail.html',ui=UI[language],report=report)
    assert f'{expected}<span>%</span>' in html
    assert 'data-mandatory-warning' in html
    assert html.count('data-status=')==report['result']['summary']['requirement_count']
    assert 'name="result_hash"' in html and 'value="1" required' in html
    for entry in report['result']['requirements']:
        assert entry['requirement'] in html
    index=render_page('matching/index.html',ui=UI['ru'],locales=UI,choices=svc.choices(),reports=svc.history(env[1]),operation_key=lambda:str(uuid4()))
    assert 'name="source_hash"' in index and 'name="operation_key"' in index and f'{expected}%' in index
    bad=copy.deepcopy(report);bad['result']['requirements'][0]['requirement']='<script>secret</script>'
    html=render_page('matching/detail.html',ui=UI[language],report=bad)
    assert '<script>secret' not in html and '&lt;script&gt;' in html
    bad['stale_source']=True
    assert UI[language]['stale'] in render_page('matching/detail.html',ui=UI[language],report=bad)


def test_gate_error_and_empty_states_render_without_javascript():
    for enabled in (False,True):
        html=render_page('matching/review_gate.html',ui=UI['ru'],enabled=enabled)
        assert 'name="csrf_token"' in html and '<form method="post"' in html
    html=render_page('matching/error.html',ui=UI['ru'],error='<script>secret</script>')
    assert '<script>secret' not in html and '&lt;script&gt;' in html
    html=render_page('matching/index.html',ui=UI['ru'],locales=UI,choices=[],reports=[],operation_key=lambda:str(uuid4()))
    assert UI['ru']['empty'] in html
    for path in (ROOT/'templates/matching').glob('*.html'):
        code=path.read_text();assert '<script' not in code and '|safe' not in code and '<textarea' not in code
    css=(ROOT/'static/vacancy_match.css').read_text()
    assert ':focus-visible' in css and '@media' in css and 'prefers-reduced-motion' in css


def test_storage_and_routes_do_not_add_provider_io_or_real_data_paths():
    for rel in ('domain/vacancy_match.py','repositories/vacancy_match.py','routes/vacancy_match.py'):
        tree=ast.parse((ROOT/rel).read_text())
        for node in ast.walk(tree):
            modules=[node.module or ''] if isinstance(node,ast.ImportFrom) else [n.name for n in node.names] if isinstance(node,ast.Import) else []
            assert not any(m.startswith(('requests','httpx','urllib','services.ai.service','services.ai.provider')) for m in modules)
    routes=(ROOT/'routes/vacancy_match.py').read_text()
    assert '.analyze(' not in routes and '.generate(' not in routes


def test_match_css_namespace_does_not_collide_with_existing_landing_widgets():
    css=(ROOT/'static/vacancy_match.css').read_text()
    html=(ROOT/'templates/matching/detail.html').read_text()
    assert '.match-score' not in css and 'class="match-card' not in html
    assert '.ai004-match-score' in css and 'ai004-match-score' in html
    # The old landing page has an absolutely positioned .match-score. Its
    # behavior must never apply to this document's normal-flow summary.
    assert 'position: absolute' not in css


@pytest.mark.parametrize('change', ['missing', 'scope', 'commit', 'ci', 'public', 'manual', 'backup', 'next'])
def test_closure_evidence_cannot_invent_acceptance(tmp_path, change):
    from scripts.check_ai004_package import validate_closure
    for rel in ('docs/AI004_VERIFICATION_STATUS.md', 'docs/evidence/ai-004/acceptance.json'):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, path)
    assert validate_closure(tmp_path) == []
    path = tmp_path / 'docs/evidence/ai-004/acceptance.json'
    data = json.loads(path.read_text())
    if change == 'missing':
        path.unlink()
    else:
        if change == 'scope': data['scope'] = 'public-live'
        if change == 'commit': data['accepted_code']['commit'] = '0' * 40
        if change == 'ci': data['github']['main_ci']['conclusion'] = 'failure'
        if change == 'public': data['owner_acceptance']['generation_available'] = True
        if change == 'manual': data['manual_two_account_isolation']['status'] = 'PASS'
        if change == 'backup': data['real_database_backup'] = 'PASS'
        if change == 'next': data['next_package']['implementation_started'] = True
        path.write_text(json.dumps(data))
    assert validate_closure(tmp_path)
