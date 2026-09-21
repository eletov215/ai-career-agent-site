"""Source-bound AI-005 execution using the existing Alice adapter and AI ledger.

No model response is a saved letter. Proposal insertion and successful accounting
commit atomically. A timeout/ambiguous transport result is never auto-retried.
There is no network I/O inside a database transaction.
"""
from __future__ import annotations
import time
from typing import Callable

from domain.ai import AIResult, ProviderCall, ProviderError, PROVIDER
from domain.cover_letter import LetterError
from repositories.ai import AIAdmissionError
from services.ai.letter_contract import LetterContract, validate_writing
from services.ai.policy import cost_microrub


class LetterRuntime:
    def __init__(self, ai_service, *, clock=time.time, monotonic=time.monotonic):
        self.repository = ai_service.repository
        self.settings = ai_service.settings
        self.provider = ai_service.provider
        self.clock = clock
        self.monotonic = monotonic
        if self.provider.provider_id != PROVIDER:
            raise ValueError('Unqualified provider')

    def run(self, *, user_id: str, operation_hash: str, request_hash: str,
            contract: LetterContract, preflight: Callable[[], None],
            on_success: Callable) -> AIResult:
        now = int(self.clock())
        reason = self.settings.gate(now)
        if reason:
            return AIResult('manual', reason)
        try:
            preflight()
            admitted = self.repository.admit(
                user_id=user_id, key_hash=operation_hash, request_hash=request_hash,
                fixture={'task':'cover_letter', 'language':contract.language,
                         'case_id':'general-letter-draft'},
                prompt_version=contract.version, now=now,
                input_estimate=contract.input_estimate,
            )
        except (LetterError, AIAdmissionError) as exc:
            return AIResult('manual', str(exc))
        except Exception:
            return AIResult('manual', 'ledger_unavailable')
        rid = admitted.request_id
        if admitted.duplicate:
            return AIResult('duplicate', 'already_' + str(admitted.previous_status), rid)
        p = admitted.policy
        # The shared ledger reserves its configured full retry cap. This new path
        # deliberately makes only one dispatch and reconciles unused reservation.
        per_attempt = cost_microrub(p['max_input_tokens'],p['max_output_tokens'],p)
        cost = inputs = outputs = 0
        uncertain = provider_failed = False
        status, reason = 'failed', 'cancelled_before_dispatch'
        validated = None
        started = self.monotonic()
        try:
            preflight()  # Owner/source/admission may have changed since reservation.
            reason = self.settings.gate(int(self.clock()))
            if reason:
                raise LetterError(reason)
            remaining = p['total_timeout_seconds'] - (self.monotonic()-started)
            if remaining <= 0:
                raise LetterError('deadline')
            if not self.repository.before_attempt(rid,now=int(self.clock())):
                raise LetterError('runtime_not_activated')
            try:
                response = self.provider.generate(ProviderCall(
                    rid, 'cover_letter', contract.language, contract.messages,
                    contract.schema, p['max_output_tokens'],
                    min(p['attempt_timeout_seconds'],remaining),
                ))
            except ProviderError as exc:
                uncertain = exc.unknown
                cost = per_attempt if uncertain else 0
                reason = exc.code
                provider_failed = exc.code in {'upstream_error','rate_limited','timeout_unknown',
                                                'transport_unknown','invalid_envelope'}
            except Exception:
                uncertain = True
                cost, reason, provider_failed = per_attempt, 'transport_unknown', True
            else:
                if (type(response.input_tokens) is not int or type(response.output_tokens) is not int
                        or not 0 <= response.input_tokens <= 1_000_000
                        or not 0 <= response.output_tokens <= 1_000_000):
                    cost, uncertain = per_attempt, True
                else:
                    inputs, outputs = response.input_tokens, response.output_tokens
                    cost = cost_microrub(inputs,outputs,p)
                if inputs > p['max_input_tokens'] or outputs > p['max_output_tokens']:
                    reason = 'usage_limit_overrun'
                elif self.monotonic()-started >= p['total_timeout_seconds']:
                    reason = 'deadline'
                elif response.finish_reason != 'stop':
                    reason = 'refusal' if response.finish_reason=='refusal' else 'incomplete_output'
                else:
                    try:
                        validated = validate_writing(response.content,contract)
                    except LetterError:
                        reason = 'feature_validation_failure'
                    else:
                        status, reason = 'succeeded', 'ok'
        except LetterError as exc:
            reason = str(exc)
        except Exception:
            # Reservation remains counted; interrupted worker recovery keeps it
            # conservative. No opaque exception text is included in the result.
            return AIResult('manual','ledger_unavailable',rid)
        if status!='succeeded' and uncertain:
            status = 'unknown'

        def store(session,event):
            on_success(session,event,validated)

        args = dict(status=status,reason=reason,cost=cost,uncertain=uncertain,
                    input_tokens=inputs,output_tokens=outputs,
                    provider_failed=provider_failed,now=int(self.clock()))
        try:
            delivered = self.repository.settle(rid, **args, on_success=store if status=='succeeded' else None)
        except (LetterError, AIAdmissionError):
            # Stale source/revoked admission/deleted document at delivery time:
            # the callback and success counters rolled back together. Record the
            # actual provider expense without a successful commercial action.
            try:
                delivered = self.repository.settle(rid, **{**args,
                    'status':'unknown' if uncertain else 'failed', 'reason':'result_not_delivered'},
                    on_success=None)
            except Exception:
                return AIResult('manual','ledger_unavailable',rid)
            return AIResult('manual','result_not_delivered',rid)
        except Exception:
            return AIResult('manual','ledger_unavailable',rid)
        if not delivered:
            return AIResult('manual','result_not_delivered',rid)
        if status=='succeeded':
            # The saved proposal is fetched by its owner separately; no private
            # model content is placed in status objects/loggable metadata.
            return AIResult('succeeded','ok',rid,commercial_action_consumed=bool(p['commercial_enforcement_enabled']))
        return AIResult('manual',reason,rid)
