"""Synthetic-only AI-002 feature service, independent of the Flask interface.

Reference reports are explicitly labeled, never represented as live model output.
The real transport is reachable only through AI-001's existing closed gates.
"""
import hashlib
import hmac
import json
import re
import time
from pathlib import Path
from domain.ai import AIRequest, CONTRACT
from domain.resume_analysis import AnalysisRequest, AnalysisOutcome, AnalysisError, FIXTURE_IDS
from services.ai.registry import ContractRegistry, ContractError
from services.ai.analysis_validation import validate_analysis

ROOT=Path(__file__).resolve().parents[1]

class ResumeAnalysisService:
    def __init__(self, repository, runtime, *, fingerprint_key, root=ROOT, clock=time.time):
        if not fingerprint_key:raise ValueError('Fingerprint key is required')
        self.repository=repository;self.runtime=runtime;self.clock=clock;self.key=fingerprint_key.encode()
        self.root=Path(root);self.registry=ContractRegistry(self.root)

    def source(self, fixture_id):
        if fixture_id not in FIXTURE_IDS:raise AnalysisError('invalid_source')
        fixture,schema=self.registry.load(fixture_id)
        serialized=json.dumps(fixture,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
        return fixture,schema,hashlib.sha256(serialized).hexdigest()

    def choices(self):
        return [{'id': f, 'language': self.source(f)[0]['language'], 'source_hash': self.source(f)[2]} for f in FIXTURE_IDS]

    def _prepare(self, request, origin):
        if not isinstance(request,AnalysisRequest) or not isinstance(request.user_id,str) or not re.fullmatch(r'[a-fA-F0-9-]{36}',request.user_id):
            raise AnalysisError('invalid_request')
        if not isinstance(request.idempotency_key,str) or not re.fullmatch(r'[A-Za-z0-9:_-]{8,128}', request.idempotency_key):
            raise AnalysisError('invalid_request')
        self.repository.check_owner(request.user_id)
        fixture,schema,source_hash=self.source(request.fixture_id)
        if source_hash!=request.expected_source_hash:raise AnalysisError('stale_source')
        digest=hmac.new(self.key,json.dumps(['analysis',request.user_id,request.idempotency_key],separators=(',',':')).encode(),hashlib.sha256).hexdigest()
        old=self.repository.find_operation(request.user_id,digest)
        if old and (old['fixture_id']!=request.fixture_id or old['source_hash']!=source_hash or old['origin']!=origin):
            raise AnalysisError('idempotency_conflict')
        if old is None:self.repository.check_owner(request.user_id, room=True)
        return fixture,schema,source_hash,digest,old

    def create_reference(self, request):
        """Offline UI verification with pinned developer-authored reference text."""
        try:
            fixture,schema,source_hash,key,old=self._prepare(request,'reference')
            if old:return AnalysisOutcome('succeeded','already_saved',old)
            path=f'prompts/analysis/reference/{request.fixture_id}.json'
            manifest=json.loads((self.root/'services/ai/analysis_reference_manifest.json').read_text())
            raw=(self.root/path).read_bytes()
            if hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()!=manifest['files'][path]:
                raise AnalysisError('invalid_reference')
            output=validate_analysis(json.loads(raw),fixture,schema)
            report=self.repository.save(user_id=request.user_id,operation_hash=key,fixture=fixture,source_hash=source_hash,
                source_version=CONTRACT,output=output,origin='reference',usage_event_id=None,now=int(self.clock()))
            return AnalysisOutcome('succeeded','reference_not_live_ai',report)
        except AnalysisError as exc:return AnalysisOutcome('manual',str(exc))
        except (ContractError,ValueError,KeyError):return AnalysisOutcome('manual','invalid_contract')
        except Exception:return AnalysisOutcome('manual','storage_unavailable')

    def analyze(self, request):
        """Internal provider path: no arbitrary profile text or HTTP POST binding."""
        try:
            fixture,schema,source_hash,key,old=self._prepare(request,'provider')
            if old:return AnalysisOutcome('succeeded','already_saved',old)
            result=self.runtime.generate(AIRequest(request.user_id,key,request.fixture_id),
                result_validator=lambda value, _fixture, _schema: validate_analysis(value,fixture,schema))
            if result.status!='succeeded' or result.content is None:
                # Do not make a second billable call when ledger succeeded but save
                # was interrupted. Recovery of missing content is not fabricated.
                old=self.repository.find_operation(request.user_id,key)
                return AnalysisOutcome('succeeded','already_saved',old) if old else AnalysisOutcome('manual',result.reason)
            report=self.repository.save(user_id=request.user_id,operation_hash=key,fixture=fixture,source_hash=source_hash,
                source_version=CONTRACT,output=result.content,origin='provider',usage_event_id=result.request_id,now=int(self.clock()))
            return AnalysisOutcome('succeeded','ok',report)
        except AnalysisError as exc:return AnalysisOutcome('manual',str(exc))
        except (ContractError,ValueError,KeyError):return AnalysisOutcome('manual','invalid_contract')
        except Exception:return AnalysisOutcome('manual','storage_unavailable')

    def get(self,user_id,report_id):return self.repository.get(user_id,report_id)
    def history(self,user_id):return self.repository.list(user_id, limit=100)
    def decide(self,**kwargs):return self.repository.decide(now=int(self.clock()),**kwargs)
    def delete(self,user_id,report_id,source_hash):return self.repository.delete(user_id,report_id,source_hash)
