"""Allowlisted snapshot projection from server search data, never raw provider JSON."""
from __future__ import annotations

import math
from typing import Any

from domain.saved_vacancy import (
    SNAPSHOT_VERSION, MAX_SOURCES, PROVIDERS, SOURCE_TITLES, SavedVacancyError,
    canonical_json, fingerprint, safe_source_url, source_identity,
)
from domain.vacancy_contract import WORK_FORMAT_VALUES, EMPLOYMENT_VALUES, EXPERIENCE_VALUES
from services.vacancy_normalizer import clean_text


def build_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or len(canonical_json(payload).encode('utf-8')) > 2_000_000:
        raise SavedVacancyError('invalid_source')
    truncated: list[str] = []

    def bounded(name: str, limit: int) -> str:
        raw = payload.get(name)
        text = clean_text(raw) if isinstance(raw, (str, int, float)) and not isinstance(raw, bool) else ''
        if len(text) > limit:
            truncated.append(name)
        return text[:limit]

    result = {name: bounded(name, limit) for name, limit in {
        'title': 512, 'company': 512, 'location': 512,
        'description': 32000, 'requirements': 16000,
        'schedule': 256, 'employment': 256, 'experience': 256,
        'published_at': 80, 'currency': 16,
    }.items()}
    if not result['title']:
        raise SavedVacancyError('invalid_source')
    for key in ('salary_from', 'salary_to'):
        value = payload.get(key)
        result[key] = (value if type(value) in (int, float) and math.isfinite(value)
                       and 0 <= value <= 1e12 else None)
    for key, allowed in [('work_format', WORK_FORMAT_VALUES), ('employment_code', EMPLOYMENT_VALUES),
                         ('experience_code', EXPERIENCE_VALUES)]:
        value = payload.get(key)
        result[key] = value if isinstance(value, str) and value in allowed else 'unknown'
    raw_sources = payload.get('source_records')
    if not isinstance(raw_sources, list) or not raw_sources:
        raw_sources = [payload]
    if len(raw_sources) > MAX_SOURCES:
        raise SavedVacancyError('invalid_source')
    sources = []
    seen = set()
    for raw in raw_sources:
        if not isinstance(raw, dict):
            raise SavedVacancyError('invalid_source')
        source = str(raw.get('source') or '').strip().lower()
        external_id = str(raw.get('external_id') or '').strip()
        if (source not in PROVIDERS or len(external_id) > 256
                or any(ord(char) < 32 or ord(char) == 127 for char in external_id)):
            raise SavedVacancyError('invalid_source')
        url = safe_source_url(raw.get('url'), source)
        identity = source_identity(source, external_id, url)
        if identity in seen:
            continue
        seen.add(identity)
        status = raw.get('source_status')
        sources.append({'source': source, 'source_title': SOURCE_TITLES[source],
                        'external_id': external_id, 'url': url, 'identity_hash': identity,
                        'source_status': status if status in ('active', 'closed', 'expired') else 'unknown'})
    if not sources:
        raise SavedVacancyError('invalid_source')
    result.update(snapshot_version=SNAPSHOT_VERSION, source_records=sources,
                  truncated_fields=truncated)
    return result


def old_browser_key(payload: dict[str, Any]) -> str:
    # Exact old presenter precedence, for explicit user-requested migration only.
    title = clean_text(payload.get('title')) or '\u0411\u0435\u0437 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u044f'
    company = clean_text(payload.get('company')) or '\u041a\u043e\u043c\u043f\u0430\u043d\u0438\u044f \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430'
    return str(payload.get('dedup_group_id') or payload.get('url') or '') or f"{payload.get('source', '')}:{title}:{company}"
