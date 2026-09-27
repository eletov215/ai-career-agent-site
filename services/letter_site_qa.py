"""Admin-only, fixed-source AI-005 browser QA using production letter services.

Never imports a test transport, changes production policy, or reads actor content.
Two persistent non-login data owners per administrator (RU/EN) reuse the shared
ledger. Preparing another case never resets budgets. Each letter has one signed,
10-minute generation intention; reissuing a preview cannot renew that window.
"""
from __future__ import annotations

import base64
import hmac
import json
import secrets
import time


from domain.cover_letter import LetterError, canonical, options
from services.ai.letter_admission import SyntheticLetterAdmission, synthetic_cases
from services.ai.letter_runtime import LetterRuntime
from services.ai.service import AIService
from services.cover_letter_ai import CoverLetterGenerator, TICKET_SECONDS, _encode
from services.cover_letters import CoverLetterService
from repositories.letter_site_qa import LetterSiteQARepository


class _FixedIntentionGenerator(CoverLetterGenerator):
    """Reuse the real ticket/dispatch implementation, not a second AI pipeline."""

    def preview(self, user_id, letter_id, expected, language, length, tone, fact_ids):
        value = super().preview(user_id, letter_id, expected, language, length, tone, fact_ids)
        record = self.repository.get(user_id, letter_id)
        if record['revision'] != 1 or int(self.clock()) >= record['created_at'] + TICKET_SECONDS:
            raise LetterError('invalid_preview')
        ticket = self._ticket(value['review_token'], user_id, letter_id)
        ticket['operation'] = self._hash(['site-qa-one-dispatch-v1', user_id, letter_id])[:32]
        ticket['issued'] = record['created_at']
        ticket['expires'] = ticket['issued'] + TICKET_SECONDS
        raw = _encode(canonical(ticket).encode())
        value['review_token'] = raw + '.' + self._hash(['letter-preview', raw])
        value['expires_at'] = ticket['expires']
        return value


class _SiteQAAdmission:
    def __init__(self, qa, actor_id, owner_id, language):
        self.qa, self.actor_id, self.owner_id, self.language = qa, actor_id, owner_id, language

    def check(self, *, user_id, letter_id, contract, now, session=None):
        # Recheck the real tester before dispatch AND inside atomic delivery.
        self.qa.authorize(self.actor_id, session=session, lock=session is not None)
        if user_id != self.owner_id or user_id != self.qa.owner_id(self.actor_id, self.language):
            raise LetterError('generation_unavailable')
        case = synthetic_cases()[self.language]
        if (contract.projection['candidate_facts'] != case['candidate_facts']
                or contract.projection['vacancy'] != case['vacancy']):
            raise LetterError('invalid_source')
        SyntheticLetterAdmission(self.owner_id).check(
            user_id=user_id, letter_id=letter_id, contract=contract, now=now, session=session)
        return 'site-qa-synthetic-only-v1:' + self.qa.mac(['actor', self.actor_id])


