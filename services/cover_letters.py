"""AI-005 private document workflow. No sending and no real-data provider call."""
from __future__ import annotations
import difflib
import hashlib
import hmac
import re
import time
from domain.cover_letter import (LetterError, canonical, identifier, revision, options, content,
                                 check_hash, text)
from repositories.cover_letters import CoverLetterRepository

class CoverLetterService:
    def __init__(self, repository: CoverLetterRepository, *, signing_key: str, clock=time.time, generator=None):
        if not signing_key:raise ValueError('Signing key required')
        self.repository=repository;self._key=signing_key.encode();self.clock=clock
        self.generator=generator

    def _operation(self,user_id,key):
        if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}',key):
            raise LetterError('invalid_request')
        return self._hash(['letter-operation',user_id,key])

    def _hash(self,value):
        return hmac.new(self._key,canonical(value).encode(),hashlib.sha256).hexdigest()

    def source(self,user_id,saved_id):
        return self.repository.source(identifier(user_id),identifier(saved_id))

    def create(self,user_id,saved_id,source_hash,operation_key,language,length,tone,*,confirmed):
        if confirmed is not True:raise LetterError('confirmation_required')
        identifier(user_id);identifier(saved_id);check_hash(source_hash)
        opts=options(language,length,tone)
        op=self._operation(user_id,operation_key)
        return self.repository.create(user_id,saved_id,source_hash,{**opts,'subject':'','body':''},op,
            self._hash([saved_id,source_hash,opts]),now=int(self.clock()))

    def get(self,user_id,letter_id):
        return self.repository.get(identifier(user_id),identifier(letter_id))

    def list(self,user_id,*,saved_id=None,page=1):
        identifier(user_id)
        if saved_id:identifier(saved_id)
        page=revision(page)
        if page>1000:raise LetterError('invalid_request')
        return self.repository.list(user_id,saved_id=saved_id,page=page)

    def save(self,user_id,letter_id,expected,subject,body,language,length,tone,*,confirmed,proposal_id=None):
        if confirmed is not True:raise LetterError('confirmation_required')
        identifier(user_id);identifier(letter_id)
        if proposal_id:identifier(proposal_id)
        return self.repository.save_version(user_id,letter_id,content(subject,body,language,length,tone),
            revision(expected),now=int(self.clock()),proposal_id=proposal_id)

    def propose_local(self,user_id,letter_id,expected,language,length,tone,ids,operation_key):
        identifier(user_id);identifier(letter_id);expected=revision(expected)
        opts=options(language,length,tone);op=self._operation(user_id,operation_key)
        # Validate the primitive request before hashing; repository revalidates selection under lock.
        if not isinstance(ids,list) or len(ids)>8 or any(not isinstance(x,str) or len(x)>128 for x in ids):
            raise LetterError('invalid_selection')
        return self.repository.propose_local(user_id,letter_id,expected,opts,ids,op,
            self._hash([letter_id,expected,opts,ids]),now=int(self.clock()))

    def preview_generation(self,user_id,letter_id,expected,language,length,tone,ids):
        self.get(user_id,letter_id)
        if self.generator is None:raise LetterError('generation_unavailable')
        return self.generator.preview(user_id,letter_id,expected,language,length,tone,ids)

    def generate(self,user_id,letter_id,*,review_token=None,confirmed=False):
        self.get(user_id,letter_id)  # Preserve ownership before availability checks.
        if self.generator is None:raise LetterError('generation_unavailable')
        return self.generator.generate(user_id,letter_id,review_token,confirmed=confirmed)

    def reject(self,user_id,letter_id,proposal_id,expected,*,confirmed):
        if confirmed is not True:raise LetterError('confirmation_required')
        return self.repository.reject(identifier(user_id),identifier(letter_id),identifier(proposal_id),revision(expected))

    def version(self,user_id,letter_id,number):
        return self.repository.get_version(identifier(user_id),identifier(letter_id),revision(number))

    def compare(self,user_id,letter_id,left,right):
        before=self.version(user_id,letter_id,left);after=self.version(user_id,letter_id,right)
        # Native escaped text, no generated HTML and no provider call.
        def lines(v):
            c=v['content'];return [f"language={c['language']}; length={c['length']}; tone={c['tone']}",c['subject'],'',*c['body'].splitlines()]
        return dict(left=before,right=after,diff='\n'.join(difflib.unified_diff(
            lines(before),lines(after),fromfile='version-'+str(before['number']),tofile='version-'+str(after['number']),lineterm='')))

    def export_text(self,user_id,letter_id,number):
        version=self.version(user_id,letter_id,number);value=version['content']
        # Only an immutable, explicitly reviewed version. No unreviewed proposal export.
        return ('\ufeff'+value['subject']+'\n\n'+value['body']+'\n').encode('utf-8')

    def delete_version(self,user_id,letter_id,number,expected,*,confirmed):
        if confirmed is not True:raise LetterError('confirmation_required')
        return self.repository.delete_version(identifier(user_id),identifier(letter_id),revision(number),revision(expected),now=int(self.clock()))

    def delete(self,user_id,letter_id,expected,*,confirmed):
        if confirmed is not True:raise LetterError('confirmation_required')
        return self.repository.delete(identifier(user_id),identifier(letter_id),revision(expected))
