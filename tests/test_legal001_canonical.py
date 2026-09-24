"""Canonical LEGAL-001 technical-acceptance status and inherited gates."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from scripts.legal001_canonical import (
    ACCEPTED_MAIN,ACCEPTED_TREE,PRODUCTION_RUNTIME,SCHEMA,
    first_table_value,validate_versions,validate_verification,validate_ci324,
)
ROOT=Path(__file__).resolve().parents[1]

def status_fixture():
    rows={
        "Package":"LEGAL-001","Implementation":"IMPLEMENTED","Verification":"TECHNICAL_ACCEPTED",
        "Accepted technical main":ACCEPTED_MAIN,"Accepted technical tree":ACCEPTED_TREE,
        "Production runtime commit":PRODUCTION_RUNTIME,"Schema":SCHEMA,
        "Main GitHub CI":"#324 SUCCESS","Package preflight":"#11 SUCCESS",
        "Dedicated PostgreSQL verification":"#5 SUCCESS","T-05":"PASS","T-06":"PASS",
        "Production /health/ready 0021":"PASS","Production QA":"PASS_WITH_RECORDED_LIMITS",
        "Production legal state":"DRAFT / NOT_ACTIVE","Real-data Alice":"CLOSED",
        "Paid provider calls":"0","Legal-owner decisions":"PENDING","Technical acceptance":"ACCEPTED","Complete":"NO",
    }
    evidence={"package":"LEGAL-001","status":"TECHNICAL_ACCEPTED","legal_status":"PENDING",
        "accepted_technical_main":ACCEPTED_MAIN,"accepted_technical_tree":ACCEPTED_TREE,
        "production_runtime_commit":PRODUCTION_RUNTIME,"schema":SCHEMA,
        "runtime_equivalence":{"compare_base":PRODUCTION_RUNTIME,"compare_head":ACCEPTED_MAIN,
            "application_runtime_changed":False,
            "changed_paths":[".github/workflows/legal001-postgresql.yml","scripts/check_legal001_package.py","tests/test_legal001_postgresql.py"]},
        "production_qa":{"status":"PASS_WITH_RECORDED_LIMITS",
            "consent_state_after_qa":{"status":"withdrawn","cycle":4,"revision":2}},
        "remaining_limits":["a","b","c"],"production_legal_state":"DRAFT / NOT_ACTIVE",
        "real_data_enabled":False,"real_data_alice":"CLOSED","paid_provider_calls":0}
    text="\n".join(f"| {key} | {value} |" for key,value in rows.items())
    return text,evidence

class PureStatusTests(unittest.TestCase):
    def test_technical_acceptance_stays_legally_closed(self):
        self.assertEqual([],validate_verification(*status_fixture()))
    def test_legal_or_live_overclaims_rejected(self):
        text,evidence=status_fixture()
        for key,value in (("Verification","COMPLETE"),("Production legal state","ACTIVE"),
                          ("Real-data Alice","OPEN"),("Paid provider calls","1"),
                          ("Legal-owner decisions","COMPLETE"),("Complete","YES")):
            with self.subTest(key=key):
                old=first_table_value(text,key)
                self.assertTrue(validate_verification(text.replace(f"| {key} | {old} |",f"| {key} | {value} |"),evidence))
    def test_runtime_equivalence_must_remain_exact(self):
        text,evidence=status_fixture()
        for mutation in ({"application_runtime_changed":True},{"compare_head":"0"*40},{"changed_paths":["app.py"]}):
            bad=deepcopy(evidence);bad["runtime_equivalence"].update(mutation)
            self.assertTrue(validate_verification(text,bad))
    def test_recorded_limits_cannot_be_erased(self):
        text,evidence=status_fixture();bad=deepcopy(evidence);bad["remaining_limits"]=[]
        self.assertTrue(validate_verification(text,bad))
    def test_ci324_requires_all_three_green_runs_and_t06(self):
        evidence={"package":"LEGAL-001","accepted_technical_main":ACCEPTED_MAIN,"accepted_technical_tree":ACCEPTED_TREE,
            "runs":{"main_ci":{"run_id":35973632218,"run_number":324,"status":"completed","conclusion":"success"},
                    "package_preflight":{"run_id":35973631903,"run_number":11,"status":"completed","conclusion":"success"},
                    "postgresql_verification":{"run_id":35973631913,"run_number":5,"status":"completed","conclusion":"success"}},
            "postgres":{"version":"17","production_credentials_used":False,"provider_credentials_used":False,
                        "paid_provider_calls":0,"t06":[{"passed":1,"skipped":0} for _ in range(8)]}}
        self.assertEqual([],validate_ci324(evidence))
        bad=deepcopy(evidence);bad["runs"]["main_ci"]["conclusion"]="failure";self.assertTrue(validate_ci324(bad))
        bad=deepcopy(evidence);bad["postgres"]["t06"][0]["skipped"]=1;self.assertTrue(validate_ci324(bad))
    def test_current_version_cannot_be_satisfied_by_historical_row(self):
        plan="| Версия | 1.6.5 |\n";passport="| Версия паспорта | 2.80 |\n"
        self.assertEqual([],validate_versions(plan,passport))
        self.assertTrue(validate_versions(plan.replace("1.6.5","1.6.4")+plan,passport))
        self.assertTrue(validate_versions(plan,passport.replace("2.80","2.79")+passport))

class RepositoryGateTests(unittest.TestCase):
    def test_every_package_gate_in_clean_dependency_free_process(self):
        for name in ("check_ai001_package.py","check_ai002_package.py","check_ai003_package.py","check_ai004_package.py",
                     "check_job001_package.py","check_ai005_package.py","check_ai005_r2_package.py",
                     "check_ai_provider_package.py","check_legal001_package.py"):
            with self.subTest(gate=name):
                result=subprocess.run([sys.executable,"-S",str(ROOT/"scripts"/name)],cwd=ROOT,capture_output=True,text=True,timeout=45)
                self.assertEqual(0,result.returncode,result.stdout+result.stderr)
                self.assertTrue(json.loads(result.stdout)["ok"])
    def test_deferred_decision_remains_byte_preserved(self):
        from scripts.check_ai005_package import matches
        baseline=json.loads((ROOT/"docs/evidence/ai-005/baseline_files_sha256.json").read_text())
        rel="docs/LEGAL001_DEFERRED_DECISION.md"
        self.assertTrue(matches(ROOT/rel,baseline["files"][rel]))
if __name__=="__main__":unittest.main()
