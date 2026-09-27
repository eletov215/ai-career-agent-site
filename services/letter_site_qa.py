"""Admin-only, fixed-source AI-005 browser QA using production letter services.

Never imports a test transport, changes production policy, or reads actor content.
Two persistent non-login data owners per administrator (RU/EN) reuse the shared
ledger. Preparing another case never resets budgets. Each letter has one signed,
10-minute generation intention; reissuing a preview cannot renew that window.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from uuid import UUID

from sqlalchemy import func, select

from domain.cover_letter import LetterError, MAX_LETTERS, canonical, digest, identifier, options
from domain.saved_vacancy import SNAPSHOT_VERSION, canonical_json, fingerprint
from models import User, CareerProfile, CareerProfileVersion, SavedVacancy
from models.saved_vacancy import SavedVacancySource
from models.cover_letter import CoverLetter
from services.admin_access import is_search_admin
from services.ai.letter_admission import SyntheticLetterAdmission, synthetic_cases
from services.ai.letter_runtime import LetterRuntime
from services.ai.service import AIService
from services.cover_letter_ai import CoverLetterGenerator, TICKET_SECONDS, _encode
from services.cover_letters import CoverLetterService
from services.saved_vacancy_snapshot import build_snapshot

MARKER = 'AI-005 SITE QA / non-login synthetic owner v1'


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
        self.letters = CoverLetterService(self.repository, signing_key=settings.flask_secret_key, clock=clock)
        self.ai = AIService(storage.ai, settings.ai, fingerprint_key=settings.flask_secret_key,
                            provider=provider, clock=clock)
        self.runtime = LetterRuntime(self.ai, clock=clock)

    def mac(self, value):
        return hmac.new(self._key, canonical(value).encode(), hashlib.sha256).hexdigest()

    def _id(self, *parts):
        return str(UUID(self.mac(['site-qa-id-v1', *parts])[:32], version=4))

    def owner_id(self, actor_id, language):
        identifier(actor_id)
        if language not in ('ru', 'en'):
            raise LetterError('invalid_request')
        return self._id('owner', actor_id, language)

    def authorize(self, actor_id, *, session=None, lock=False):
        identifier(actor_id)
        if not self.enabled:
            raise LetterError('not_found')
        if session is None:
            with self.repository.session() as s:
                return self.authorize(actor_id, session=s, lock=lock)
        statement = select(User).where(User.id == actor_id)
        actor = session.scalar(statement.with_for_update() if lock else statement)
        if not is_search_admin(actor, self.settings):
            raise LetterError('not_found')

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

    @staticmethod
    def _internal_owner(session, owner_id):
        row = session.get(User, owner_id)
        if (row is None or row.display_name != MARKER or row.status != 'active'
                or row.email_verified_at is None or row.email is not None
                or row.normalized_email is not None or row.password_hash is not None):
            raise LetterError('storage_integrity')
        return row

    @staticmethod
    def _fixed_source(source, language):
        case = synthetic_cases()[language]
        if source.get('facts') != case['candidate_facts'] or source.get('vacancy') != case['vacancy']:
            raise LetterError('invalid_source')

    def _seed(self, session, owner_id, language, now):
        """Atomically create immutable fixtures, never repair a tampered workspace."""
        case = synthetic_cases()[language]
        saved_id = self._id('vacancy', owner_id)
        if session.get(User, owner_id) is not None:
            self._internal_owner(session, owner_id)
            return saved_id
        # No email, password, session, OAuth identity, token or consent is issued.
        session.add(User(id=owner_id, display_name=MARKER, status='active',
                         email_verified_at=now, created_at=now, updated_at=now))
        session.flush()
        profile = {'summary': case['candidate_facts'][0]['text']}
        profile_id = self._id('profile', owner_id)
        profile_hash = digest(profile)
        session.add(CareerProfile(id=profile_id, user_id=owner_id, schema_version=1, version=1,
            summary=profile['summary'], content_hash=profile_hash, completion_percent=0,
            confirmed_at=now, created_at=now, updated_at=now))
        session.flush()
        session.add(CareerProfileVersion(id=self._id('profile-version', owner_id), profile_id=profile_id,
            schema_version=1, version=1, snapshot_json=canonical(profile), content_hash=profile_hash,
            changed_sections_json='["summary"]', source_kind='manual',
            provenance_json='{"scope":"synthetic_only","package":"AI-005-SITE-QA"}', created_at=now))
        snapshot = build_snapshot({'source': 'hh', 'external_id': 'ai005-isolated-synthetic',
            'url': 'https://hh.ru/vacancy/ai005-isolated-synthetic', **case['vacancy'],
            'location': '', 'source_status': 'active', 'currency': 'RUB'})
        session.add(SavedVacancy(id=saved_id, user_id=owner_id, snapshot_json=canonical_json(snapshot),
            snapshot_hash=fingerprint(snapshot), snapshot_version=SNAPSHOT_VERSION,
            title=snapshot['title'], company=snapshot['company'], location=snapshot['location'],
            search_text='synthetic site qa', note='', revision=1, created_at=now, updated_at=now))
        session.flush()
        for source in snapshot['source_records']:
            session.add(SavedVacancySource(id=self._id('source', owner_id, source['identity_hash']),
                saved_vacancy_id=saved_id, user_id=owner_id, source=source['source'],
                external_id=source['external_id'], identity_hash=source['identity_hash'],
                url=source['url'], created_at=now))
        session.flush()
        return saved_id

    def prepare(self, actor_id, token, language, length, tone):
        self.authorize(actor_id)
        intention = self._intention(actor_id, token)
        opts = options(language, length, tone)
        owner_id = self.owner_id(actor_id, language)
        letter_id = self._id('letter', actor_id, intention['nonce'])
        request_hash = self.mac(['prepare', actor_id, intention['nonce'], opts])
        now = int(self.clock())
        # The actor lock serializes creation across BOTH language workspaces.
        with self.repository._write(actor_id) as session:
            self.authorize(actor_id, session=session)
            old = session.get(CoverLetter, letter_id)
            if old is not None:
                if old.user_id != owner_id or old.request_hash != request_hash:
                    raise LetterError('idempotency_conflict')
                return letter_id
            saved_id = self._seed(session, owner_id, language, now)
            source = self.repository._source(session, owner_id, saved_id)
            self._fixed_source(source, language)
            count = session.scalar(select(func.count()).select_from(CoverLetter).where(CoverLetter.user_id == owner_id))
            if count >= MAX_LETTERS:
                raise LetterError('history_limit')
            value = {'subject': '', 'body': '', **opts}
            session.add(CoverLetter(id=letter_id, user_id=owner_id, saved_vacancy_id=saved_id,
                operation_hash=self.mac(['prepare-operation', actor_id, intention['nonce']]),
                request_hash=request_hash, source_json=canonical(source), source_hash=digest(source),
                content_json=canonical(value), content_hash=digest(value), revision=1, last_version=0,
                created_at=now, updated_at=now))
        return letter_id

    def record(self, actor_id, letter_id):
        self.authorize(actor_id)
        identifier(letter_id)
        owners = {self.owner_id(actor_id, lang): lang for lang in ('ru', 'en')}
        with self.repository.session() as session:
            owner_id = session.scalar(select(CoverLetter.user_id).where(
                CoverLetter.id == letter_id, CoverLetter.user_id.in_(owners)))
            if owner_id is None:
                raise LetterError('not_found')
            self._internal_owner(session, owner_id)
        result = self.letters.get(owner_id, letter_id)
        self._fixed_source(result['source'], owners[owner_id])
        return owner_id, owners[owner_id], result

    def recent(self, actor_id):
        self.authorize(actor_id)
        owners = [self.owner_id(actor_id, lang) for lang in ('ru', 'en')]
        with self.repository.session() as session:
            rows = session.execute(select(CoverLetter.id, CoverLetter.created_at).where(
                CoverLetter.user_id.in_(owners)).order_by(CoverLetter.created_at.desc(), CoverLetter.id).limit(20)).all()
        return [{'id': row.id, 'created_at': row.created_at} for row in rows]

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
