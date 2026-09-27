"""Persistent synthetic SITE QA data access; no provider I/O in transactions."""
from __future__ import annotations

import hashlib
import hmac
from uuid import UUID

from sqlalchemy import func, select

from domain.cover_letter import LetterError, MAX_LETTERS, canonical, digest, identifier
from domain.saved_vacancy import SNAPSHOT_VERSION, canonical_json, fingerprint
from models import User, CareerProfile, CareerProfileVersion, SavedVacancy
from models.saved_vacancy import SavedVacancySource
from models.cover_letter import CoverLetter
from services.admin_access import is_search_admin
from services.ai.letter_admission import synthetic_cases
from services.saved_vacancy_snapshot import build_snapshot

MARKER = 'AI-005 SITE QA / non-login synthetic owner v1'


class LetterSiteQARepository:
    def __init__(self, letter_repository, settings):
        self.repository = letter_repository
        self.settings = settings
        self._key = settings.flask_secret_key.encode()
        if not self._key:
            raise ValueError('Signing key required')

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
        if session is None:
            with self.repository.session() as s:
                return self.authorize(actor_id, session=s, lock=lock)
        statement = select(User).where(User.id == actor_id)
        actor = session.scalar(statement.with_for_update() if lock else statement)
        if not is_search_admin(actor, self.settings):
            raise LetterError('not_found')

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

    def prepare(self, actor_id, nonce, opts, *, now):
        self.authorize(actor_id)
        language = opts['language']
        owner_id = self.owner_id(actor_id, language)
        letter_id = self._id('letter', actor_id, nonce)
        request_hash = self.mac(['prepare', actor_id, nonce, opts])
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
                operation_hash=self.mac(['prepare-operation', actor_id, nonce]),
                request_hash=request_hash, source_json=canonical(source), source_hash=digest(source),
                content_json=canonical(value), content_hash=digest(value), revision=1, last_version=0,
                created_at=now, updated_at=now))
        return letter_id

    def owned_owner(self, actor_id, letter_id):
        self.authorize(actor_id)
        identifier(letter_id)
        owners = {self.owner_id(actor_id, lang): lang for lang in ('ru', 'en')}
        with self.repository.session() as session:
            owner_id = session.scalar(select(CoverLetter.user_id).where(
                CoverLetter.id == letter_id, CoverLetter.user_id.in_(owners)))
            if owner_id is None:
                raise LetterError('not_found')
            self._internal_owner(session, owner_id)
        return owner_id, owners[owner_id]

    def recent(self, actor_id):
        self.authorize(actor_id)
        owners = [self.owner_id(actor_id, lang) for lang in ('ru', 'en')]
        with self.repository.session() as session:
            rows = session.execute(select(CoverLetter.id, CoverLetter.created_at).where(
                CoverLetter.user_id.in_(owners)).order_by(CoverLetter.created_at.desc(), CoverLetter.id).limit(20)).all()
        return [{'id': row.id, 'created_at': row.created_at} for row in rows]
