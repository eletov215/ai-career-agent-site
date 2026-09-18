"""AI-005 document contracts. Documents are not canonical candidate facts.

Only reviewed versions can be exported. Local composition is extractive and
explicitly NOT a live AI response. Real-data provider activation stays closed.
"""
from __future__ import annotations
import hashlib
import json
import re
import unicodedata
from typing import Any
from uuid import UUID

SOURCE_VERSION = 'cover-letter-source-v1'
COMPOSITION_VERSION = 'extractive-letter-v1'
MAX_LETTERS = 100
MAX_VERSIONS = 50
MAX_PROPOSALS = 20
MAX_BODY = 8000
MAX_SUBJECT = 240
MAX_FACTS = 100
MAX_SOURCE_BYTES = 160000
LANGUAGES = ('ru', 'en')
LENGTHS = ('short', 'full')
TONES = ('professional', 'friendly')

class LetterError(ValueError):
    """Fixed codes only; never include user content or database errors."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def identifier(value: str) -> str:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
        return value
    except (ValueError, TypeError, AttributeError):
        raise LetterError('invalid_request') from None


def revision(value: Any, *, zero=False) -> int:
    if type(value) is int:
        number = value
    elif isinstance(value, str) and re.fullmatch(r'[0-9]{1,9}', value):
        number = int(value)
    else:
        raise LetterError('invalid_request')
    if not (0 if zero else 1) <= number <= 999999999:
        raise LetterError('invalid_request')
    return number


def text(value: Any, maximum: int, *, blank=False, multiline=True) -> str:
    if not isinstance(value, str):
        raise LetterError('invalid_text')
    value = value.replace('\r\n', '\n').replace('\r', '\n').strip()
    if len(value) > maximum or (not blank and not value):
        raise LetterError('invalid_text')
    for char in value:
        if unicodedata.category(char) in ('Cc', 'Cs', 'Cf') and not (multiline and char in '\n\t'):
            raise LetterError('invalid_text')
    return value


def options(language: str, length: str, tone: str) -> dict[str, str]:
    if language not in LANGUAGES or length not in LENGTHS or tone not in TONES:
        raise LetterError('invalid_options')
    return dict(language=language, length=length, tone=tone)


def content(subject: str, body: str, language: str, length: str, tone: str) -> dict:
    return {**options(language, length, tone),
            'subject': text(subject, MAX_SUBJECT, multiline=False), 'body': text(body, MAX_BODY)}


def check_hash(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise LetterError('invalid_request')
    return value


def selected_facts(source: dict, ids: list[str], length: str) -> list[dict]:
    maximum = 3 if length == 'short' else 8
    if (not isinstance(ids, list) or not 1 <= len(ids) <= maximum
            or any(not isinstance(item, str) for item in ids) or len(set(ids)) != len(ids)):
        raise LetterError('invalid_selection')
    facts = {row['id']: row for row in source['facts']}
    if any(item not in facts for item in ids):
        raise LetterError('invalid_selection')
    return [facts[item] for item in ids]


def compose(source: dict, ids: list[str], language: str, length: str, tone: str) -> dict:
    """Copy ONLY selected confirmed-source excerpts. No duration/impact inference.

    Excerpts are not translated; the user reviews mixed-language source text.
    Tone/length affect framing and allowed fact count, not claimed qualifications.
    """
    opts = options(language, length, tone)
    facts = selected_facts(source, ids, length)
    title = source['vacancy']['title']
    company = source['vacancy']['company']
    if language == 'en':
        subject = 'Application: ' + title
        greeting = 'Dear hiring team,' if tone == 'professional' else 'Hello,'
        opening = f'I would like to apply for the position of {title}' + (f' at {company}.' if company else '.')
        lead = 'The following excerpts from my profile describe my experience:'
        closing = 'Thank you for considering my application.'
        extra = 'I would welcome a conversation about the role and your requirements.'
    else:
        subject = '\u041e\u0442\u043a\u043b\u0438\u043a: ' + title
        greeting = '\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435!' if tone == 'professional' else '\u0414\u043e\u0431\u0440\u044b\u0439 \u0434\u0435\u043d\u044c!'
        opening = '\u0425\u043e\u0447\u0443 \u043e\u0442\u043a\u043b\u0438\u043a\u043d\u0443\u0442\u044c\u0441\u044f \u043d\u0430 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u044e \u00ab' + title + '\u00bb' + (' \u0432 \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438 ' + company if company else '') + '.'
        lead = '\u041c\u043e\u0439 \u043e\u043f\u044b\u0442 \u043e\u043f\u0438\u0441\u044b\u0432\u0430\u044e\u0442 \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0435 \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442\u044b \u043f\u0440\u043e\u0444\u0438\u043b\u044f:'
        closing = '\u0421\u043f\u0430\u0441\u0438\u0431\u043e \u0437\u0430 \u0440\u0430\u0441\u0441\u043c\u043e\u0442\u0440\u0435\u043d\u0438\u0435 \u043c\u043e\u0435\u0433\u043e \u043e\u0442\u043a\u043b\u0438\u043a\u0430.'
        extra = '\u0413\u043e\u0442\u043e\u0432 \u043e\u0431\u0441\u0443\u0434\u0438\u0442\u044c \u0437\u0430\u0434\u0430\u0447\u0438 \u0440\u043e\u043b\u0438 \u0438 \u0432\u0430\u0448\u0438 \u0442\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u044f.'
    subject = subject[:MAX_SUBJECT]
    blocks = [greeting, opening, lead + '\n' + '\n'.join('- ' + f['text'] for f in facts)]
    if length == 'full':
        blocks.append(extra)
    blocks.append(closing)
    return content(subject, '\n\n'.join(blocks), **opts)
