#!/usr/bin/env python3
"""Operator-only technical controls, versioned atomically. No public admin endpoint."""
from pathlib import Path
import argparse,json,sys,time
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from config import load_database_url
from database import create_database
from repositories.ai import AIRepository
from services.ai.policy import rub_to_micro

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('show','set','recover','cleanup'))
    p.add_argument('--expected-version',type=int)
    p.add_argument('--user-daily-budget-rub')
    p.add_argument('--global-daily-budget-rub')
    p.add_argument('--global-monthly-budget-rub')
    p.add_argument('--user-daily-requests',type=int)
    p.add_argument('--global-daily-requests',type=int)
    p.add_argument('--max-global-concurrency',type=int)
    p.add_argument('--max-user-concurrency',type=int)
    p.add_argument('--kill-switch',choices=('on','off'))
    p.add_argument('--synthetic-enabled',choices=('on','off'))
    p.add_argument('--pricing-checked-on')
    p.add_argument('--input-microrub-per-token',type=int)
    p.add_argument('--output-microrub-per-token',type=int)
    args=p.parse_args(argv)
    runtime=None
    try:
        url,_=load_database_url();runtime=create_database(url);repo=AIRepository(runtime);now=int(time.time())
        if args.command=='show':
            version,policy=repo.read_policy();result={'version':version,'policy':policy,'scope':'technical_only_real_data_blocked'}
        elif args.command=='set':
            if args.expected_version is None:p.error('set requires --expected-version from show')
            changes={}
            for key in ('user_daily_budget_rub','global_daily_budget_rub','global_monthly_budget_rub'):
                v=getattr(args,key)
                if v is not None:changes[key.replace('_rub','_microrub')]=rub_to_micro(v)
            for key in ('user_daily_requests','global_daily_requests','max_global_concurrency','max_user_concurrency','pricing_checked_on','input_microrub_per_token','output_microrub_per_token'):
                v=getattr(args,key)
                if v is not None:changes[key]=v
            if args.kill_switch is not None:changes['kill_switch']=args.kill_switch=='on'
            if args.synthetic_enabled is not None:changes['enabled']=args.synthetic_enabled=='on'
            if not changes:p.error('No control change was supplied')
            version,policy=repo.update_policy(changes,expected_version=args.expected_version,now=now)
            result={'version':version,'policy':policy,'scope':'technical_only_real_data_blocked'}
        elif args.command=='recover':result={'recovered':repo.recover(now=now)}
        else:result=repo.cleanup(now=now)
        print(json.dumps({'ok':True,**result},indent=2));return 0
    except Exception:
        # Database exceptions may embed credentials; do not print them.
        print(json.dumps({'ok':False,'error':'ai_control_failed','hint':'Check database readiness, values and expected version locally.'}));return 1
    finally:
        if runtime:runtime.dispose()

if __name__=='__main__':raise SystemExit(main())
