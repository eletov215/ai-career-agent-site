import json
import shutil
import subprocess
import sys
from pathlib import Path
import pytest
from scripts.check_ai005_r2_package import ROOT,load_boundary,validate
from tests.ai005_boundary_helper import copy_ai005_boundary


def test_r2_guard_preserves_r1_acceptance_and_closed_real_data():
    assert validate()==[]
    result=subprocess.run([sys.executable,'-S',str(ROOT/'scripts/check_ai005_r2_package.py')],
        cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('mutation',['public','commit','previous','runtime','new','extra','r1_continuity'])
def test_r2_boundary_tampering_is_rejected(tmp_path,mutation):
    copy_ai005_boundary(ROOT,tmp_path);assert load_boundary(tmp_path)
    p=tmp_path/'docs/evidence/ai-005-r2/change_boundary.json';d=json.loads(p.read_text())
    if mutation=='public':d['public_real_data_enabled']=True
    if mutation=='commit':d['source_commit']='0'*40
    if mutation=='previous':d['reviewed_runtime_changes']['app.py']['previous_sha256']='0'*64
    if mutation=='runtime':(tmp_path/'repositories/ai.py').write_text('changed')
    if mutation=='new':(tmp_path/'services/ai/letter_runtime.py').write_text('changed')
    if mutation=='extra':d['reviewed_runtime_changes']['config.py']={}
    if mutation=='r1_continuity':
        p1=tmp_path/'docs/evidence/ai-005/change_boundary.json';d1=json.loads(p1.read_text())
        d1['reviewed_runtime_changes']['app.py']['current_sha256']='0'*64;p1.write_text(json.dumps(d1))
    p.write_text(json.dumps(d))
    from scripts.check_ai005_package import load_boundary as load_parent
    with pytest.raises(ValueError):load_parent(tmp_path)


def test_preview_template_escapes_provider_source_and_token():
    from tests.test_ai005_package import render
    from services.cover_letter_labels import UI
    preview={'projection':{'candidate_facts':[{'id':'profile.summary','text':'<script>private</script>'}],
                'vacancy':{'title':'<b>role</b>'},'preferences':{'language':'en','length':'short','tone':'professional'}},
             'recipient':'Yandex','review_token':'\" onclick=\"bad'}
    result=render('letters/generation_preview.html',preview=preview,letter_id='fake')
    assert '<script>private' not in result and '&lt;script&gt;' in result
    assert 'name="csrf_token"' in result and 'name="confirm"' in result
    assert 'onclick="bad' not in result