class LetterSiteQA:
    def __init__(self, storage, settings, *, enabled=False, live_enabled=False,
                 provider=None, clock=time.time):
        self.settings, self.enabled, self.live_enabled, self.clock = settings, enabled, live_enabled, clock
        self._key = settings.flask_secret_key.encode()
        if not self._key:
            raise ValueError('Signing key required')
        self.repository = storage.cover_letters
        self.workspace = LetterSiteQARepository(self.repository, settings)
        self.letters = CoverLetterService(self.repository, signing_key=settings.flask_secret_key, clock=clock)
        self.ai = AIService(storage.ai, settings.ai, fingerprint_key=settings.flask_secret_key,
                            provider=provider, clock=clock)
        self.runtime = LetterRuntime(self.ai, clock=clock)

    def mac(self, value):
        return self.workspace.mac(value)

    def owner_id(self, actor_id, language):
        return self.workspace.owner_id(actor_id, language)

    def authorize(self, actor_id, *, session=None, lock=False):
        if not self.enabled:
            raise LetterError('not_found')
        return self.workspace.authorize(actor_id, session=session, lock=lock)

    def new_intention(self, actor_id):
        self.authorize(actor_id)
        value = {'v': 1, 'actor': actor_id, 'nonce': secrets.token_hex(16), 'issued': int(self.clock())}
        raw = _encode(canonical(value).encode())
        return raw + '.' + self.mac(['site-qa-prepare-v1', raw])

    def _intention(self, actor_id, token):
        try:
            if not isinstance(token, str) or len(token) > 2048:
                raise ValueError
            raw, signature = token.split('.')
            if not hmac.compare_digest(signature, self.mac(['site-qa-prepare-v1', raw])):
                raise ValueError
            value = json.loads(base64.b64decode(raw + '=' * (-len(raw) % 4), altchars=b'-_', validate=True))
            if (set(value) != {'v', 'actor', 'nonce', 'issued'} or value['v'] != 1
                    or value['actor'] != actor_id or type(value['issued']) is not int
                    or not value['issued'] <= int(self.clock()) < value['issued'] + TICKET_SECONDS
                    or not isinstance(value['nonce'], str) or len(value['nonce']) != 32
                    or any(c not in '0123456789abcdef' for c in value['nonce'])):
                raise ValueError
            return value
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
            raise LetterError('invalid_preview') from None

    def prepare(self, actor_id, token, language, length, tone):
        self.authorize(actor_id)
        intention = self._intention(actor_id, token)
        opts = options(language, length, tone)
        return self.workspace.prepare(actor_id, intention['nonce'], opts, now=int(self.clock()))

    def record(self, actor_id, letter_id):
        self.authorize(actor_id)
        owner_id, language = self.workspace.owned_owner(actor_id, letter_id)
        result = self.letters.get(owner_id, letter_id)
        case = synthetic_cases()[language]
        if result['source'].get('facts') != case['candidate_facts'] or result['source'].get('vacancy') != case['vacancy']:
            raise LetterError('invalid_source')
        return owner_id, language, result

    def recent(self, actor_id):
        self.authorize(actor_id)
        return self.workspace.recent(actor_id)

    def _generator(self, actor_id, owner_id, language):
        return _FixedIntentionGenerator(self.repository, self.runtime,
            signing_key=self.settings.flask_secret_key,
            admission=_SiteQAAdmission(self, actor_id, owner_id, language), clock=self.clock)

    def preview(self, actor_id, letter_id):
        owner_id, language, record = self.record(actor_id, letter_id)
        if record['revision'] != 1:
            raise LetterError('stale_write')
        return self._generator(actor_id, owner_id, language).preview(owner_id, letter_id, 1,
            **{k: record['content'][k] for k in ('language', 'length', 'tone')},
            fact_ids=[f['id'] for f in synthetic_cases()[language]['candidate_facts']])

    def generate(self, actor_id, letter_id, token):
        owner_id, language, record = self.record(actor_id, letter_id)
        if not self.live_enabled:
            raise LetterError('generation_unavailable')
        if record['revision'] != 1:
            raise LetterError('stale_write')
        # POST of the signed preview is the action. No per-call checkbox exists.
        return self._generator(actor_id, owner_id, language).generate(
            owner_id, letter_id, token, confirmed=True)

    def save(self, actor_id, letter_id, expected, subject, body, proposal_id, *, confirmed):
        owner_id, _, record = self.record(actor_id, letter_id)
        proposal = next((p for p in record['proposals'] if p['id'] == proposal_id), None)
        if (proposal_id and proposal is None) or (not proposal_id and not record['last_version']):
            raise LetterError('not_found')
        source = proposal['content'] if proposal else record['content']
        return self.letters.save(owner_id, letter_id, expected, subject, body,
            **{k: source[k] for k in ('language', 'length', 'tone')},
            confirmed=confirmed, proposal_id=proposal_id or None)

    def reject(self, actor_id, letter_id, proposal_id, expected):
        owner_id, _, _ = self.record(actor_id, letter_id)
        return self.letters.reject(owner_id, letter_id, proposal_id, expected, confirmed=True)

    def version(self, actor_id, letter_id, number):
        owner_id, _, _ = self.record(actor_id, letter_id)
        return self.letters.version(owner_id, letter_id, number)

    def export(self, actor_id, letter_id, number):
        owner_id, _, _ = self.record(actor_id, letter_id)
        return self.letters.export_text(owner_id, letter_id, number)

    def compare(self, actor_id, letter_id, left, right):
        owner_id, _, _ = self.record(actor_id, letter_id)
        return self.letters.compare(owner_id, letter_id, left, right)
