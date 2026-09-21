"""Short owner-serialized AI-005 transactions, never provider I/O.

Snapshots and versions are immutable. Editing or deleting a profile does not
silently rewrite a historical letter. Normal saved-vacancy deletion is protected
while letters exist; account deletion intentionally cascades the whole subtree.
"""
from __future__ import annotations
from contextlib import contextmanager
import json
from uuid import uuid4
from sqlalchemy import select, delete, func, text as sqltext
from models import User, CareerProfile, CareerProfileVersion, SavedVacancy
from models.cover_letter import CoverLetter, CoverLetterVersion, CoverLetterProposal
from repositories.base import RepositoryBase
from repositories.saved_vacancies import saved_view
from domain.saved_vacancy import SavedVacancyError
from domain.cover_letter import (SOURCE_VERSION, MAX_LETTERS, MAX_VERSIONS, MAX_PROPOSALS,
    LetterError, canonical, digest, content)
from services.cover_letter_source import build_source


def checked_json(raw, expected):
    try:
        if not isinstance(raw, str) or len(raw) > 200000:
            raise ValueError
        value = json.loads(raw)
        if not isinstance(value, dict) or digest(value) != expected:
            raise ValueError
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise LetterError('storage_integrity') from None


def letter_view(row):
    source = checked_json(row.source_json, row.source_hash)
    if source.get('schema') != SOURCE_VERSION or source.get('saved_vacancy_id') != row.saved_vacancy_id:
        raise LetterError('storage_integrity')
    return dict(id=row.id, saved_vacancy_id=row.saved_vacancy_id, source=source,
                source_hash=row.source_hash, content=checked_json(row.content_json,row.content_hash),
                revision=row.revision,last_version=row.last_version,
                created_at=row.created_at,updated_at=row.updated_at)


def evidence_view(raw):
    try:
        if not isinstance(raw,str) or len(raw)>10000:raise ValueError
        result=json.loads(raw)
        if not isinstance(result,dict):raise ValueError
        ids=result.get('selected_fact_ids',[])
        if not isinstance(ids,list) or len(ids)>8 or any(not isinstance(k,str) or len(k)>128 for k in ids):raise ValueError
        return result
    except (ValueError,TypeError,RecursionError):
        raise LetterError('storage_integrity') from None


def version_view(row):
    if row.origin not in ('manual','local_template','user_edited_local_template','alice_draft','user_edited_alice_draft'):
        raise LetterError('storage_integrity')
    return dict(id=row.id, letter_id=row.letter_id, number=row.number,
                content=checked_json(row.content_json,row.content_hash),content_hash=row.content_hash,
                source_hash=row.source_hash,origin=row.origin,evidence=evidence_view(row.evidence_json),
                reviewed_at=row.reviewed_at)


def proposal_view(row):
    if row.origin not in ('local_template','alice_draft'):raise LetterError('storage_integrity')
    return dict(id=row.id,letter_id=row.letter_id,base_revision=row.base_revision,
                source_hash=row.source_hash,content=checked_json(row.content_json,row.content_hash),
                content_hash=row.content_hash,evidence=evidence_view(row.evidence_json),
                origin=row.origin,status=row.status,created_at=row.created_at)


