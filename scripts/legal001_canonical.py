"""Dependency-free canonical release checks for LEGAL-001 technical acceptance."""
from __future__ import annotations
import json
from pathlib import Path

BASELINE = "f5ce1f42836e3872854332324f2ebdd9c8934b36"
HISTORICAL_CI_COMMIT = "fe3a7e1b553ccc9ebb5b956efce3779287291c04"
HISTORICAL_CI_TREE = "55f03c287a3132aa9a2a55b7429c24d35e2a1957"
ACCEPTED_MAIN = "309afe0089356e6fb0d1c205ce7ca2c7cb682ae2"
ACCEPTED_TREE = "2616a3b15df09f85bf7ae261e605356fb9f52f9d"
PRODUCTION_RUNTIME = "28db01b719003149a0d616934e469b1b83c0237f"
SCHEMA = "20260922_0021"
HISTORICAL_EVIDENCE_PATH = "docs/evidence/legal-001/ci304_verified_summary.json"
FINAL_CI_EVIDENCE_PATH = "docs/evidence/legal-001/ci324_verified_summary.json"
FINAL_ACCEPTANCE_PATH = "docs/evidence/legal-001/technical_acceptance_20260924.json"

def first_table_value(text: str, key: str) -> str | None:
    for line in text.splitlines():
        cells=[cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and len(cells)==2 and cells[0]==key:
            return cells[1]
    return None

def validate_versions(plan: str, passport: str) -> list[str]:
    errors=[]
    for text,key,value,label in (
        (plan,"Версия","1.6.5","PLAN_CURRENT"),
        (passport,"Версия паспорта","2.80","PROJECT_PASSPORT"),
    ):
        if first_table_value(text,key)!=value:
            errors.append("Current canonical version mismatch: "+label)
    return errors

def validate_verification(text: str, evidence: dict) -> list[str]:
    errors=[]
    required={
        "Package":"LEGAL-001","Implementation":"IMPLEMENTED","Verification":"TECHNICAL_ACCEPTED",
        "Accepted technical main":ACCEPTED_MAIN,"Accepted technical tree":ACCEPTED_TREE,
        "Production runtime commit":PRODUCTION_RUNTIME,"Schema":SCHEMA,
        "Main GitHub CI":"#324 SUCCESS","Package preflight":"#11 SUCCESS",
        "Dedicated PostgreSQL verification":"#5 SUCCESS","T-05":"PASS","T-06":"PASS",
        "Production /health/ready 0021":"PASS","Production QA":"PASS_WITH_RECORDED_LIMITS",
        "Production legal state":"DRAFT / NOT_ACTIVE","Real-data Alice":"CLOSED",
        "Paid provider calls":"0","Legal-owner decisions":"PENDING",
        "Technical acceptance":"ACCEPTED","Complete":"NO",
    }
    for key,value in required.items():
        if first_table_value(text,key)!=value:
            errors.append("Unproven or inconsistent LEGAL-001 status: "+key)
    expected={
        "package":"LEGAL-001","status":"TECHNICAL_ACCEPTED","legal_status":"PENDING",
        "accepted_technical_main":ACCEPTED_MAIN,"accepted_technical_tree":ACCEPTED_TREE,
        "production_runtime_commit":PRODUCTION_RUNTIME,"schema":SCHEMA,
        "production_legal_state":"DRAFT / NOT_ACTIVE","real_data_enabled":False,
        "real_data_alice":"CLOSED","paid_provider_calls":0,
    }
    for key,value in expected.items():
        actual=evidence.get(key)
        if type(actual) is not type(value) or actual!=value:
            errors.append("Invalid LEGAL-001 technical acceptance evidence: "+key)
    eq=evidence.get("runtime_equivalence",{})
    expected_paths={".github/workflows/legal001-postgresql.yml","scripts/check_legal001_package.py","tests/test_legal001_postgresql.py"}
    if (not isinstance(eq,dict) or eq.get("compare_base")!=PRODUCTION_RUNTIME
            or eq.get("compare_head")!=ACCEPTED_MAIN or eq.get("application_runtime_changed") is not False
            or set(eq.get("changed_paths",[]))!=expected_paths):
        errors.append("Invalid runtime-equivalence evidence")
    qa=evidence.get("production_qa",{})
    if (not isinstance(qa,dict) or qa.get("status")!="PASS_WITH_RECORDED_LIMITS"
            or qa.get("consent_state_after_qa")!={"status":"withdrawn","cycle":4,"revision":2}):
        errors.append("Invalid production QA acceptance evidence")
    limits=evidence.get("remaining_limits",[])
    if not isinstance(limits,list) or len(limits)!=3:
        errors.append("Recorded evidence limits must remain explicit")
    return errors

def validate_ci324(evidence: dict) -> list[str]:
    errors=[]
    if evidence.get("package")!="LEGAL-001":
        errors.append("Invalid final CI evidence package")
    if evidence.get("accepted_technical_main")!=ACCEPTED_MAIN or evidence.get("accepted_technical_tree")!=ACCEPTED_TREE:
        errors.append("Final CI evidence points to wrong source")
    runs=evidence.get("runs",{})
    expected_runs={
        "main_ci":(35973632218,324),
        "package_preflight":(35973631903,11),
        "postgresql_verification":(35973631913,5),
    }
    for name,(run_id,run_number) in expected_runs.items():
        row=runs.get(name,{}) if isinstance(runs,dict) else {}
        if (row.get("run_id"),row.get("run_number"),row.get("status"),row.get("conclusion")) != (run_id,run_number,"completed","success"):
            errors.append("Invalid final CI run evidence: "+name)
    pg=evidence.get("postgres",{})
    if (not isinstance(pg,dict) or pg.get("version")!="17"
            or pg.get("production_credentials_used") is not False
            or pg.get("provider_credentials_used") is not False
            or pg.get("paid_provider_calls")!=0):
        errors.append("Invalid PostgreSQL environment evidence")
    t06=pg.get("t06",[]) if isinstance(pg,dict) else []
    if len(t06)!=8 or any(row.get("skipped")!=0 or row.get("passed",0)<1 for row in t06):
        errors.append("Incomplete T-06 PostgreSQL evidence")
    return errors

def validate_historical_ci304(evidence: dict) -> list[str]:
    required={"package":"LEGAL-001","run_id":35734563736,"run_number":304,
        "head_sha":HISTORICAL_CI_COMMIT,"tree_sha":HISTORICAL_CI_TREE,
        "conclusion":"success","paid_provider_calls":0,"paid_jobs":"skipped",
        "production_tested":False,"real_data_enabled":False}
    return ["Historical CI304 evidence changed: "+key for key,value in required.items()
            if type(evidence.get(key)) is not type(value) or evidence.get(key)!=value]

def validate(root: Path) -> list[str]:
    try:
        errors=validate_versions((root/"docs/PLAN_CURRENT.md").read_text(encoding="utf-8"),
                                 (root/"docs/PROJECT_PASSPORT.md").read_text(encoding="utf-8"))
        historical=json.loads((root/HISTORICAL_EVIDENCE_PATH).read_text(encoding="utf-8"))
        final_ci=json.loads((root/FINAL_CI_EVIDENCE_PATH).read_text(encoding="utf-8"))
        final_acceptance=json.loads((root/FINAL_ACCEPTANCE_PATH).read_text(encoding="utf-8"))
        if not all(isinstance(item,dict) for item in (historical,final_ci,final_acceptance)):
            return errors+["Malformed LEGAL-001 canonical evidence"]
        return errors+validate_historical_ci304(historical)+validate_ci324(final_ci)+validate_verification(
            (root/"docs/LEGAL001_VERIFICATION_STATUS.md").read_text(encoding="utf-8"),final_acceptance)
    except (OSError,ValueError,TypeError,KeyError):
        return ["Missing or malformed LEGAL-001 canonical evidence"]
