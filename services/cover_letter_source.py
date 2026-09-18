"""Minimal letter input projection. No notes, contacts, resume drafts or AI reports.

Profile confirmation is evidence of a user's declaration, not an independent
verification of employment or competence. Missing fields stay missing.
"""
from __future__ import annotations
from domain.cover_letter import SOURCE_VERSION, MAX_FACTS, MAX_SOURCE_BYTES, LetterError, canonical, digest, text


def build_source(saved: dict, profile: dict, *, profile_version: int, profile_hash: str) -> dict:
    facts = []
    omitted = []
    def add(key, value):
        if not value:
            return
        if len(facts) >= MAX_FACTS:
            omitted.append(key)
            return
        try:
            value = text(value, 4000)
        except LetterError:
            omitted.append(key)
            return
        facts.append({'id': key, 'text': value})
    add('profile.headline', profile.get('headline'))
    add('profile.summary', profile.get('summary'))
    for section, fields in (('skills', ('name',)), ('employment', ('position','company','description')),
                            ('achievements', ('title','description')), ('education', ('institution','degree','field','description'))):
        for i, row in enumerate(profile.get(section, [])):
            if not isinstance(row, dict):
                raise LetterError('invalid_source')
            for field in fields:
                add(f'profile.{section}.{i}.{field}', row.get(field))
    snap = saved['snapshot']
    vacancy = {k: snap.get(k, '') for k in ('title','company','description','requirements')}
    # Validate title/company without allowing control characters into export headings.
    vacancy['title'] = text(vacancy['title'], 500, multiline=False)
    vacancy['company'] = text(vacancy['company'], 500, blank=True, multiline=False)
    source = {'schema': SOURCE_VERSION, 'saved_vacancy_id': saved['id'],
              'vacancy_snapshot_hash': saved['snapshot_hash'], 'vacancy': vacancy,
              'profile_version': profile_version, 'profile_hash': profile_hash,
              'candidate_origin': 'user_confirmed_profile', 'facts': facts,
              'omitted_fact_ids': omitted, 'match': None, 'match_reason': 'real_data_match_not_available'}
    if len(canonical(source).encode('utf-8')) > MAX_SOURCE_BYTES:
        raise LetterError('source_too_large')
    return source