class CoverLetterRepository(RepositoryBase):
    @staticmethod
    def _owner(session,user_id,*,lock=False):
        query=select(User).where(User.id==user_id)
        row=session.scalar(query.with_for_update() if lock else query)
        if row is None or row.status!='active' or row.email_verified_at is None:
            raise LetterError('verified_account_required')
        return row

    @contextmanager
    def _write(self,user_id):
        with self.session() as session:
            try:
                if self.engine.dialect.name=='sqlite':session.execute(sqltext('BEGIN IMMEDIATE'))
                elif self.engine.dialect.name=='postgresql':session.execute(sqltext("SET LOCAL lock_timeout = '5s'"))
                self._owner(session,user_id,lock=True)
                yield session
                session.commit()
            except BaseException:
                session.rollback()
                raise

    @staticmethod
    def _row(session,user_id,letter_id):
        row=session.scalar(select(CoverLetter).where(CoverLetter.id==letter_id,CoverLetter.user_id==user_id))
        if row is None:raise LetterError('not_found')
        return row

    @staticmethod
    def _saved(session,user_id,saved_id):
        row=session.scalar(select(SavedVacancy).where(SavedVacancy.id==saved_id,SavedVacancy.user_id==user_id))
        if row is None:raise LetterError('not_found')
        try:return saved_view(row)
        except SavedVacancyError:raise LetterError('storage_integrity') from None

    def _source(self,session,user_id,saved_id):
        saved=self._saved(session,user_id,saved_id)
        row=session.scalar(select(CareerProfile).where(CareerProfile.user_id==user_id))
        data={};version=0;source_hash=''
        if row is not None and row.confirmed_at is not None:
            historical=session.scalar(select(CareerProfileVersion).where(
                CareerProfileVersion.profile_id==row.id,CareerProfileVersion.version==row.version))
            if historical is None or historical.content_hash!=row.content_hash:
                raise LetterError('storage_integrity')
            data=checked_json(historical.snapshot_json,historical.content_hash)
            version=row.version;source_hash=row.content_hash
        return build_source(saved,data,profile_version=version,profile_hash=source_hash)

    def source(self,user_id,saved_id):
        with self._write(user_id) as s:
            source=self._source(s,user_id,saved_id)
            return {'source':source,'source_hash':digest(source)}

    def create(self,user_id,saved_id,expected_source_hash,initial,operation_hash,request_hash,*,now):
        with self._write(user_id) as s:
            old=s.scalar(select(CoverLetter).where(CoverLetter.user_id==user_id,CoverLetter.operation_hash==operation_hash))
            if old is not None:
                if old.request_hash!=request_hash:raise LetterError('idempotency_conflict')
                return {**letter_view(old),'created':False}
            source=self._source(s,user_id,saved_id)
            if digest(source)!=expected_source_hash:raise LetterError('stale_source')
            count=s.scalar(select(func.count()).select_from(CoverLetter).where(CoverLetter.user_id==user_id))
            if count>=MAX_LETTERS:raise LetterError('history_limit')
            row=CoverLetter(id=str(uuid4()),user_id=user_id,saved_vacancy_id=saved_id,
                operation_hash=operation_hash,request_hash=request_hash,source_json=canonical(source),
                source_hash=digest(source),content_json=canonical(initial),content_hash=digest(initial),
                revision=1,last_version=0,created_at=now,updated_at=now)
            s.add(row);s.flush()
            return {**letter_view(row),'created':True}

    @staticmethod
    def _revision(row,expected):
        if row.revision!=expected:raise LetterError('stale_write')

    def _fresh(self,s,user_id,row):
        return digest(self._source(s,user_id,row.saved_vacancy_id))==row.source_hash

    def get(self,user_id,letter_id):
        with self.session() as s:
            self._owner(s,user_id);row=self._row(s,user_id,letter_id)
            result=letter_view(row)
            result['source_stale']=not self._fresh(s,user_id,row)
            result['versions']=[version_view(v) for v in s.scalars(select(CoverLetterVersion).where(
                CoverLetterVersion.user_id==user_id,CoverLetterVersion.letter_id==letter_id)
                .order_by(CoverLetterVersion.number.desc()).limit(MAX_VERSIONS+1)).all()]
            result['proposals']=[proposal_view(p) for p in s.scalars(select(CoverLetterProposal).where(
                CoverLetterProposal.user_id==user_id,CoverLetterProposal.letter_id==letter_id,
                CoverLetterProposal.status=='pending').order_by(CoverLetterProposal.created_at.desc(),CoverLetterProposal.id)
                .limit(MAX_PROPOSALS+1)).all()]
            if any(v['source_hash']!=row.source_hash for v in [*result['versions'],*result['proposals']]):
                raise LetterError('storage_integrity')
            if len(result['versions'])>MAX_VERSIONS or len(result['proposals'])>MAX_PROPOSALS:
                raise LetterError('storage_integrity')
            return result

    def list(self,user_id,*,saved_id=None,page=1):
        with self.session() as s:
            self._owner(s,user_id)
            where=[CoverLetter.user_id==user_id]
            if saved_id:
                self._saved(s,user_id,saved_id);where.append(CoverLetter.saved_vacancy_id==saved_id)
            total=s.scalar(select(func.count()).select_from(CoverLetter).where(*where)) or 0
            rows=s.scalars(select(CoverLetter).where(*where).order_by(CoverLetter.updated_at.desc(),CoverLetter.id)
                           .offset((page-1)*20).limit(20)).all()
            return dict(items=[letter_view(r) for r in rows],total=total,page=page,pages=max(1,(total+19)//20))

    def _save(self,s,row,value,*,origin,evidence,now):
        if row.content_hash==digest(value) and row.last_version:
            return {**letter_view(row),'changed':False}
        count=s.scalar(select(func.count()).select_from(CoverLetterVersion).where(CoverLetterVersion.letter_id==row.id))
        if count>=MAX_VERSIONS:raise LetterError('version_limit')
        row.last_version+=1;row.revision+=1;row.updated_at=now
        row.content_json=canonical(value);row.content_hash=digest(value)
        s.add(CoverLetterVersion(id=str(uuid4()),letter_id=row.id,user_id=row.user_id,
            number=row.last_version,content_json=row.content_json,content_hash=row.content_hash,
            source_hash=row.source_hash,origin=origin,evidence_json=canonical(evidence),reviewed_at=now))
        s.flush()
        return {**letter_view(row),'changed':True}

    def save_version(self,user_id,letter_id,value,expected,*,now,proposal_id=None):
        with self._write(user_id) as s:
            row=self._row(s,user_id,letter_id);self._revision(row,expected)
            letter_view(row)
            origin='manual';evidence={'review':'user_declared_not_independently_verified'}
            if proposal_id:
                p=s.scalar(select(CoverLetterProposal).where(CoverLetterProposal.id==proposal_id,
                    CoverLetterProposal.letter_id==letter_id,CoverLetterProposal.user_id==user_id))
                if p is None:raise LetterError('not_found')
                proposal_view(p)
                if p.status!='pending' or p.base_revision!=row.revision or p.source_hash!=row.source_hash:
                    raise LetterError('stale_write')
                if not self._fresh(s,user_id,row):raise LetterError('stale_source')
                exact=digest(value)==p.content_hash
                origin=p.origin if exact else 'user_edited_'+p.origin
                evidence={**json.loads(p.evidence_json),'text_unchanged':exact,
                          'review':'user_declared_not_independently_verified'}
                s.delete(p)
            return self._save(s,row,value,origin=origin,evidence=evidence,now=now)

    def propose_local(self,user_id,letter_id,expected,opts,ids,operation_hash,request_hash,*,now):
        from domain.cover_letter import compose
        with self._write(user_id) as s:
            row=self._row(s,user_id,letter_id)
            old=s.scalar(select(CoverLetterProposal).where(CoverLetterProposal.user_id==user_id,
                        CoverLetterProposal.operation_hash==operation_hash))
            if old is not None:
                if old.request_hash!=request_hash:raise LetterError('idempotency_conflict')
                return proposal_view(old)
            self._revision(row,expected)
            source=letter_view(row)['source']
            if not self._fresh(s,user_id,row):raise LetterError('stale_source')
            count=s.scalar(select(func.count()).select_from(CoverLetterProposal).where(
                CoverLetterProposal.user_id==user_id,CoverLetterProposal.letter_id==letter_id,
                CoverLetterProposal.status=='pending'))
            if count>=MAX_PROPOSALS:raise LetterError('proposal_limit')
            value=compose(source,ids,**opts)
            p=CoverLetterProposal(id=str(uuid4()),letter_id=letter_id,user_id=user_id,
                operation_hash=operation_hash,request_hash=request_hash,base_revision=row.revision,
                source_hash=row.source_hash,content_json=canonical(value),content_hash=digest(value),
                evidence_json=canonical({'selected_fact_ids':ids,'composition':'extractive-letter-v1'}),
                origin='local_template',status='pending',created_at=now)
            s.add(p);s.flush()
            return proposal_view(p)

    def generation_snapshot(self,user_id,letter_id,expected):
        """Short serial preflight. The transaction ends before the provider call."""
        with self._write(user_id) as s:
            row=self._row(s,user_id,letter_id);self._revision(row,expected)
            if not self._fresh(s,user_id,row):raise LetterError('stale_source')
            count=s.scalar(select(func.count()).select_from(CoverLetterProposal).where(
                CoverLetterProposal.user_id==user_id,CoverLetterProposal.letter_id==letter_id,
                CoverLetterProposal.status=='pending'))
            if count>=MAX_PROPOSALS:raise LetterError('proposal_limit')
            return letter_view(row)

    def insert_ai_proposal(self,s,user_id,letter_id,expected,source_hash,
                           operation_hash,request_hash,value,evidence,*,now):
        """Called inside AIRepository.settle: proposal and accounting are atomic."""
        self._owner(s,user_id,lock=True)
        row=self._row(s,user_id,letter_id);self._revision(row,expected)
        if row.source_hash!=source_hash or not self._fresh(s,user_id,row):
            raise LetterError('stale_source')
        if len(canonical(evidence))>10000:raise LetterError('invalid_generation')
        old=s.scalar(select(CoverLetterProposal).where(CoverLetterProposal.user_id==user_id,
                    CoverLetterProposal.operation_hash==operation_hash))
        if old is not None:
            if old.letter_id!=letter_id or old.request_hash!=request_hash:
                raise LetterError('idempotency_conflict')
            return proposal_view(old)
        count=s.scalar(select(func.count()).select_from(CoverLetterProposal).where(
            CoverLetterProposal.user_id==user_id,CoverLetterProposal.letter_id==letter_id,
            CoverLetterProposal.status=='pending'))
        if count>=MAX_PROPOSALS:raise LetterError('proposal_limit')
        p=CoverLetterProposal(id=str(uuid4()),letter_id=letter_id,user_id=user_id,
            operation_hash=operation_hash,request_hash=request_hash,base_revision=row.revision,
            source_hash=source_hash,content_json=canonical(value),content_hash=digest(value),
            evidence_json=canonical(evidence),origin='alice_draft',status='pending',created_at=now)
        s.add(p);s.flush()
        return proposal_view(p)

    def generated_proposal(self,user_id,letter_id,operation_hash,request_hash):
        with self.session() as s:
            self._owner(s,user_id);self._row(s,user_id,letter_id)
            p=s.scalar(select(CoverLetterProposal).where(CoverLetterProposal.user_id==user_id,
                CoverLetterProposal.letter_id==letter_id,CoverLetterProposal.operation_hash==operation_hash))
            if p is None:return None
            if p.request_hash!=request_hash:raise LetterError('idempotency_conflict')
            return proposal_view(p)

    def reject(self,user_id,letter_id,proposal_id,expected):
        with self._write(user_id) as s:
            row=self._row(s,user_id,letter_id);self._revision(row,expected)
            p=s.scalar(select(CoverLetterProposal).where(CoverLetterProposal.id==proposal_id,
                CoverLetterProposal.user_id==user_id,CoverLetterProposal.letter_id==letter_id))
            if p is None:raise LetterError('not_found')
            # Rejecting a pending proposal is also deletion of its private text.
            if p.status!='pending':raise LetterError('stale_write')
            s.delete(p)

    def get_version(self,user_id,letter_id,number):
        with self.session() as s:
            self._owner(s,user_id);letter=letter_view(self._row(s,user_id,letter_id))
            row=s.scalar(select(CoverLetterVersion).where(CoverLetterVersion.letter_id==letter_id,
                CoverLetterVersion.user_id==user_id,CoverLetterVersion.number==number))
            if row is None:raise LetterError('not_found')
            result=version_view(row)
            if result['source_hash']!=letter['source_hash']:raise LetterError('storage_integrity')
            return result

    def delete_version(self,user_id,letter_id,number,expected,*,now):
        with self._write(user_id) as s:
            row=self._row(s,user_id,letter_id);self._revision(row,expected)
            if row.last_version==number:raise LetterError('current_version')
            old=s.scalar(select(CoverLetterVersion).where(CoverLetterVersion.letter_id==letter_id,
                CoverLetterVersion.user_id==user_id,CoverLetterVersion.number==number))
            if old is None:raise LetterError('not_found')
            s.delete(old);row.revision+=1;row.updated_at=now

    def delete(self,user_id,letter_id,expected):
        with self._write(user_id) as s:
            row=self._row(s,user_id,letter_id);self._revision(row,expected)
            s.execute(delete(CoverLetter).where(CoverLetter.id==letter_id,CoverLetter.user_id==user_id))

    @staticmethod
    def export_in_session(s,user_id):
        rows=s.scalars(select(CoverLetter).where(CoverLetter.user_id==user_id)
                       .order_by(CoverLetter.id).limit(MAX_LETTERS+1)).all()
        versions=s.scalars(select(CoverLetterVersion).where(CoverLetterVersion.user_id==user_id)
                          .order_by(CoverLetterVersion.letter_id,CoverLetterVersion.number)
                          .limit(MAX_LETTERS*MAX_VERSIONS+1)).all()
        proposals=s.scalars(select(CoverLetterProposal).where(CoverLetterProposal.user_id==user_id)
                           .order_by(CoverLetterProposal.letter_id,CoverLetterProposal.created_at)
                           .limit(MAX_LETTERS*MAX_PROPOSALS+1)).all()
        if len(rows)>MAX_LETTERS or len(versions)>MAX_LETTERS*MAX_VERSIONS or len(proposals)>MAX_LETTERS*MAX_PROPOSALS:
            raise LetterError('export_limit')
        owned={r.id for r in rows}
        if any(r.letter_id not in owned for r in [*versions,*proposals]):raise LetterError('storage_integrity')
        return {'cover_letters':[letter_view(r) for r in rows],
                'cover_letter_versions':[version_view(r) for r in versions],
                'cover_letter_proposals':[proposal_view(r) for r in proposals]}
