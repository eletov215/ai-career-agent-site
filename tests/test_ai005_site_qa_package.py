"""AI-005 SITE QA package guard remains synthetic-only and fail-closed."""
import json
import subprocess
import sys
from scripts.check_ai005_site_qa_package import ROOT, validate


def test_ai005_site_qa_package_guard():
    assert validate()==[]
    result=subprocess.run([sys.executable,"-S",str(ROOT/"scripts/check_ai005_site_qa_package.py")],
        cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    report=json.loads(result.stdout)
    assert report["scope"]=="synthetic_only"
    assert report["paid_provider_calls"]==0
    assert report["real_data_enabled"] is False
    assert report["remote_ci"]=="NOT ATTESTED BY LOCAL CHECK"
