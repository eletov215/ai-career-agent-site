"""Rebuilt JOB-001 scope, native rendering, and non-network controls."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, StrictUndefined, select_autoescape
from scripts.check_job001_package import ROOT, CHANGES, NEW_RUNTIME, EVIDENCE, load_boundary, validate
from services.saved_vacancy_labels import UI
from tests.test_job001_service import job_env, reference


def render_page(name, **values):
    environment = Environment(loader=ChoiceLoader([
        DictLoader({'base.html': '<!doctype html><html><head>{% block head_extra %}{% endblock %}</head><body>{% block content %}{% endblock %}</body></html>'}),
        FileSystemLoader(ROOT/'templates')]), undefined=StrictUndefined, autoescape=select_autoescape(['html']))
    environment.globals.update(url_for=lambda endpoint, **kwargs: '/'+endpoint,
                               csrf_token=lambda: 'test-only-csrf', csp_nonce='test-only-nonce')
    environment.filters['saved_time'] = lambda value: str(value)
    return environment.get_template(name).render(**values)


def test_package_passes_without_site_packages():
    assert validate() == []
    result = subprocess.run([sys.executable, '-S', str(ROOT/'scripts/check_job001_package.py')],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert json.loads(result.stdout)['external_ci'] == 'not_run'


def test_missing_scope_is_rejected(tmp_path):
    assert validate(tmp_path)


@pytest.mark.parametrize('mutation', ['public', 'commit', 'tree', 'previous', 'extra', 'missing', 'runtime', 'new_runtime'])
def test_scope_rejects_tampering(tmp_path, mutation):
    from tests.job001_boundary_helper import copy_job001_boundary
    copy_job001_boundary(ROOT, tmp_path)
    parent = Path('docs/evidence/ai-004/change_boundary.json')
    (tmp_path/parent).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT/parent, tmp_path/parent)
    assert load_boundary(tmp_path)
    path = tmp_path/'docs/evidence/job-001/change_boundary.json'
    data = json.loads(path.read_text())
    if mutation == 'public': data['public_real_data_enabled'] = True
    if mutation == 'commit': data['source_commit'] = '0'*40
    if mutation == 'tree': data['source_tree'] = '0'*40
    if mutation == 'previous': data['reviewed_runtime_changes']['app.py']['previous_sha256'] = '0'*64
    if mutation == 'extra': data['reviewed_runtime_changes']['config.py'] = {'previous_sha256': 'a', 'current_sha256': 'b'}
    if mutation == 'missing': data['new_runtime_sha256'].pop('routes/saved_vacancies.py')
    if mutation == 'runtime': (tmp_path/'app.py').write_text('unexpected code')
    if mutation == 'new_runtime': (tmp_path/'routes/saved_vacancies.py').write_text('unexpected code')
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError): load_boundary(tmp_path)


def test_closed_ai_and_dependencies_are_byte_preserved():
    base = json.loads((ROOT/'docs/evidence/job-001/baseline_files_sha256.json').read_text())['files']
    for rel, sha in base.items():
        if rel.startswith(('prompts/', 'schemas/', 'evals/', 'services/ai/')) or rel in {
            'config.py','render.yaml','requirements.txt','requirements-dev.txt','domain/ai.py'}:
            assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == sha, rel


def test_list_detail_conflict_and_error_are_escaped_native_forms(job_env):
    e = job_env
    row = e.svc.save(e.owner, reference(e)[0])
    record = e.svc.get(e.owner, row['id'])
    html = render_page('saved_vacancies/index.html', ui=UI, results=e.svc.list(e.owner))
    assert 'data-legacy-panel hidden' in html and 'data-legacy-form' in html
    assert 'name="csrf_token"' in html and 'name="confirm"' in html
    record['snapshot']['description'] = '<script>bad()</script>'
    record['old_snapshot'] = True
    html = render_page('saved_vacancies/detail.html', ui=UI, record=record, error=None,
                       draft_note='</textarea><script>bad()</script>', note_limit=4000)
    assert UI['old'] in html and UI['match_unavailable'] in html
    assert '<script>bad' not in html and '&lt;script&gt;' in html
    assert 'name="expected_revision" value="1"' in html and 'name="confirm"' in html
    assert 'name="note"' in html and 'method="post"' in html
    html = render_page('saved_vacancies/conflict.html', ui=UI, record=record,
                       draft_note='<b>unsaved note</b>', error='conflict')
    assert '&lt;b&gt;unsaved note&lt;/b&gt;' in html and 'name="expected_revision"' not in html
    assert 'unsaved note' in html
    html = render_page('saved_vacancies/error.html', ui=UI, error='<script>bad()</script>')
    assert '<script>bad' not in html
    empty = e.svc.list(e.other)
    assert UI['empty'] in render_page('saved_vacancies/index.html', ui=UI, results=empty)


def test_network_no_auto_import_csrf_and_accessibility_boundaries():
    for rel in ('repositories/saved_vacancies.py','services/saved_vacancies.py','routes/saved_vacancies.py'):
        tree = ast.parse((ROOT/rel).read_text())
        for node in ast.walk(tree):
            modules = [node.module or ''] if isinstance(node, ast.ImportFrom) else [m.name for m in node.names] if isinstance(node, ast.Import) else []
            assert not any(m.startswith(('requests','httpx','urllib.request','services.ai')) for m in modules)
    route = (ROOT/'routes/saved_vacancies.py').read_text()
    assert 'csrf.exempt' not in route and "user.email_verified_at is None" in route
    js = (ROOT/'static/saved_vacancies.js').read_text()
    assert 'innerHTML' not in js and 'saved_keys' in js
    css = (ROOT/'static/saved_vacancies.css').read_text()
    assert 'prefers-reduced-motion' in css and ':focus-visible' in css
    for path in (ROOT/'templates/saved_vacancies').glob('*.html'):
        assert '|safe' not in path.read_text()
