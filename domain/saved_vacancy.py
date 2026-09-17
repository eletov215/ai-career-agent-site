"""JOB-001 value validation. Saving a vacancy never invokes an AI provider."""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit, unquote

SNAPSHOT_VERSION = 'saved-vacancy-v1'
MAX_SAVED = 500
MAX_SOURCES = 16
MAX_NOTE = 4000
MAX_LEGACY = 50
REFERENCE_TTL = 1800
STALE_SECONDS = 86400
PROVIDERS = {
    'hh': ('hh.ru', 'hh.by', 'hh.kz', 'hh.uz', 'hh.kg', 'rabota.by', 'headhunter.ge'),
    'superjob': ('superjob.ru',),
    'reed': ('reed.co.uk',),
    'trudvsem': ('trudvsem.ru',),
}
SOURCE_TITLES = {'hh': 'HeadHunter', 'superjob': 'SuperJob', 'reed': 'Reed.co.uk',
                 'trudvsem': '\u0420\u0430\u0431\u043e\u0442\u0430 \u0420\u043e\u0441\u0441\u0438\u0438'}


class SavedVacancyError(ValueError):
    """Public fixed error code only; never echo an input or a storage exception."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


def safe_source_url(value: Any, source: str) -> str:
    """External links only. Never used as a server-side fetch target.

    Drop query/fragment tracking or credentials. Only named provider hosts and
    their subdomains on default web ports may become clickable links.
    """
    if not isinstance(value, str) or not value or len(value) > 2048:
        return ''
    if re.search(r'[\x00-\x20\x7f\\]', value):
        return ''
    try:
        parts = urlsplit(value)
        host = (parts.hostname or '').lower()
        if (parts.scheme not in ('https', 'http') or parts.username or parts.password
                or parts.port not in (None, 80, 443)
                or not any(host == d or host.endswith('.' + d) for d in PROVIDERS.get(source, ()))):
            return ''
        if re.search(r'[\x00-\x1f\x7f\\]', unquote(parts.path)):
            return ''
        return urlunsplit(('https', host, parts.path or '/', '', ''))
    except (ValueError, UnicodeError):
        return ''


def source_identity(source: str, external_id: str, url: str) -> str:
    if source not in PROVIDERS or not (external_id or url):
        raise SavedVacancyError('invalid_source')
    return fingerprint([source, 'id' if external_id else 'url', external_id or url])


def note_value(value: Any) -> str:
    if not isinstance(value, str) or len(value) > MAX_NOTE:
        raise SavedVacancyError('invalid_note')
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', value):
        raise SavedVacancyError('invalid_note')
    return value.strip()


def revision_value(value: Any) -> int:
    if type(value) is int and 1 <= value <= 2147483647:
        return value
    if isinstance(value, str) and re.fullmatch(r'[1-9][0-9]{0,9}', value):
        number = int(value)
        if number <= 2147483647:
            return number
    raise SavedVacancyError('invalid_revision')


def legacy_keys(value: Any) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_LEGACY:
        raise SavedVacancyError('invalid_legacy')
    if any(not isinstance(key, str) or not key or len(key) > 2048
           or re.search(r'[\x00-\x1f\x7f]', key) for key in value):
        raise SavedVacancyError('invalid_legacy')
    return list(dict.fromkeys(value))
