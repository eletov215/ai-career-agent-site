from __future__ import annotations
import json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] if 'tests' in str(Path(__file__).resolve()) else Path.cwd()
CHECKER = ROOT / 'scripts/check_ai_bench_alice_final_result.py'

def sample_run(passed=8, errors=0, status='passed', provider_id='yandex-alice-ai-llm'):
    return {'execution_mode':'live_or_mixed','status':status,'dataset':{'case_count':8},'providers':[{'id':provider_id,'summary':{'case_count':8,'passed_count':passed,'error_count':errors,'retry_count':0,'forbidden_claim_count':0,'unsupported_number_count':0,'user_facing_technical_token_count':0,'claim_evidence_violation_count':0,'unsupported_impact_claim_count':0,'language_consistency_violation_count':0,'scenario_provenance_violation_count':0,'match_consistency_violation_count':0,'mean_quality_score':1.0,'mean_grounding_score':1.0,'p95_latency_ms':1000,'estimated_cost_usd':0.01}}]}

class AliceFinalGateTests(unittest.TestCase):
    def _run(self,payload):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'run.json'; path.write_text(json.dumps(payload),encoding='utf-8')
            return subprocess.run([sys.executable,str(CHECKER),str(path)],cwd=ROOT,text=True,capture_output=True,check=False)
    def test_pass(self):
        c=self._run(sample_run()); self.assertEqual(c.returncode,0,c.stderr)
    def test_partial_rejected(self):
        c=self._run(sample_run(passed=7,status='failed')); self.assertNotEqual(c.returncode,0); self.assertIn('machine safety gate not fully passed',c.stderr)
    def test_wrong_provider_rejected(self):
        c=self._run(sample_run(provider_id='yandex-alice-ai-llm-flash')); self.assertNotEqual(c.returncode,0)
    def test_safety_counter_rejected(self):
        p=sample_run(); p['providers'][0]['summary']['unsupported_impact_claim_count']=1
        c=self._run(p); self.assertNotEqual(c.returncode,0); self.assertIn('non-zero safety counters',c.stderr)
if __name__=='__main__': unittest.main()
