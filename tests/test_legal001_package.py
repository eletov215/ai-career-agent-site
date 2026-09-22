"""LEGAL-001 package guard remains fail-closed and dependency-free."""
import json
import subprocess
import sys
from scripts.check_legal001_package import ROOT, validate

def test_legal001_package_guard():
    assert validate()==[]
    result=subprocess.run([sys.executable,"-S",str(ROOT/"scripts/check_legal001_package.py")],
        cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    report=json.loads(result.stdout)
    assert report["production_legal_state"]=="DRAFT"
    assert report["real_data_enabled"] is False
    assert report["paid_provider_calls"]==0
    assert report["remote_ci"]=="NOT ATTESTED BY LOCAL CHECK"

def test_no_client_or_environment_legal_bypass():
    route=(ROOT/"routes/privacy_controls.py").read_text()
    policy=(ROOT/"services/legal_policy.py").read_text()
    admission=(ROOT/"services/ai/letter_admission.py").read_text()
    assert "legal_approved" not in route
    assert "policy_version" not in route
    assert "os.environ" not in policy+admission
    assert "getenv(" not in policy+admission
    assert "AI_LEGAL_APPROVED" not in policy+admission
    assert 'REAL_DATA_SUPPORTED = False' in (ROOT/"domain/ai.py").read_text()
