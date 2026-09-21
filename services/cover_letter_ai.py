"""Owned preview -> explicit confirmation -> Alice -> pending proposal.

A signed preview is a technical acknowledgement, NOT a legal consent record.
The default admission object is closed until LEGAL-001 and release-quality gates
are implemented. No environment flag can select the synthetic test admission.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import json
import secrets
import time

from domain.cover_letter import LetterError, canonical, check_hash, identifier, revision
from services.ai.letter_admission import ClosedLetterAdmission
from services.ai.letter_contract import build_writing_contract, RECIPIENT

TICKET_SECONDS = 600
TICKET_VERSION = 'letter-preview-v1'


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


def _decode(raw: str) -> bytes:
    return base64.b64decode(raw+'='*((-len(raw))%4),altchars=b'-_',validate=True)


class CoverLetterGenerator:
    def __init__(self, repository, runtime, *, signing_key: str, admission=None, clock=time.time):
        if not signing_key:
            raise ValueError('Signing key is required')
        self.repository, self.runtime = repository, runtime
        self._key = signing_key.encode()
        self.admission = admission if admission is not None else ClosedLetterAdmission()
        self.clock = clock

    def _hash(self, value) -> str:
        return hmac.new(self._key,canonical(value).encode(),hashlib.sha256).hexdigest()

    def _check(self,user_id,letter_id,contract,*,session=None):
        return self.admission.check(user_id=user_id,letter_id=letter_id,contract=contract,
                                    now=int(self.clock()),session=session)

    def preview(self,user_id,letter_id,expected,language,length,tone,fact_ids):
        identifier(user_id); identifier(letter_id); expected=revision(expected)
        record=self.repository.generation_snapshot(user_id,letter_id,expected)
        contract=build_writing_contract(record['source'],fact_ids,language,length,tone)
        self._check(user_id,letter_id,contract)
        now=int(self.clock())
        ticket={'v':TICKET_VERSION,'user':user_id,'letter':letter_id,'revision':expected,
                'source_hash':record['source_hash'],'payload_hash':contract.payload_hash,
                'facts':fact_ids,'options':{'language':language,'length':length,'tone':tone},
                'issued':now,'expires':now+TICKET_SECONDS,'operation':secrets.token_urlsafe(24)}
        raw=_encode(canonical(ticket).encode())
        signature=self._hash(['letter-preview',raw])
        return {'recipient':RECIPIENT,'projection':contract.projection,
                'payload_hash':contract.payload_hash,'review_token':raw+'.'+signature,
                'expires_at':ticket['expires'],'contract_version':contract.version}

    def _ticket(self,token,user_id,letter_id):
        try:
            if not isinstance(token,str) or len(token)>8192:
                raise ValueError
            raw,signature=token.split('.')
            if not hmac.compare_digest(signature,self._hash(['letter-preview',raw])):
                raise ValueError
            def unique(pairs):
                out={}
                for key,value in pairs:
                    if key in out:raise ValueError
                    out[key]=value
                return out
            ticket=json.loads(_decode(raw),object_pairs_hook=unique)
            if set(ticket)!={'v','user','letter','revision','source_hash','payload_hash','facts','options','issued','expires','operation'}:
                raise ValueError
            if ticket['v']!=TICKET_VERSION or ticket['user']!=user_id or ticket['letter']!=letter_id:
                raise ValueError
            now=int(self.clock())
            if (type(ticket['issued']) is not int or type(ticket['expires']) is not int
                    or ticket['expires']-ticket['issued']!=TICKET_SECONDS
                    or not ticket['issued']<=now<ticket['expires']):
                raise ValueError
            revision(ticket['revision']);check_hash(ticket['source_hash']);check_hash(ticket['payload_hash'])
            if not isinstance(ticket['operation'],str) or len(ticket['operation'])!=32:
                raise ValueError
            return ticket
        except (ValueError,TypeError,KeyError,UnicodeError,RecursionError):
            raise LetterError('invalid_preview') from None

    def generate(self,user_id,letter_id,review_token,*,confirmed):
        identifier(user_id);identifier(letter_id)
        # Verify ownership even while disabled, avoiding a foreign-object oracle.
        record=self.repository.get(user_id,letter_id)
        if isinstance(self.admission,ClosedLetterAdmission):
            raise LetterError('generation_unavailable')
        if confirmed is not True:
            raise LetterError('confirmation_required')
        ticket=self._ticket(review_token,user_id,letter_id)
        opts=ticket['options']
        contract=build_writing_contract(record['source'],ticket['facts'],**opts)
        if contract.payload_hash!=ticket['payload_hash'] or record['source_hash']!=ticket['source_hash']:
            raise LetterError('stale_source')
        self._check(user_id,letter_id,contract)
        operation=self._hash(['ai005-paid-operation',user_id,ticket['operation']])
        request_hash=self._hash(['ai005-paid-request',user_id,letter_id,ticket['revision'],
                                 ticket['source_hash'],contract.payload_hash,contract.version])

        def preflight():
            current=self.repository.generation_snapshot(user_id,letter_id,ticket['revision'])
            if current['source_hash']!=ticket['source_hash']:
                raise LetterError('stale_source')
            if int(self.clock())>=ticket['expires']:
                raise LetterError('invalid_preview')
            self._check(user_id,letter_id,contract)

        def store(session,event,validated):
            decision=self._check(user_id,letter_id,contract,session=session)
            # Store no opaque provider IDs/errors/raw response or review token.
            evidence={**validated['evidence'],'runtime_request_id':event.id,
                      'admission_scope':decision,'review':'pending_user_confirmation'}
            self.repository.insert_ai_proposal(session,user_id,letter_id,ticket['revision'],
                ticket['source_hash'],operation,request_hash,validated['content'],evidence,
                now=int(self.clock()))

        result=self.runtime.run(user_id=user_id,operation_hash=operation,request_hash=request_hash,
                                contract=contract,preflight=preflight,on_success=store)
        if result.status in ('succeeded','duplicate'):
            proposal=self.repository.generated_proposal(user_id,letter_id,operation,request_hash)
            if proposal is not None:
                return {'status':'proposal','proposal':proposal,'request_id':result.request_id}
            # A replay after acceptance/deletion never re-dispatches or resurrects
            # a proposal. It reports the completed/in-flight/unknown operation.
            return {'status':'already_processed','reason':result.reason,'request_id':result.request_id}
        return {'status':'manual','reason':result.reason,'request_id':result.request_id}
