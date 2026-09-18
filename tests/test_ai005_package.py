"""Explicit source scope and escaped native rendering, independent of Flask."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import shutil
import pytest
from jinja2 import Environment,ChoiceLoader,DictLoader,FileSystemLoader,StrictUndefined,select_autoescape
from scripts.check_ai005_package import ROOT,CHANGES,NEW_RUNTIME,EVIDENCE,load_boundary,validate
from tests.ai005_boundary_helper import copy_ai005_boundary
from services.cover_letter_labels import UI
from tests.test_ai005_service import letters,new,save,proposal
from tests.test_job001_service import job_env


def render(name,**data):
    env=Environment(loader=ChoiceLoader([DictLoader({'base.html':'<!doctype html><html><head>{% block head_extra %}{% endblock %}</head><body>{% block content %}{% endblock %}</body></html>'}),FileSystemLoader(ROOT/'templates')]),undefined=StrictUndefined,autoescape=select_autoescape(['html']))
    env.globals.update(url_for=lambda endpoint,**kwargs:'/'+endpoint,csrf_token=lambda:'test-only')
    return env.get_template(name).render(ui=UI,**data)


def test_package_status_and_dependency_free_check():
    assert validate()==[]
    run=subprocess.run([sys.executable,'-S',str(ROOT/'scripts/check_ai005_package.py')],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert run.returncode==0,run.stdout+run.stderr
    assert json.loads(run.stdout)['remote_ci']=='not_attested_by_local_check'


@pytest.mark.parametrize('mutation',['public','commit','tree','previous','changed_file','new_file','new_missing','extra'])
def test_new_hash_boundary_rejects_mutations(tmp_path,mutation):
    copy_ai005_boundary(ROOT,tmp_path);assert load_boundary(tmp_path)
    path=tmp_path/'docs/evidence/ai-005/change_boundary.json';data=json.loads(path.read_text())
    if mutation=='public':data['public_real_data_enabled']=True
    if mutation=='commit':data['source_commit']='0'*40
    if mutation=='tree':data['source_tree']='0'*40
    if mutation=='previous':data['reviewed_runtime_changes']['app.py']['previous_sha256']='0'*64
    if mutation=='changed_file':(tmp_path/'app.py').write_text('wrong')
    if mutation=='new_file':(tmp_path/'services/cover_letters.py').write_text('wrong')
    if mutation=='new_missing':data['new_runtime_sha256'].pop('domain/cover_letter.py')
    if mutation=='extra':data['reviewed_runtime_changes']['config.py']={}
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):load_boundary(tmp_path)


def test_editor_template_version_comparison_and_conflict_escape_content(letters):
    e=letters;row=new(e);record=e.svc.get(e.owner,row['id'])
    editor={**row['content'],'subject':'<script>title</script>','body':'</textarea><script>body</script>'}
    html=render('letters/detail.html',record=record,proposal=None,editor=editor,operation_key='test',max_body=8000,max_subject=240)
    assert '<script>title' not in html and '<script>body' not in html
    assert '&lt;script&gt;' in html and 'name="confirm"' in html and 'name="expected_revision"' in html
    row=save(e,row,body='Before');row=save(e,row,body='<script>After</script>')
    record=e.svc.get(e.owner,row['id']);version=e.svc.version(e.owner,row['id'],2)
    html=render('letters/version.html',record=record,version=version)
    assert '<script>After' not in html and '&lt;script&gt;After' in html
    html=render('letters/compare.html',letter_id=row['id'],compared=e.svc.compare(e.owner,row['id'],1,2))
    assert '<script>After' not in html
    html=render('letters/conflict.html',record=record,draft=editor)
    assert 'name="expected_revision"' not in html and '&lt;/textarea&gt;' in html


def test_library_source_preview_and_pending_proposal_states_render(letters):
    e=letters
    html=render('letters/index.html',results=e.svc.list(e.owner),source=None,saved_id=None)
    assert UI['empty'] in html
    source=e.svc.source(e.owner,e.saved_id)
    html=render('letters/index.html',results=e.svc.list(e.owner),source=source,saved_id=e.saved_id,operation_key='test')
    assert 'name="source_hash"' in html and UI['source_confirm'] in html
    row=new(e);p=proposal(e,row);record=e.svc.get(e.owner,row['id'])
    html=render('letters/detail.html',record=record,proposal=p,editor=p['content'],operation_key='test',max_body=8000,max_subject=240)
    assert UI['local_template'] in html and UI['unreviewed'] in html
    assert 'name="proposal_id"' in html


def test_no_network_no_auto_send_and_current_ai_boundary():
    for rel in ('routes/cover_letters.py','repositories/cover_letters.py','services/cover_letters.py','services/cover_letter_generation.py'):
        tree=ast.parse((ROOT/rel).read_text())
        for node in ast.walk(tree):
            modules=[node.module or ''] if isinstance(node,ast.ImportFrom) else [x.name for x in node.names] if isinstance(node,ast.Import) else []
            assert not any(m.startswith(('requests','httpx','smtplib','urllib.request','services.ai.provider')) for m in modules)
    assert "raise LetterError('generation_unavailable')" in (ROOT/'services/cover_letters.py').read_text()
    css=(ROOT/'static/cover_letters.css').read_text();assert 'prefers-reduced-motion' in css and ':focus-visible' in css
    for file in (ROOT/'templates/letters').glob('*.html'):
        assert '|safe' not in file.read_text()
    assert 'REAL_DATA_SUPPORTED = False' in (ROOT/'domain/ai.py').read_text()
