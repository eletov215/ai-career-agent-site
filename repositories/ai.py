"""Atomic AI admission and settlement. Transactions never contain HTTP calls.

All control-plane mutations lock the singleton policy row on PostgreSQL or use
BEGIN IMMEDIATE on SQLite. Budgets count reservations immediately. Global buckets
and anonymous leases survive account deletion; refunds are never invented.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timezone, date
from dataclasses import dataclass
import json
from uuid import uuid4
from sqlalchemy import select, delete, func, text
from models.ai import (AIRuntimePolicy, AIUsageEvent, AIBudgetBucket, AIRequestLease,
                       AIProviderState, AIPlanEntitlement, AIUserPlan)
from models.user import User
from repositories.base import RepositoryBase
from services.ai.policy import validate_policy, cost_microrub
from domain.ai import PROVIDER, CONTRACT

class AIAdmissionError(RuntimeError):
    pass

@dataclass(frozen=True)
class Admission:
    request_id: str
    policy: dict
    duplicate: bool = False
    previous_status: str | None = None


def _keys(user_id: str, task: str, day: str, month: str):
    return [(f'user:{user_id}:day:{day}',user_id,day),
            (f'global:day:{day}',None,day),(f'global:month:{month}',None,month),
            (f'user:{user_id}:action:{task}:{month}',user_id,month)]

class AIRepository(RepositoryBase):
    @contextmanager
    def _locked(self):
        with self.session() as s:
            try:
                if self.engine.dialect.name == 'sqlite':
                    s.execute(text('BEGIN IMMEDIATE'))
                statement=select(AIRuntimePolicy).where(AIRuntimePolicy.id==1)
                if self.engine.dialect.name=='postgresql':
                    s.execute(text("SET LOCAL lock_timeout = '5s'"))
                    statement=statement.with_for_update()
                row=s.scalar(statement)
                if row is None: raise AIAdmissionError('policy_unavailable')
                policy=validate_policy(json.loads(row.policy_json))
                yield s,row,policy
                s.commit()
            except BaseException:
                s.rollback()
                raise

    def read_policy(self) -> tuple[int,dict]:
        with self.session() as s:
            row=s.get(AIRuntimePolicy,1)
            if row is None: raise AIAdmissionError('policy_unavailable')
            return row.version,validate_policy(json.loads(row.policy_json))

    def update_policy(self,changes: dict,*,expected_version: int,now: int) -> tuple[int,dict]:
        with self._locked() as (s,row,p):
            if row.version!=expected_version: raise AIAdmissionError('policy_version_conflict')
            merged=validate_policy({**p,**changes})
            if merged!=p:
                row.version+=1;row.policy_json=json.dumps(merged,sort_keys=True);row.updated_at=now
            return row.version,merged

    @staticmethod
    def _bucket(s,key,user,period):
        row=s.get(AIBudgetBucket,key)
        if row is None:
            row=AIBudgetBucket(id=key,user_id=user,period=period,spent_microrub=0,requests=0,successes=0)
            s.add(row);s.flush()
        return row

    @staticmethod
    def _recover(s,now):
        stale=s.scalars(select(AIUsageEvent).where(AIUsageEvent.status=='reserved',AIUsageEvent.lease_expires_at<=now)).all()
        for e in stale:
            e.status='unknown';e.reason='worker_interrupted';e.cost_uncertain=True;e.updated_at=now
            # Full reservation was already included in all technical buckets.
        s.execute(delete(AIRequestLease).where(AIRequestLease.expires_at<=now))
        return len(stale)

    def recover(self,*,now:int) -> int:
        with self._locked() as (s,row,p): return self._recover(s,now)

    def admit(self,*,user_id:str,key_hash:str,request_hash:str,fixture:dict,now:int,input_estimate:int | None=None,
              prompt_version:str=CONTRACT) -> Admission:
        # A new general writer records its actual contract, not the accepted
        # benchmark's version. This is metadata, never an admission permission.
        if prompt_version not in {CONTRACT, 'cover-letter-draft-v1'}:
            raise AIAdmissionError('invalid_contract')
        day=datetime.fromtimestamp(now,timezone.utc).date().isoformat();month=day[:7]
        with self._locked() as (s,control,p):
            self._recover(s,now)
            previous=s.scalar(select(AIUsageEvent).where(AIUsageEvent.user_id==user_id,AIUsageEvent.idempotency_hash==key_hash))
            if previous is not None:
                if previous.request_hash!=request_hash: raise AIAdmissionError('idempotency_conflict')
                return Admission(previous.id,p,True,previous.status)
            if not p['enabled'] or p['kill_switch']: raise AIAdmissionError('runtime_not_activated')
            if input_estimate is not None and (type(input_estimate) is not int or not 0 <= input_estimate <= p['max_input_tokens']):
                raise AIAdmissionError('input_limit')
            age=(date.fromisoformat(day)-date.fromisoformat(p['pricing_checked_on'])).days
            if not 0<=age<p['pricing_valid_days']: raise AIAdmissionError('pricing_stale')
            user=s.get(User,user_id)
            if user is None or user.status!='active' or user.email_verified_at is None:
                raise AIAdmissionError('verified_account_required')
            active_user=s.scalar(select(func.count()).select_from(AIUsageEvent).where(AIUsageEvent.user_id==user_id,AIUsageEvent.status=='reserved')) or 0
            active_global=s.scalar(select(func.count()).select_from(AIRequestLease).where(AIRequestLease.expires_at>now)) or 0
            if active_user>=p['max_user_concurrency'] or active_global>=p['max_global_concurrency']:
                raise AIAdmissionError('concurrency_limit')
            state=s.get(AIProviderState,PROVIDER)
            if state is None: raise AIAdmissionError('policy_unavailable')
            if state.open_until>now or state.probe_until>now: raise AIAdmissionError('provider_circuit_open')
            worst=cost_microrub(p['max_input_tokens'],p['max_output_tokens'],p)*p['max_attempts']
            buckets=[self._bucket(s,*k) for k in _keys(user_id,fixture['task'],day,month)]
            for b,limit in zip(buckets[:3],(p['user_daily_budget_microrub'],p['global_daily_budget_microrub'],p['global_monthly_budget_microrub'])):
                if b.spent_microrub+worst>limit: raise AIAdmissionError('budget_exhausted')
            if buckets[0].requests>=p['user_daily_requests'] or buckets[1].requests>=p['global_daily_requests']:
                raise AIAdmissionError('request_limit')
            if p['commercial_enforcement_enabled']:
                plan=s.get(AIUserPlan,user_id)
                entitlement=s.get(AIPlanEntitlement,(plan.plan_key,fixture['task'])) if plan else None
                if not entitlement or not entitlement.enabled: raise AIAdmissionError('entitlement_unavailable')
                in_flight=s.scalar(select(func.count()).select_from(AIUsageEvent).where(AIUsageEvent.user_id==user_id,AIUsageEvent.task==fixture['task'],AIUsageEvent.month==month,AIUsageEvent.status=='reserved',AIUsageEvent.commercial_reserved.is_(True))) or 0
                if buckets[3].successes+in_flight>=entitlement.monthly_limit: raise AIAdmissionError('commercial_quota_exhausted')
            request_id=str(uuid4())
            for b in buckets[:3]: b.spent_microrub+=worst;b.requests+=1
            s.add(AIUsageEvent(id=request_id,user_id=user_id,idempotency_hash=key_hash,request_hash=request_hash,
                task=fixture['task'],language=fixture['language'],fixture_id=fixture['case_id'],prompt_version=prompt_version,
                policy_version=control.version,input_rate=p['input_microrub_per_token'],output_rate=p['output_microrub_per_token'],
                day=day,month=month,status='reserved',reason='admitted',reserved_microrub=worst,charged_microrub=worst,
                cost_uncertain=True,attempts=0,input_tokens=0,output_tokens=0,commercial_reserved=p['commercial_enforcement_enabled'],commercial_action_consumed=False,
                created_at=now,updated_at=now,lease_expires_at=now+p['lease_seconds']))
            s.add(AIRequestLease(id=request_id,expires_at=now+p['lease_seconds']))
            if state.open_until:
                state.probe_request_id=request_id;state.probe_until=now+p['lease_seconds']
            return Admission(request_id,p)

    def before_attempt(self,request_id:str,*,now:int) -> bool:
        with self._locked() as (s,control,p):
            e=s.get(AIUsageEvent,request_id)
            if e is None or e.status!='reserved' or e.lease_expires_at<=now: return False
            if not p['enabled'] or p['kill_switch']: return False
            e.attempts+=1;e.updated_at=now
            return True

    def settle(self,request_id:str,*,status:str,reason:str,cost:int,uncertain:bool,
               input_tokens:int,output_tokens:int,provider_failed:bool,now:int,
               on_success=None) -> bool:
        if status not in {'succeeded','failed','unknown'} or type(cost) is not int or cost<0:
            raise ValueError('Invalid settlement')
        with self._locked() as (s,control,p):
            e=s.get(AIUsageEvent,request_id)
            s.execute(delete(AIRequestLease).where(AIRequestLease.id==request_id))
            if e is None:
                # Deleted owner: retain global reservation conservatively, never return output.
                return False
            if e.status!='reserved':return False
            if status=='succeeded' and on_success is not None:
                if not p['enabled'] or p['kill_switch'] or e.lease_expires_at<=now:
                    raise AIAdmissionError('result_not_delivered')
                # The callback may insert a feature-owned proposal in this same
                # transaction. A failed insertion cannot consume a success quota.
                on_success(s,e)
            buckets=[s.get(AIBudgetBucket,k[0]) for k in _keys(e.user_id,e.task,e.day,e.month)]
            if any(b is None for b in buckets): raise AIAdmissionError('ledger_integrity_failure')
            delta=cost-e.charged_microrub
            for b in buckets[:3]: b.spent_microrub+=delta
            # The success count is a future allowance counter, NOT a payment charge.
            if status=='succeeded':
                for b in buckets[:3]:b.successes+=1
                if e.commercial_reserved:buckets[3].successes+=1
            e.status=status;e.reason=reason;e.charged_microrub=cost;e.cost_uncertain=uncertain
            e.input_tokens=input_tokens;e.output_tokens=output_tokens;e.updated_at=now
            e.commercial_action_consumed=(status=='succeeded' and e.commercial_reserved)
            state=s.get(AIProviderState,PROVIDER)
            probe_matches=state.probe_request_id==request_id
            if probe_matches:state.probe_request_id=None;state.probe_until=0
            if provider_failed:
                state.failures+=1
                if state.failures>=p['circuit_failures'] or probe_matches:state.open_until=now+p['circuit_cooldown_seconds']
            elif status=='succeeded' and (not state.open_until or probe_matches):
                # A late success from a pre-open request must not close an opened circuit.
                state.failures=0;state.open_until=0
            if cost>e.reserved_microrub or reason=='usage_limit_overrun':
                # Reconcile actual overrun but prevent further admissions until operator review.
                p['kill_switch']=True;control.policy_json=json.dumps(p,sort_keys=True);control.version+=1;control.updated_at=now
            return True

    def cleanup(self,*,now:int,limit:int=500) -> dict[str,int]:
        if type(limit)is not int or not 1<=limit<=5000:raise ValueError('Invalid cleanup batch')
        with self._locked() as (s,row,p):
            recovered=self._recover(s,now)
            cutoff=now-p['metadata_retention_days']*86400
            ids=s.scalars(select(AIUsageEvent.id).where(AIUsageEvent.status!='reserved',AIUsageEvent.updated_at<cutoff).order_by(AIUsageEvent.updated_at).limit(limit)).all()
            if ids:s.execute(delete(AIUsageEvent).where(AIUsageEvent.id.in_(ids)))
            # Never erase the active calendar month's budgets while it still enforces a cap.
            month=datetime.fromtimestamp(now,timezone.utc).strftime('%Y-%m')
            bucket_cutoff=min(datetime.fromtimestamp(cutoff,timezone.utc).strftime('%Y-%m'),month)
            old=s.scalars(select(AIBudgetBucket.id).where(AIBudgetBucket.period<bucket_cutoff).limit(limit)).all()
            if old:s.execute(delete(AIBudgetBucket).where(AIBudgetBucket.id.in_(old)))
            return {'recovered':recovered,'events_deleted':len(ids),'buckets_deleted':len(old)}

    def owner_usage(self,user_id:str,*,limit:int=500) -> list[dict]:
        with self.session() as s:
            rows=s.scalars(select(AIUsageEvent).where(AIUsageEvent.user_id==user_id).order_by(AIUsageEvent.created_at.desc()).limit(limit)).all()
            return [public_usage(e) for e in rows]

def public_usage(e:AIUsageEvent) -> dict:
    return {key:getattr(e,key) for key in ('id','task','language','status','reason','created_at','updated_at',
        'input_tokens','output_tokens','charged_microrub','cost_uncertain','commercial_action_consumed')}
