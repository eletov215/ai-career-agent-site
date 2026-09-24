"""Admin-only AI-005 SITE QA orchestration using fixed synthetic fixtures."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

from domain.cover_letter import canonical, content, identifier, options
from services.ai.letter_admission import SyntheticLetterAdmission, synthetic_cases
from services.cover_letter_ai import CoverLetterGenerator


class AliceSiteQAService:
    """Prepare synthetic workspaces and reuse the production Alice runtime."""

    def __init__(self, repository, runtime, *, signing_key: str, clock=time.time):
        if not signing_key:
            raise ValueError("Signing key required")
        self.repository=repository
        self.runtime=runtime
        self._key=signing_key.encode()
        self._signing_key=signing_key
        self.clock=clock

    def _hash(self,value):
        return hmac.new(self._key,canonical(value).encode(),hashlib.sha256).hexdigest()

    def _generator(self,user_id):
        return CoverLetterGenerator(
            self.repository,self.runtime,signing_key=self._signing_key,
            admission=SyntheticLetterAdmission(user_id),clock=self.clock)

    def prepare(self,user_id,language,length,tone):
        user_id=identifier(user_id)
        opts=options(language,length,tone)
        cases=synthetic_cases()
        case=cases.get(opts['language'])
        if case is None:
            raise ValueError("Unsupported synthetic fixture")
        operation=secrets.token_urlsafe(24)
        operation_hash=self._hash(['ai005-site-qa-workspace',user_id,operation])
        request_hash=self._hash(['ai005-site-qa-workspace-v1',user_id,operation,opts])
        initial=content('', '', opts['language'], opts['length'], opts['tone'])
        row=self.repository.create_synthetic_qa(
            user_id,opts['language'],initial,operation_hash,request_hash,now=int(self.clock()))
        fact_ids=[fact['id'] for fact in case['candidate_facts']]
        preview=self._generator(user_id).preview(
            user_id,row['id'],row['revision'],opts['language'],opts['length'],opts['tone'],fact_ids)
        return {'letter':row,'preview':preview,'scope':'synthetic_only'}

    def generate(self,user_id,letter_id,review_token):
        # One ordinary button is the explicit user action. Technical confirmation
        # stays server-side; idempotency/ledger controls remain unchanged.
        return self._generator(identifier(user_id)).generate(
            user_id,identifier(letter_id),review_token,confirmed=True)
