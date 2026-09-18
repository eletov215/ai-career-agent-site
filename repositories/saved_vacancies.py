"""JOB-001 short owner-locked transactions, independent of cache retention."""
from __future__ import annotations

from contextlib import contextmanager
import json
from uuid import uuid4
from typing import Any

from sqlalchemy import delete, func, or_, select, text, tuple_
from domain.saved_vacancy import (
    MAX_SAVED, MAX_SOURCES, SNAPSHOT_VERSION, STALE_SECONDS, SavedVacancyError,
    canonical_json, fingerprint, note_value, revision_value, safe_source_url,
)
from models import User, SearchSnapshot, SearchSnapshotItem, VacancySourceRecord
from models.saved_vacancy import SavedVacancy, SavedVacancySource
from models.cover_letter import CoverLetter
from services.saved_vacancy_snapshot import build_snapshot, old_browser_key
from .base import RepositoryBase


def saved_view(row: SavedVacancy) -> dict[str, Any]:
    try:
        snapshot = json.loads(row.snapshot_json)
        if (fingerprint(snapshot) != row.snapshot_hash
                or row.snapshot_version != SNAPSHOT_VERSION
                or snapshot.get('snapshot_version') != SNAPSHOT_VERSION):
            raise ValueError('Invalid snapshot')
    except (TypeError, ValueError, AttributeError):
        raise SavedVacancyError('invalid_saved_snapshot') from None
    return {'id': row.id, 'snapshot': snapshot, 'snapshot_hash': row.snapshot_hash,
            'snapshot_version': row.snapshot_version, 'note': row.note,
            'revision': row.revision, 'created_at': row.created_at, 'updated_at': row.updated_at}


def source_view(row: SavedVacancySource) -> dict[str, Any]:
    return {'saved_vacancy_id': row.saved_vacancy_id, 'source': row.source,
            'external_id': row.external_id, 'url': safe_source_url(row.url, row.source), 'created_at': row.created_at}


