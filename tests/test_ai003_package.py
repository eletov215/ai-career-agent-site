"""Package/static UI checks that do not require Flask or any paid API."""
import ast
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader, StrictUndefined, select_autoescape

from scripts.check_ai003_package import CHANGES, ROOT, load_boundary, validate
from services.ai.interview_labels import UI
from tests.test_ai003_service import env, answer, review, start, confirm_command


def test_package_contract_and_missing_evidence():
    assert validate() == []


def test_all_direct_package_commands_are_stdlib_only():
    for script in ('check_ai003_package.py', 'check_ai002_package.py', 'check_ai001_package.py',
                   'check_ai_provider_package.py', 'check_ai_bench_package.py'):
        result = subprocess.run([sys.executable, '-S', str(ROOT/'scripts'/script)],
                                cwd=ROOT, capture_output=True, text=True, timeout=45)
        assert result.returncode == 0, (script, result.stdout, result.stderr)


def test_missing_evidence_is_not_accepted(tmp_path):
    assert validate(tmp_path)


def copy_boundary(tmp_path):
    files = CHANGES | {'docs/evidence/ai-001/change_boundary.json', 'docs/evidence/ai-002/change_boundary.json',
                       'docs/evidence/ai-003/change_boundary.json', 'docs/evidence/ai-003/baseline_files_sha256.json',
                       'docs/evidence/ai-004/change_boundary.json', 'docs/evidence/ai-004/baseline_files_sha256.json'}
    for rel in files:
        (tmp_path/rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/rel, tmp_path/rel)
    assert load_boundary(tmp_path)


@pytest.mark.parametrize('violation', ['public', 'source', 'scope', 'baseline', 'runtime'])
def test_successor_scope_and_hashes_fail_closed(tmp_path, violation):
    copy_boundary(tmp_path)
    path = tmp_path/'docs/evidence/ai-003/change_boundary.json'
    data = json.loads(path.read_text())
    if violation == 'public':
        data['public_real_data_enabled'] = True
    elif violation == 'source':
        data['source_commit'] = '0'*40
    elif violation == 'scope':
        data['reviewed_runtime_changes']['evals/ai_bench/scoring.py'] = {'previous_sha256': 'a', 'current_sha256': 'b'}
    elif violation == 'baseline':
        data['reviewed_runtime_changes']['config.py']['previous_sha256'] = '0'*64
    else:
        (tmp_path/'app.py').write_text('tampered')
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_boundary(tmp_path)


def test_accepted_benchmark_provider_and_reference_artifacts_are_byte_preserved():
    baseline = json.loads((ROOT/'docs/evidence/ai-003/baseline_files_sha256.json').read_text())['files']
    for rel, expected in baseline.items():
        if rel.startswith(('evals/', 'prompts/', 'schemas/', 'docs/evidence/ai-001/',
                           'docs/evidence/ai-002/', 'docs/evidence/ai-provider-001/')) or rel in {
            'requirements.txt', 'requirements-dev.txt', 'services/ai/provider_policy.json',
            'services/ai/analysis_reference_manifest.json'}:
            assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == expected, rel


def test_new_sources_compile_and_do_not_import_provider_network():
    for rel in ('domain/resume_interview.py', 'services/resume_interview.py',
                'services/ai/interview_reference.py', 'repositories/resume_interview.py', 'routes/resume_interview.py'):
        code = (ROOT/rel).read_text()
        compile(code, rel, 'exec')
        modules = []
        for node in ast.walk(ast.parse(code)):
            if isinstance(node, ast.ImportFrom):
                modules.append(node.module or '')
            elif isinstance(node, ast.Import):
                modules.extend(item.name for item in node.names)
        assert not any(module.startswith(('requests', 'urllib', 'httpx', 'services.ai.provider', 'services.ai.service')) for module in modules)


def render_page(name, **values):
    # Stub only the application shell, not the new template itself. This is not a Flask HTTP test.
    environment = Environment(loader=ChoiceLoader([
        DictLoader({'base.html': '<!doctype html><html><head>{% block head_extra %}{% endblock %}</head><body>{% block content %}{% endblock %}</body></html>'}),
        FileSystemLoader(ROOT/'templates')]), autoescape=select_autoescape(['html']))
    environment.globals.update(url_for=lambda endpoint, **kwargs: '/'+endpoint,
                               csrf_token=lambda: 'test-csrf-token')
    return environment.get_template(name).render(ui=UI, operation_key=lambda: str(uuid4()), **values)


@pytest.mark.parametrize('language', ['ru', 'en'])
def test_all_private_template_states_and_escaping(env, language):
    page = render_page('interview/index.html', choices=env[-1].choices(), interviews=[])
    assert 'name="fixture_id"' in page and 'name="csrf_token"' in page
    result = start(env, language)
    for choice in ('vague', 'specific', 'measured', 'uncertain', 'documented'):
        page = render_page('interview/detail.html', interview=result)
        assert 'name="choice_id"' in page and '<textarea' not in page and 'type="file"' not in page
        result = answer(env, result, choice)
    page = render_page('interview/detail.html', interview=result)
    assert 'name="confirm"' in page and 'name="selected_fact_ids"' in page
    assert '<button' in page
    final = env[-1].execute(confirm_command(env, result, ['contribution']))
    page = render_page('interview/detail.html', interview=final)
    assert 'name="confirm"' not in page and 'name="answer_index"' not in page
    assert final['confirmed_text'] in page
    injected = copy.deepcopy(final)
    injected['confirmed_text'] = '<script>alert("secret")</script>'
    page = render_page('interview/detail.html', interview=injected)
    assert '<script>alert(' not in page and '&lt;script&gt;' in page
    error = render_page('interview/error.html', error='<script>private</script>')
    assert '&lt;script&gt;private' in error


def test_empty_fact_review_does_not_offer_false_confirmation(env):
    result = start(env)
    for _ in range(3):
        result = answer(env, result, 'skip')
    page = render_page('interview/detail.html', interview=result)
    assert result['status'] == 'review' and result['suggestions'] == []
    assert 'name="confirm"' not in page


def test_native_forms_are_usable_without_javascript():
    for path in (ROOT/'templates/interview').glob('*.html'):
        html = path.read_text()
        assert '<script' not in html and '|safe' not in html and 'onclick=' not in html
    css = (ROOT/'static/resume_interview.css').read_text()
    assert '@media' in css and ':focus-visible' in css and 'prefers-reduced-motion' in css
