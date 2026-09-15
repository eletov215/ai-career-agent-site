"""Bounded synthetic-only orchestration, independent of Flask/provider transport.

There is intentionally no arbitrary-text entry point and no public POST handler.
Schema validation is not a claim of semantic grounding for future real profiles.
"""
from __future__ import annotations
import hashlib,hmac,json,re,time
from dataclasses import asdict
from domain.ai import AIRequest,AIResult,ProviderCall,ProviderError,PROVIDER,CONTRACT,REAL_DATA_SUPPORTED
from repositories.ai import AIRepository,AIAdmissionError
from services.ai.provider import YandexAliceProvider
from services.ai.registry import ContractRegistry,ContractError,validate_output
from services.ai.policy import cost_microrub
from services.ai.settings import AISettings

# Deliberately human-facing and neutral; internal gates/credentials are not exposed.
MANUAL_NOTICE = ('AI-\u0444\u0443\u043d\u043a\u0446\u0438\u0438 \u043f\u043e\u043a\u0430 \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b. '
                 '\u041f\u043e\u0438\u0441\u043a \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0439, \u043f\u0440\u043e\u0444\u0438\u043b\u044c \u0438 \u0440\u0443\u0447\u043d\u043e\u0435 \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435 \u0440\u0435\u0437\u044e\u043c\u0435 \u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0430\u044e\u0442 \u0440\u0430\u0431\u043e\u0442\u0430\u0442\u044c.')

class AIService:
    def __init__(self,repository:AIRepository,settings:AISettings,*,fingerprint_key:str,
                 provider=None,registry=None,clock=time.time,monotonic=time.monotonic,sleep=time.sleep):
        if not fingerprint_key:raise ValueError('Fingerprint key is required')
        self.repository=repository;self.settings=settings;self.fingerprint_key=fingerprint_key.encode()
        self.provider=provider or YandexAliceProvider(settings)
        if self.provider.provider_id!=PROVIDER:raise ValueError('Unqualified provider')
        self.registry=registry or ContractRegistry();self.clock=clock;self.monotonic=monotonic;self.sleep=sleep

    def public_status(self)->dict:
        # Public runtime is intentionally not activated, even if synthetic access is enabled.
        # No database/network work on page rendering and no configuration disclosure.
        return {'ok':True,'generation_available':False,'mode':'manual','reason':'runtime_not_activated',
                'notice_key':'ai_temporarily_unavailable_manual_mode','notice':MANUAL_NOTICE}

    def _digest(self,items:list)->str:
        return hmac.new(self.fingerprint_key,json.dumps(items,ensure_ascii=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()

    def generate(self,request:AIRequest)->AIResult:
        if not isinstance(request,AIRequest):return AIResult('manual','invalid_request')
        if not re.fullmatch(r'[A-Za-z0-9:_-]{8,128}',request.idempotency_key) or not re.fullmatch(r'[a-fA-F0-9-]{36}',request.user_id):
            return AIResult('manual','invalid_request')
        now=int(self.clock());reason=self.settings.gate(now)
        if reason:return AIResult('manual',reason)
        try:
            fixture,schema=self.registry.load(request.fixture_id)
            # Character-based preflight estimate for pinned synthetic fixtures ONLY.
            # It is not a vendor tokenizer. Full cap is reserved; actual overruns stop AI.
            estimate=len(json.dumps({'messages':fixture['messages'],'schema':schema},ensure_ascii=False))+256
            admission=self.repository.admit(user_id=request.user_id,
                key_hash=self._digest(['key',request.user_id,request.idempotency_key]),
                request_hash=self._digest(['request',request.user_id,request.fixture_id,CONTRACT]),fixture=fixture,now=now,input_estimate=estimate)
        except AIAdmissionError as exc:return AIResult('manual',str(exc))
        except ContractError:return AIResult('manual','invalid_contract')
        except Exception:return AIResult('manual','ledger_unavailable')
        rid=admission.request_id;p=admission.policy
        if admission.duplicate:
            # Output is not cached here; future feature documents own persisted results.
            return AIResult('duplicate','already_'+str(admission.previous_status),rid)
        started=self.monotonic();cost=0;uncertain=False;inputs=0;outputs=0;result=None
        status='failed';reason='cancelled_before_dispatch';provider_failed=False
        per_attempt=cost_microrub(p['max_input_tokens'],p['max_output_tokens'],p)
        try:
            for attempt in range(p['max_attempts']):
                remaining=p['total_timeout_seconds']-(self.monotonic()-started)
                if remaining<=0:
                    reason='deadline';break
                if not self.repository.before_attempt(rid,now=int(self.clock())):
                    reason='runtime_not_activated';break
                call=ProviderCall(rid,fixture['task'],fixture['language'],fixture['messages'],schema,
                                  p['max_output_tokens'],min(p['attempt_timeout_seconds'],remaining))
                try:
                    response=self.provider.generate(call)
                except ProviderError as exc:
                    if exc.unknown:cost+=per_attempt;uncertain=True
                    reason=exc.code;provider_failed=exc.code in {'upstream_error','rate_limited','timeout_unknown','transport_unknown','invalid_envelope'}
                    if exc.retryable and attempt+1<p['max_attempts']:
                        delay=p['retry_delay_seconds']
                        if self.monotonic()-started+delay>=p['total_timeout_seconds']:break
                        self.sleep(delay);continue
                    break
                except Exception:
                    # An unknown post-dispatch exception must never refund possible spend.
                    cost+=per_attempt;uncertain=True;reason='transport_unknown';provider_failed=True;break
                if response.input_tokens is None or response.output_tokens is None:
                    cost+=per_attempt;uncertain=True
                else:
                    inputs+=response.input_tokens;outputs+=response.output_tokens
                    cost+=cost_microrub(response.input_tokens,response.output_tokens,p)
                if ((response.input_tokens is not None and response.input_tokens>p['max_input_tokens']) or
                    (response.output_tokens is not None and response.output_tokens>p['max_output_tokens'])):
                    reason='usage_limit_overrun';break
                if self.monotonic()-started>=p['total_timeout_seconds']:
                    reason='deadline';break
                if response.finish_reason!='stop':
                    reason='refusal' if response.finish_reason=='refusal' else 'incomplete_output';break
                try:result=validate_output(response.content,schema)
                except ContractError:reason='schema_failure';break
                status='succeeded';reason='ok';provider_failed=False;break
        except Exception:
            # Database failure after a reservation: keep the full pre-counted reservation.
            return AIResult('manual','ledger_unavailable',rid)
        if status!='succeeded' and uncertain:status='unknown'
        try:
            accepted=self.repository.settle(rid,status=status,reason=reason,cost=cost,uncertain=uncertain,
                input_tokens=inputs,output_tokens=outputs,provider_failed=provider_failed,now=int(self.clock()))
            if not accepted:return AIResult('manual','result_not_delivered',rid)
        except Exception:return AIResult('manual','ledger_unavailable',rid)
        if status=='succeeded':return AIResult('succeeded','ok',rid,result,bool(p['commercial_enforcement_enabled']))
        return AIResult('manual',reason,rid)
