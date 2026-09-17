"""JOB-001 orchestration: signed server references, owned data, no network I/O."""
from __future__ import annotations
import time
from uuid import UUID
from typing import Any
from itsdangerous import URLSafeTimedSerializer, BadData
from domain.saved_vacancy import REFERENCE_TTL, MAX_NOTE, SavedVacancyError, fingerprint, legacy_keys, revision_value
from repositories.saved_vacancies import SavedVacancyRepository
from services.saved_vacancy_snapshot import build_snapshot
from services.vacancy_presenter import present_vacancy


class SavedVacancyService:
    def __init__(self, repository: SavedVacancyRepository, *, signing_key: str):
        self.repository = repository
        self.signer = URLSafeTimedSerializer(signing_key, salt='job001-saved-vacancy-v1')

    def controls(self, user_id: str, snapshot_id: str, items: list[dict[str, Any]]):
        prepared = []
        for raw in items:
            payload = {k: v for k, v in raw.items() if k != '_snapshot_item_key'}
            key = raw.get('_snapshot_item_key')
            try:
                snapshot = build_snapshot(payload)
                if not isinstance(key, str) or not key or not snapshot_id:
                    raise SavedVacancyError('invalid_source')
                token = self.signer.dumps({'owner': user_id, 'snapshot': snapshot_id, 'key': key, 'hash': fingerprint(payload)})
                identities = [source['identity_hash'] for source in snapshot['source_records']]
                prepared.append({'token': token, 'identities': identities})
            except (ValueError, TypeError):
                prepared.append({'token': None, 'identities': []})
        mapping = self.repository.saved_ids(user_id, list({identity for item in prepared for identity in item['identities']}))
        return [{'reference': item['token'], 'saved_id': next((mapping[key] for key in item['identities'] if key in mapping), None)}
                for item in prepared]

    def save(self, user_id: str, reference: str, *, now: int | None = None):
        if not isinstance(reference, str) or not reference or len(reference) > 4096:
            raise SavedVacancyError('invalid_reference')
        try:
            data = self.signer.loads(reference, max_age=REFERENCE_TTL)
            if (not isinstance(data, dict) or set(data) != {'owner','snapshot','key','hash'}
                    or data['owner'] != user_id
                    or any(not isinstance(data[k], str) for k in data)):
                raise ValueError('invalid reference')
            UUID(data['snapshot'])
        except (BadData, ValueError, TypeError, AttributeError):
            raise SavedVacancyError('invalid_reference') from None
        return self.repository.save_reference(user_id, data['snapshot'], data['key'], data['hash'],
                                              now=int(time.time()) if now is None else now)

    def list(self, user_id: str, *, query: str = '', page: int = 1):
        if not isinstance(query, str) or len(query) > 160 or type(page) is not int or not 1 <= page <= 10000:
            raise SavedVacancyError('invalid_request')
        result = self.repository.list(user_id, query=query.strip(), page=page)
        for item in result['items']:
            item['card'] = present_vacancy(item['snapshot'])
        return result

    def get(self, user_id: str, saved_id: str, *, now: int | None = None):
        result = self.repository.get(user_id, saved_id, now=int(time.time()) if now is None else now)
        result['card'] = present_vacancy(result['snapshot'])
        return result

    def update_note(self, user_id: str, saved_id: str, note: str, expected_revision: Any):
        return self.repository.update_note(user_id, saved_id, note, revision_value(expected_revision), now=int(time.time()))

    def delete(self, user_id: str, saved_id: str, expected_revision: Any):
        self.repository.delete(user_id, saved_id, revision_value(expected_revision))

    def import_legacy(self, user_id: str, keys: Any):
        return self.repository.import_legacy(user_id, legacy_keys(keys), now=int(time.time()))