class SavedVacancyRepository(RepositoryBase):
    @staticmethod
    def _owner(session, user_id: str, *, lock: bool = False):
        query = select(User).where(User.id == user_id)
        owner = session.scalar(query.with_for_update() if lock else query)
        if owner is None or owner.status != 'active' or owner.email_verified_at is None:
            raise SavedVacancyError('verified_account_required')
        return owner

    @contextmanager
    def _write(self, user_id: str):
        with self.session() as session:
            if self.engine.dialect.name == 'sqlite':
                session.execute(text('BEGIN IMMEDIATE'))
            elif self.engine.dialect.name == 'postgresql':
                session.execute(text("SET LOCAL lock_timeout = '5s'"))
            try:
                self._owner(session, user_id, lock=True)
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def _row(session, user_id: str, saved_id: str):
        row = session.scalar(select(SavedVacancy).where(
            SavedVacancy.user_id == user_id, SavedVacancy.id == saved_id))
        if row is None:
            raise SavedVacancyError('not_found')
        return row

    @staticmethod
    def _search_row(session, snapshot_id: str, key: str, now: int):
        row = session.scalar(select(SearchSnapshotItem).join(
            SearchSnapshot, SearchSnapshot.id == SearchSnapshotItem.snapshot_id).where(
            SearchSnapshot.id == snapshot_id, SearchSnapshot.expires_at > now,
            SearchSnapshot.status != 'expired', SearchSnapshotItem.stable_key == key,
            SearchSnapshotItem.ordinal < SearchSnapshot.committed_count))
        if row is None:
            raise SavedVacancyError('stale_source')
        try:
            payload = json.loads(row.payload_json)
            if not isinstance(payload, dict):
                raise ValueError('not an object')
            return payload
        except (TypeError, ValueError):
            raise SavedVacancyError('invalid_source') from None

    def saved_ids(self, user_id: str, identities: list[str]) -> dict[str, str]:
        if not identities:
            return {}
        with self.session() as session:
            self._owner(session, user_id)
            rows = session.execute(select(SavedVacancySource.identity_hash, SavedVacancySource.saved_vacancy_id)
                                   .where(SavedVacancySource.user_id == user_id,
                                          SavedVacancySource.identity_hash.in_(identities[:1000]))).all()
            return dict(rows)

    def _save(self, session, user_id: str, snapshot: dict[str, Any], now: int):
        sources = snapshot['source_records']
        identities = [source['identity_hash'] for source in sources]
        existing = session.scalars(select(SavedVacancySource).where(
            SavedVacancySource.user_id == user_id, SavedVacancySource.identity_hash.in_(identities))).all()
        saved_ids = {source.saved_vacancy_id for source in existing}
        if len(saved_ids) > 1:
            # Preserve both notes and snapshots instead of destructively coalescing.
            raise SavedVacancyError('ambiguous_group')
        if saved_ids:
            row = self._row(session, user_id, next(iter(saved_ids)))
            known = session.scalars(select(SavedVacancySource.identity_hash).where(
                SavedVacancySource.user_id == user_id, SavedVacancySource.saved_vacancy_id == row.id)).all()
            known = set(known)
            extra = [source for source in sources if source['identity_hash'] not in known]
            if len(known) + len(extra) > MAX_SOURCES:
                raise SavedVacancyError('source_limit')
            if extra:
                row.revision += 1
                row.updated_at = now
            created = False
        else:
            count = session.scalar(select(func.count()).select_from(SavedVacancy).where(SavedVacancy.user_id == user_id))
            if count >= MAX_SAVED:
                raise SavedVacancyError('history_limit')
            row = SavedVacancy(id=str(uuid4()), user_id=user_id,
                snapshot_json=canonical_json(snapshot), snapshot_hash=fingerprint(snapshot),
                snapshot_version=SNAPSHOT_VERSION, title=snapshot['title'], company=snapshot['company'],
                location=snapshot['location'], search_text=' '.join(snapshot[k] for k in ('title','company','location')).casefold(),
                note='', revision=1, created_at=now, updated_at=now)
            session.add(row)
            session.flush()
            extra = sources
            created = True
        for source in extra:
            session.add(SavedVacancySource(id=str(uuid4()), saved_vacancy_id=row.id, user_id=user_id,
                source=source['source'], external_id=source['external_id'], identity_hash=source['identity_hash'],
                url=source['url'], created_at=now))
        session.flush()
        return {**saved_view(row), 'created': created}

    def save_reference(self, user_id: str, snapshot_id: str, key: str, source_hash: str, *, now: int):
        with self._write(user_id) as session:
            payload = self._search_row(session, snapshot_id, key, now)
            if fingerprint(payload) != source_hash:
                raise SavedVacancyError('stale_source')
            return self._save(session, user_id, build_snapshot(payload), now)

    def list(self, user_id: str, *, query: str = '', page: int = 1, per_page: int = 20):
        with self.session() as session:
            self._owner(session, user_id)
            conditions = [SavedVacancy.user_id == user_id]
            if query:
                # A literal substring: %, _ and SQL fragments have no wildcard meaning.
                conditions.append(SavedVacancy.search_text.contains(query.casefold(), autoescape=True))
            total = session.scalar(select(func.count()).select_from(SavedVacancy).where(*conditions)) or 0
            rows = session.scalars(select(SavedVacancy).where(*conditions)
                .order_by(SavedVacancy.created_at.desc(), SavedVacancy.id.asc())
                .offset((page-1)*per_page).limit(per_page)).all()
            return {'items': [saved_view(row) for row in rows], 'total': total, 'page': page,
                    'pages': max(1, (total+per_page-1)//per_page), 'query': query}

    def get(self, user_id: str, saved_id: str, *, now: int):
        with self.session() as session:
            self._owner(session, user_id)
            result = saved_view(self._row(session, user_id, saved_id))
            sources = session.scalars(select(SavedVacancySource).where(
                SavedVacancySource.user_id == user_id, SavedVacancySource.saved_vacancy_id == saved_id)
                .order_by(SavedVacancySource.source, SavedVacancySource.external_id)).all()
            pairs = [(source.source, source.external_id) for source in sources if source.external_id]
            cached = session.scalars(select(VacancySourceRecord).where(
                tuple_(VacancySourceRecord.source, VacancySourceRecord.external_id).in_(pairs))).all() if pairs else []
            cache = {(row.source, row.external_id): row for row in cached}
            views = []
            for source in sources:
                current = cache.get((source.source, source.external_id))
                state = 'not_in_cache'
                observed = None
                if current is not None:
                    observed = current.fetched_at
                    state = ('closed_in_cache' if current.source_status in ('closed','expired')
                             else 'stale_cache' if now-current.fetched_at > STALE_SECONDS
                             else 'active_in_cache' if current.source_status == 'active' else 'unknown')
                views.append({**source_view(source), 'state': state, 'observed_at': observed})
            result.update(sources=views, old_snapshot=now-result['created_at'] > STALE_SECONDS,
                          match=None, match_reason='not_available')
            return result

    def update_note(self, user_id: str, saved_id: str, value: str, expected_revision: int, *, now: int):
        value, expected_revision = note_value(value), revision_value(expected_revision)
        with self._write(user_id) as session:
            row = self._row(session, user_id, saved_id)
            if row.revision != expected_revision:
                raise SavedVacancyError('stale_write')
            if row.note != value:
                row.note = value
                row.search_text = ' '.join((row.title, row.company, row.location, value)).casefold()
                row.revision += 1
                row.updated_at = now
            return saved_view(row)

    def delete(self, user_id: str, saved_id: str, expected_revision: int):
        expected_revision = revision_value(expected_revision)
        with self._write(user_id) as session:
            row = self._row(session, user_id, saved_id)
            if row.revision != expected_revision:
                raise SavedVacancyError('stale_write')
            # The shared owner lock serializes letter creation against deletion.
            # Account deletion has a separate explicit whole-account confirmation.
            if session.scalar(select(CoverLetter.id).where(CoverLetter.user_id == user_id,
                                CoverLetter.saved_vacancy_id == saved_id).limit(1)) is not None:
                raise SavedVacancyError('has_letters')
            session.execute(delete(SavedVacancy).where(SavedVacancy.id == saved_id, SavedVacancy.user_id == user_id))

    @staticmethod
    def _cache_payload(row: VacancySourceRecord):
        # Explicit fields only. Do not deserialize raw_json (may contain extra data).
        return {key: getattr(row, key) for key in (
            'source','external_id','title','company','location','salary_from','salary_to','currency',
            'work_format','employment_code','experience_code','schedule','employment','experience',
            'description','requirements','published_at','url','source_status')}

    def import_legacy(self, user_id: str, keys: list[str], *, now: int):
        """Bounded exact-key resolution; caller must obtain explicit user consent.

        Legacy browser keys have no account identity. No automatic migration,
        source HTTP lookup or invented snapshot. Unresolved keys remain local.
        """
        from domain.saved_vacancy import legacy_keys
        keys = legacy_keys(keys)
        with self._write(user_id) as session:
            # Old URL/anonymous keys can be found in canonical cache. Dedup keys
            # can be resolved only against recent served search items (bounded).
            cache_rows = session.scalars(select(VacancySourceRecord).where(or_(
                VacancySourceRecord.url.in_(keys),
                (VacancySourceRecord.source + ':' + VacancySourceRecord.title + ':' + func.coalesce(VacancySourceRecord.company,'')).in_(keys)
            )).limit(101)).all()
            recent = session.scalars(select(SearchSnapshotItem).join(
                SearchSnapshot, SearchSnapshot.id == SearchSnapshotItem.snapshot_id).where(
                SearchSnapshot.expires_at > now, SearchSnapshot.status != 'expired',
                SearchSnapshotItem.ordinal < SearchSnapshot.committed_count)
                .order_by(SearchSnapshotItem.created_at.desc(),SearchSnapshotItem.id.desc()).limit(200)).all()
            choices: dict[str, dict[tuple[str, ...], dict[str, Any]]] = {key: {} for key in keys}
            payloads = [self._cache_payload(row) for row in cache_rows]
            for row in recent:
                try:
                    if len(row.payload_json) <= 2_000_000:
                        raw = json.loads(row.payload_json)
                        if isinstance(raw, dict):
                            payloads.append(raw)
                except (ValueError, TypeError):
                    continue
            for payload in payloads:
                key = old_browser_key(payload)
                if key not in choices:
                    continue
                try:
                    snapshot = build_snapshot(payload)
                    identity = tuple(sorted(row['identity_hash'] for row in snapshot['source_records']))
                except (SavedVacancyError, ValueError, TypeError):
                    continue
                choices[key].setdefault(identity, snapshot)
            saved, unresolved = [], []
            for key in keys:
                candidates = choices[key]
                if len(candidates) != 1:
                    unresolved.append(key)
                    continue
                try:
                    self._save(session, user_id, next(iter(candidates.values())), now)
                except SavedVacancyError as exc:
                    if str(exc) not in ('ambiguous_group','source_limit','history_limit'):
                        raise
                    unresolved.append(key)
                    continue
                saved.append(key)
            return {'saved_keys': saved, 'saved_count': len(saved), 'unresolved_count': len(unresolved)}
