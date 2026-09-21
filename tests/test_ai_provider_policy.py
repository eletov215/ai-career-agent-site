"""Offline strategy and cost regressions; no paid API or Flask import required."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.ai_provider_policy import (
    BENCH_PATH, GATES, POLICY_PATH, PolicyError, TASKS, cost_report,
    load_policy, pricing_is_current, quote_cost, route_preview, validate_policy,
)
from scripts.check_ai_provider_package import validate as validate_package, validate_canonical_status


class ProviderPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()

    def test_current_policy_is_valid(self):
        self.assertEqual([], validate_policy(self.policy))

    def test_known_routes_remain_disabled(self):
        for task in TASKS:
            for lang in ('ru','en'):
                for market in ('RU','BY'):
                    with self.subTest(task=task,lang=lang,market=market):
                        result=route_preview(self.policy,task,lang,market)
                        self.assertEqual('yandex-alice-ai-llm',result['planned_provider'])
                        self.assertIs(result['provider_call_allowed'],False)

    def test_unknown_routes_are_denied(self):
        for args in [('web_search','ru','RU'),('cover_letter','de','RU'),('cover_letter','en','US')]:
            with self.subTest(args=args):
                result=route_preview(self.policy,*args)
                self.assertIsNone(result['planned_provider'])
                self.assertFalse(result['provider_call_allowed'])

    def test_route_type_is_checked(self):
        with self.assertRaises(PolicyError):route_preview(self.policy,[],'ru','RU')

    def test_environment_cannot_enable_offline_preview(self):
        with patch.dict(os.environ,{'AI_ENABLED':'1','AI_KILL_SWITCH':'0','AI_YANDEX_API_KEY':'dummy-do-not-read'}):
            self.assertFalse(route_preview(self.policy,'cover_letter','ru','RU')['provider_call_allowed'])

    def test_no_network_is_used(self):
        with patch('socket.socket',side_effect=AssertionError('Network forbidden')):
            self.assertEqual([],validate_policy(load_policy()))
            self.assertEqual(Decimal('0.86'),quote_cost(self.policy,1000,300))

    def test_cannot_activate_runtime(self):
        self.policy['runtime_activation']=True
        self.assertTrue(validate_policy(self.policy))
        with self.assertRaises(PolicyError):route_preview(self.policy,'cover_letter','ru','RU')

    def test_owner_approval_is_explicit_and_cannot_revert(self):
        self.assertEqual('approved', self.policy['owner_approval'])
        self.policy['owner_approval']='pending'
        self.assertTrue(validate_policy(self.policy))

    def test_manual_fallback_requires_user_notice(self):
        self.assertTrue(self.policy['routing']['fallback_user_notice_required'])
        self.assertEqual('manual_without_generation', self.policy['routing']['fallback'])
        self.assertEqual(['vacancy_search','career_profile','resume_editor'], self.policy['routing']['manual_mode_features'])
        p=deepcopy(self.policy);p['routing']['fallback_user_notice_required']=False
        self.assertTrue(validate_policy(p))

    def test_commercial_tier_architecture_is_reserved_without_quota_values(self):
        c=self.policy['commercial_access']
        self.assertEqual(['free','standard'],c['launch_tiers'])
        self.assertEqual(['max'],c['reserved_tiers'])
        self.assertIsNone(c['commercial_quota_values'])
        self.assertFalse(c['tokens_user_visible'])
        self.assertEqual('feature_actions_not_tokens',c['user_visible_meter'])
        self.assertFalse(c['failed_generation_consumes_user_entitlement'])

    def test_internal_guards_are_not_commercial_entitlements(self):
        limits=self.policy['limits']
        self.assertEqual('200.00',limits['user_daily_budget_rub'])
        self.assertEqual('1000.00',limits['global_daily_budget_rub'])
        self.assertEqual('20000.00',limits['global_monthly_budget_rub'])
        self.assertIn('not_commercial_entitlement',limits['budget_status'])
        self.assertTrue(limits['provider_adapter_must_not_embed_commercial_limits'])

    def test_missing_field_rejected(self):
        del self.policy['primary']['required_headers']
        self.assertTrue(validate_policy(self.policy))

    def test_secret_values_and_unknown_fields_rejected_without_echo(self):
        secret='SENSITIVE-DO-NOT-PRINT'
        self.policy['primary']['api_key']=secret
        errors=validate_policy(self.policy)
        self.assertTrue(errors)
        self.assertNotIn(secret,' '.join(errors))

    def test_invalid_roots_rejected(self):
        for root in (None,[],True,'secret',42):
            with self.subTest(root=root):self.assertTrue(validate_policy(root))

    def test_nested_wrong_type_rejected(self):
        self.policy['primary']=[]
        self.assertTrue(validate_policy(self.policy))

    def test_no_logging_header_is_required(self):
        for value in ('true','False',False,None):
            with self.subTest(value=value):
                p=deepcopy(self.policy);p['primary']['required_headers']['x-data-logging-enabled']=value
                self.assertTrue(validate_policy(p))

    def test_contractual_wait_cannot_be_shortened(self):
        self.policy['privacy']['no_logging_min_wait_hours']=23
        self.assertTrue(validate_policy(self.policy))

    def test_optout_time_is_not_invented(self):
        self.policy['privacy']['no_logging_effective_at']='2026-09-14T00:00:00Z'
        self.assertTrue(validate_policy(self.policy))

    def test_privacy_expansion_is_rejected(self):
        for field in ('request_body_logging','response_body_logging','cross_user_cache','provider_async','provider_files','provider_tools','real_personal_data_allowed_now'):
            with self.subTest(field=field):
                p=deepcopy(self.policy);p['privacy'][field]=True
                self.assertTrue(validate_policy(p))

    def test_endpoint_injection_rejected(self):
        self.policy['primary']['endpoint']='http://127.0.0.1/credentials'
        self.assertTrue(validate_policy(self.policy))

    def test_unknown_model_or_fallback_cannot_be_enabled(self):
        for block,field,value in [('primary','provider_id','unqualified-model'),('routing','cross_provider_fallback',True),('routing','enabled_markets',['RU']),('routing','local_model','unverified-weights')]:
            with self.subTest(field=field):
                p=deepcopy(self.policy);p[block][field]=value
                self.assertTrue(validate_policy(p))

    def test_qualification_must_match_accepted_contract(self):
        self.policy['primary']['qualification_dataset']='1.3.0'
        self.assertTrue(validate_policy(self.policy))

    def test_activation_gates_cannot_be_removed(self):
        self.assertEqual(list(GATES),self.policy['activation_gates'])
        self.policy['activation_gates'].pop()
        self.assertTrue(validate_policy(self.policy))

    def test_boolean_is_not_an_integer_limit(self):
        self.policy['limits']['max_attempts']=True
        self.assertTrue(validate_policy(self.policy))

    def test_float_is_not_a_status_code(self):
        self.policy['failure_policy']['retry_http_statuses'][0]=429.0
        self.assertTrue(validate_policy(self.policy))

    def test_unsafe_retry_policy_rejected(self):
        self.policy['failure_policy']['retry_http_statuses'].append(401)
        self.assertTrue(validate_policy(self.policy))

    def test_reservation_unknown_cannot_be_zero_cost(self):
        self.policy['failure_policy']['unknown_usage']='zero'
        self.assertTrue(validate_policy(self.policy))

    def test_excessive_attempts_rejected(self):
        self.policy['limits']['max_attempts']=3
        self.assertTrue(validate_policy(self.policy))

    def test_timeout_budget_consistency(self):
        self.policy['limits']['total_timeout_seconds']=40
        self.assertTrue(validate_policy(self.policy))

    def test_budget_ordering(self):
        self.policy['limits']['user_daily_budget_rub']='1001.00'
        self.assertTrue(validate_policy(self.policy))

    def test_invalid_monetary_values(self):
        for bad in ('NaN','Infinity','-1','1e5','0',' 1 ',False,0.5):
            with self.subTest(value=bad):
                p=deepcopy(self.policy);p['pricing']['RUB']['input']=bad
                self.assertTrue(validate_policy(p))

    def test_bad_date_rejected(self):
        self.policy['pricing']['checked_on']='2026-02-30'
        self.assertTrue(validate_policy(self.policy))

    def test_future_price_check_rejected(self):
        self.policy['pricing']['checked_on']='2026-09-15'
        self.assertTrue(validate_policy(self.policy))

    def test_price_freshness_uses_explicit_date(self):
        self.assertTrue(pricing_is_current(self.policy,date(2026,9,14)))
        self.assertTrue(pricing_is_current(self.policy,date(2026,10,13)))
        self.assertFalse(pricing_is_current(self.policy,date(2026,10,14)))
        self.assertFalse(pricing_is_current(self.policy,date(2026,9,13)))

    def test_decimal_prices_and_reservations(self):
        self.assertEqual(Decimal('0.86'),quote_cost(self.policy,1000,300))
        self.assertEqual(Decimal('2.84'),quote_cost(self.policy,4000,700))
        self.assertEqual(Decimal('11.84'),quote_cost(self.policy,8000,1600,attempts=2))
        self.assertEqual(Decimal('0'),quote_cost(self.policy,0,0))

    def test_invalid_usage_rejected(self):
        for i,o in ((True,1),(1,-1),(1,0.5),(1000001,1)):
            with self.subTest(i=i,o=o):
                with self.assertRaises(PolicyError):quote_cost(self.policy,i,o)

    def test_invalid_attempt_and_currency_rejected(self):
        for value in (0,3,True):
            with self.subTest(value=value):
                with self.assertRaises(PolicyError):quote_cost(self.policy,1,1,attempts=value)
        with self.assertRaises(PolicyError):quote_cost(self.policy,1,1,currency='EUR')

    def test_full_accepted_run_repriced(self):
        evidence=json.loads(BENCH_PATH.read_text(encoding='utf-8'))
        report=cost_report(self.policy,evidence)
        self.assertEqual(Decimal('6.832'),Decimal(report['totals']['rub_including_vat']))
        self.assertEqual(5120,report['totals']['input_tokens'])
        self.assertEqual(3560,report['totals']['output_tokens'])
        self.assertEqual(Decimal('0.055999991040'),Decimal(report['totals']['usd_excluding_vat']))
        self.assertLess(abs(Decimal('0.055999992')-Decimal(report['totals']['usd_excluding_vat'])),Decimal('0.000000001'))
        self.assertFalse(report['provider_call_allowed'])
        heavy=report['heavy_user_scenario']['rub']
        self.assertEqual(Decimal('85.92'),Decimal(heavy['base_min']))
        self.assertEqual(Decimal('92.04'),Decimal(heavy['base_max']))
        self.assertEqual(Decimal('103.1040'),Decimal(heavy['with_buffer_min']))
        self.assertEqual(Decimal('110.4480'),Decimal(heavy['with_buffer_max']))
        self.assertGreater(Decimal(self.policy['limits']['user_daily_budget_rub']), Decimal(heavy['with_buffer_max']))

    def test_wrong_run_cannot_be_cost_evidence(self):
        with self.assertRaises(PolicyError):cost_report(self.policy,{'run_id':'not-the-accepted-run'})

    def test_missing_or_duplicate_cases_rejected(self):
        evidence=json.loads(BENCH_PATH.read_text(encoding='utf-8'))
        evidence['cases'][-1]=evidence['cases'][0]
        with self.assertRaises(PolicyError):cost_report(self.policy,evidence)

    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'policy.json';p.write_text('{"runtime_activation":false,"runtime_activation":true}')
            with self.assertRaises(PolicyError):load_policy(p)

    def test_malformed_and_oversize_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'policy.json'
            for text in ('{', ' '*65537):
                p.write_text(text)
                with self.assertRaises(PolicyError):load_policy(p)

    def test_missing_policy_is_safe_error(self):
        with self.assertRaises(PolicyError) as ctx:load_policy(Path('/nonexistent/secret-like-path'))
        self.assertNotIn('secret-like-path',str(ctx.exception))

    def test_current_package_passes(self):
        self.assertEqual([],validate_package())

    def test_package_evidence_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(validate_package(Path(tmp)))

    def test_active_canonical_status_is_complete_after_final_ci(self):
        root = POLICY_PATH.parents[2]
        plan = (root / 'docs/PLAN_CURRENT.md').read_text(encoding='utf-8')
        passport = (root / 'docs/PROJECT_PASSPORT.md').read_text(encoding='utf-8')
        self.assertEqual([], validate_canonical_status(plan, passport))

    def test_status_regression_and_stale_active_docs_rejected(self):
        root = POLICY_PATH.parents[2]
        plan = (root / 'docs/PLAN_CURRENT.md').read_text(encoding='utf-8')
        passport = (root / 'docs/PROJECT_PASSPORT.md').read_text(encoding='utf-8')
        start = plan.index('#### AI-PROVIDER-001')
        end = plan.index('#### AI-001', start)
        complete = "\u0412\u042b\u041f\u041e\u041b\u041d\u0415\u041d\u041e"
        pending = "\u041d\u0423\u0416\u041d\u0410 \u041f\u0420\u041e\u0412\u0415\u0420\u041a\u0410"
        for bad_plan in (
            plan[:start] + plan[start:end].replace(complete, pending) + plan[end:],
            plan.replace('PLAN_CURRENT 1.6.3;', 'PLAN_CURRENT 1.4.22;'),
            plan.replace('PROJECT_PASSPORT 2.78;', 'PROJECT_PASSPORT 2.77;'),
            plan.replace('schema20260917_0020 / main CI285 attempt2', 'schema20260917_0019 / main CI283'),
            plan.replace('| Current full package |', '| missing-package |'),
            plan.replace('AI-004 COMPLETE', 'AI-004 PENDING'),
            plan.replace('| JOB-001 |', '| missing-job |'),
            plan.replace('| AI-PROVIDER-001 |', '| deleted-provider-card |'),
            plan.replace('| AI-004 |', '| deleted-match-card |'),
            plan.replace('| LEGAL-001 | P0 до публичного AI | ОТЛОЖЕНО ДО РЕШЕНИЯ ВЛАДЕЛЬЦА |', '| LEGAL-001 | P0 до публичного AI | ЗАПЛАНИРОВАНО |'),
        ):
            with self.subTest(case=bad_plan[:30]):
                self.assertTrue(validate_canonical_status(bad_plan, passport))


if __name__ == '__main__':
    unittest.main()
