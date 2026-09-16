"""AI-004 service: pinned reference review and a closed internal provider path."""
import hashlib
import hmac
import json
import re
import time
from pathlib import Path
from uuid import UUID
from domain.ai import AIRequest
from domain.vacancy_match import FIXTURE_IDS, MATCH_VERSION, MatchError, MatchRequest
from services.ai.registry import ContractRegistry, ContractError
from services.ai.match_validation import content_hash, validate_match

ROOT = Path(__file__).resolve().parents[1]

class VacancyMatchService:
    def __init__(self, repository, runtime, *, fingerprint_key, root=ROOT, clock=time.time):
        if not fingerprint_key:
            raise ValueError('Fingerprint key required')
        self.repository = repository
        self.runtime = runtime
        self.key = fingerprint_key.encode()
        self.root = Path(root)
        self.clock = clock
        self.registry = ContractRegistry(self.root)

    def source(self, fixture_id):
        if not isinstance(fixture_id, str) or fixture_id not in FIXTURE_IDS:
            raise MatchError('invalid_source')
        fixture, schema = self.registry.load(fixture_id)
        return fixture, schema, content_hash(fixture)

    def choices(self):
        choices = []
        for fid in FIXTURE_IDS:
            fixture, _, digest = self.source(fid)
            choices.append({'fixture_id': fid, 'language': fixture['language'], 'source_hash': digest,
                            'source_facts': fixture['source_facts']})
        return choices

    def _prepare(self, request, origin):
        if not isinstance(request, MatchRequest):
            raise MatchError('invalid_request')
        try:
            if not isinstance(request.user_id, str) or str(UUID(request.user_id)) != request.user_id:
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            raise MatchError('invalid_request') from None
        if (not isinstance(request.operation_key, str) or not re.fullmatch(r'[A-Za-z0-9:_-]{8,128}', request.operation_key)
                or not isinstance(request.source_hash, str) or not re.fullmatch(r'[a-f0-9]{64}', request.source_hash)):
            raise MatchError('invalid_request')
        self.repository.check_owner(request.user_id)
        fixture, schema, digest = self.source(request.fixture_id)
        if not hmac.compare_digest(request.source_hash, digest):
            raise MatchError('stale_source')
        key = hmac.new(self.key, json.dumps(['match', request.user_id, request.operation_key],
                      separators=(',', ':')).encode(), hashlib.sha256).hexdigest()
        old = self.repository.find_operation(request.user_id, key)
        if old:
            self._check_saved(old)
            if (old['fixture_id'], old['source_hash'], old['origin'], old['policy_version']) != (request.fixture_id, digest, origin, MATCH_VERSION):
                raise MatchError('idempotency_conflict')
        else:
            self.repository.check_owner(request.user_id, room=True)
        return fixture, schema, digest, key, old

    def _save(self, request, fixture, digest, key, output, origin, usage=None):
        return self.repository.save(user_id=request.user_id, operation_hash=key, fixture=fixture,
            source_hash=digest, result=output, result_hash=content_hash(output),
            candidate_hash=content_hash([f for f in fixture['source_facts'] if f['kind'] == 'candidate']),
            vacancy_hash=content_hash([f for f in fixture['source_facts'] if f['kind'] == 'vacancy']),
            origin=origin, usage_event_id=usage, now=int(self.clock()))

    def create_reference(self, request):
        """No provider call, even if operator runtime flags happen to be enabled."""
        fixture, schema, digest, key, old = self._prepare(request, 'reference')
        if old:
            return old
        relative = f'prompts/matching/reference/{request.fixture_id}.json'
        manifest = json.loads((self.root/'services/ai/match_reference_manifest.json').read_text())
        raw = (self.root/relative).read_bytes()
        if (manifest.get('origin') != 'reference_not_live_ai'
                or hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest() != manifest['files'].get(relative)):
            raise ContractError('Invalid pinned match reference')
        result = validate_match(json.loads(raw), fixture, schema)
        return self._save(request, fixture, digest, key, result, 'reference')

    def analyze(self, request):
        """Internal synthetic-only path; deliberately NOT bound to a browser POST.

        Reuses AI-001 cost, kill switch, ledger and idempotency. Invalid
        classifications fail inside result_validator before settlement. Provider
        prose is discarded; it is never persisted or shown as a factual claim.
        """
        fixture, schema, digest, key, old = self._prepare(request, 'provider')
        if old:
            return old
        result = self.runtime.generate(AIRequest(request.user_id, key, request.fixture_id),
            result_validator=lambda output, _f, _s: validate_match(output, fixture, schema))
        if result.status != 'succeeded' or result.content is None:
            saved = self.repository.find_operation(request.user_id, key)
            if saved:
                return saved
            # Never replay a paid call to recover content lost after settlement.
            raise MatchError('provider_result_unavailable')
        validated = validate_match(result.content, fixture, schema)
        return self._save(request, fixture, digest, key, validated, 'provider', result.request_id)

    @staticmethod
    def _check_saved(row):
        try:
            facts = row['source_facts']
            valid = (content_hash(row['result']) == row['result_hash']
                     and content_hash([f for f in facts if f['kind'] == 'candidate']) == row['candidate_hash']
                     and content_hash([f for f in facts if f['kind'] == 'vacancy']) == row['vacancy_hash'])
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            raise MatchError('invalid_saved_report')

    def get(self, user_id, report_id):
        self.repository.check_owner(user_id)
        row = self.repository.get(user_id, report_id)
        if row is None:
            raise MatchError('not_found')
        self._check_saved(row)
        # A report remains a historical snapshot, not a claim about current data.
        _, _, current_hash = self.source(row['fixture_id'])
        row['stale_source'] = current_hash != row['source_hash'] or row['policy_version'] != MATCH_VERSION
        return row

    def history(self, user_id):
        self.repository.check_owner(user_id)
        rows = self.repository.list(user_id)
        for row in rows:
            self._check_saved(row)
        return rows

    def delete(self, user_id, report_id, result_hash):
        if not isinstance(result_hash, str) or not re.fullmatch(r'[a-f0-9]{64}', result_hash):
            raise MatchError('invalid_request')
        self.repository.delete(user_id, report_id, result_hash)
