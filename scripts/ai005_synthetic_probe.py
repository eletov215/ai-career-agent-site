#!/usr/bin/env python3
"""AI-005 isolated synthetic probe. Default: preview only, zero network.

Never imports app.py, accepts arbitrary input or connects to DATABASE_URL. A paid
invocation requires --allow-billable-alice plus the existing provider gates. It
makes at most one dispatch in a fresh disposable database. Re-running a paid
command is a NEW paid operation; it is not a retry of the previous command.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from database import create_database,upgrade_database
from domain.cover_letter import SOURCE_VERSION
from domain.saved_vacancy import fingerprint,canonical_json
from models import User,SearchSnapshot,SearchSnapshotItem
from repositories.ai import AIRepository
from repositories.cover_letters import CoverLetterRepository
from repositories.profiles import CareerProfileRepository
from repositories.saved_vacancies import SavedVacancyRepository
from services.ai.service import AIService
from services.ai.settings import AISettings
from services.ai.provider import YandexAliceProvider
from services.ai.letter_contract import build_writing_contract
from services.ai.letter_admission import synthetic_cases,SyntheticLetterAdmission
from services.ai.letter_runtime import LetterRuntime
from services.cover_letter_ai import CoverLetterGenerator
from services.cover_letters import CoverLetterService
from services.saved_vacancies import SavedVacancyService
from services.profile import CareerProfileService


def private_json(path:Path,value):
    # Exclusive create prevents overwriting a previous paid result.
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)


def seed(db,case,now):
    """Only bundled synthetic strings go through ordinary profile/save services."""
    uid,sid=str(uuid4()),str(uuid4());key=secrets.token_hex(32)
    raw={'source':'hh','external_id':'ai005-isolated-synthetic',
         'url':'https://hh.ru/vacancy/ai005-isolated-synthetic',**case['vacancy'],'location':'',
         'source_status':'active','currency':'RUB'}
    stable=fingerprint(raw)[:40]
    with db.session() as s,s.begin():
        s.add(User(id=uid,status='active',email_verified_at=now,created_at=now,updated_at=now))
        s.add(SearchSnapshot(id=sid,query_fingerprint='0'*64,selected_sources_json='["hh"]',
            sort_code='date',page_size=20,committed_count=1,known_unique_total=1,
            created_at=now,updated_at=now,expires_at=now+3600))
        s.flush()
        s.add(SearchSnapshotItem(snapshot_id=sid,ordinal=0,stable_key=stable,source_keys_json='[]',
            payload_json=canonical_json(raw),created_at=now,updated_at=now))
    saved_service=SavedVacancyService(SavedVacancyRepository(db),signing_key=key)
    reference=saved_service.controls(uid,sid,[{**raw,'_snapshot_item_key':stable}])[0]['reference']
    saved=saved_service.save(uid,reference,now=now)
    CareerProfileService(CareerProfileRepository(db)).save(user_id=uid,
        payload={'summary':case['candidate_facts'][0]['text']},expected_version=0)
    svc=CoverLetterService(CoverLetterRepository(db),signing_key=key)
    source=svc.source(uid,saved['id'])
    return uid,svc,saved['id'],source,key


def execute(output:Path,*,language='ru',length='short',tone='professional',allow_billable=False,
            environ=None,provider_factory=YandexAliceProvider):
    env=dict(os.environ if environ is None else environ)
    # Even with an explicit local DB below, refuse a production-looking shell.
    if any(env.get(k) for k in ('DATABASE_URL','POSTGRES_TEST_URL','RESTORE_DATABASE_URL','RENDER','RENDER_SERVICE_ID')):
        raise ValueError('Use an isolated shell without database or Render environment variables')
    if allow_billable and env.get('APP_ENV','').lower() in ('test','production','prod'):
        raise ValueError('Use an isolated development environment, never test/production')
    output=output.expanduser().resolve()
    if output==ROOT or ROOT in output.parents:
        raise ValueError('Reports must be outside the repository')
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    case=synthetic_cases()[language]
    contract=build_writing_contract({'schema':SOURCE_VERSION,'facts':case['candidate_facts'],'vacancy':case['vacancy']},
        [case['candidate_facts'][0]['id']],language,length,tone)
    private_json(output/'request-preview.json',{'scope':'synthetic_only','recipient':'Yandex AI Studio / Alice AI LLM',
        'payload':contract.projection,'payload_hash':contract.payload_hash,'contract':contract.version,
        'estimated_input_upper_bound':contract.input_estimate,'semantic_quality':'NOT RUN'})
    if not allow_billable:
        report={'scope':'synthetic_only','mode':'preview_only','network_calls':0,'live_quality':'NOT RUN'}
        private_json(output/'report.json',report);return report
    now=int(time.time());settings=AISettings.from_environ(env)
    reason=settings.gate(now)
    if reason:raise ValueError('Provider gates are not satisfied: '+reason)
    # Fresh explicit SQLite URL only; no real account/database ID is accepted.
    with tempfile.TemporaryDirectory(prefix='aca-ai005-synthetic-') as temp:
        url='sqlite:///'+str(Path(temp)/'probe.db');upgrade_database(url);db=create_database(url)
        try:
            uid,svc,saved_id,source,key=seed(db,case,now)
            letter=svc.create(uid,saved_id,source['source_hash'],secrets.token_urlsafe(24),language,length,tone,confirmed=True)
            ledger=AIRepository(db);version,policy=ledger.read_policy()
            # Does not refresh price timestamps or qualify the new prompt. Only
            # this temporary technical ledger is enabled; production is untouched.
            ledger.update_policy({'enabled':True,'kill_switch':False},expected_version=version,now=now)
            service=AIService(ledger,settings,fingerprint_key=key,provider=provider_factory(settings))
            generator=CoverLetterGenerator(svc.repository,LetterRuntime(service),signing_key=key,
                admission=SyntheticLetterAdmission(uid))
            preview=generator.preview(uid,letter['id'],letter['revision'],language,length,tone,[case['candidate_facts'][0]['id']])
            result=generator.generate(uid,letter['id'],preview['review_token'],confirmed=True)
            with db.session() as s:
                from sqlalchemy import select
                from models.ai import AIUsageEvent
                rows=list(s.scalars(select(AIUsageEvent)))
                usage=[{'status':e.status,'reason':e.reason,'attempts':e.attempts,
                    'cost_microrub':e.charged_microrub,'cost_uncertain':e.cost_uncertain,
                    'input_tokens':e.input_tokens,'output_tokens':e.output_tokens} for e in rows]
            report={'scope':'synthetic_only','mode':'paid_probe','status':result['status'],
                    'dispatches':sum(e['attempts'] for e in usage),'usage':usage,
                    'contract':contract.version,'live_quality':'REQUIRES_HUMAN_REVIEW',
                    'real_data_authorized':False,'commercial_readiness':False,
                    'price_snapshot':{k:policy[k] for k in ('pricing_checked_on','pricing_valid_days','input_microrub_per_token','output_microrub_per_token')}}
            if result['status']=='proposal':
                p=result['proposal']
                private_json(output/'proposal-for-review.json',{'origin':p['origin'],'content':p['content'],'evidence':p['evidence']})
            private_json(output/'report.json',report)
            return report
        finally:db.dispose()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--language',choices=('ru','en'),default='ru')
    parser.add_argument('--length',choices=('short','full'),default='short')
    parser.add_argument('--tone',choices=('professional','friendly'),default='professional')
    parser.add_argument('--allow-billable-alice',action='store_true')
    args=parser.parse_args(argv)
    try:
        result=execute(args.output_dir,language=args.language,length=args.length,tone=args.tone,
                       allow_billable=args.allow_billable_alice)
    except Exception:
        # Never echo credentials, raw provider errors or private filesystem input.
        print(json.dumps({'ok':False,'reason':'probe_failed_check_isolation_and_gates'}));return 1
    print(json.dumps({'ok':result.get('status','preview_only') in ('preview_only','proposal'),
                      'mode':result['mode'],'scope':'synthetic_only','live_quality':result['live_quality']}))
    return 0 if result.get('status','preview_only') in ('preview_only','proposal') else 1

if __name__=='__main__':raise SystemExit(main())
