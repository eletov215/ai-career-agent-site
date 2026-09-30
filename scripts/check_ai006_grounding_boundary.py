#!/usr/bin/env python3
"""Verify the additive candidate-fit grounding successor boundary."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = 'docs/evidence/ai-006-grounding-hardening/change_boundary.json'
CONTRACT = 'services/ai/letter_contract.py'
SOURCE_MAIN_SHA = 'ba7288518a3dab13878f610bbd9f8f6f38d66019'
PREVIOUS_SHA256 = '0cc6d87b2390b12c0145025819f85099175b30880e005e8a3a039618a9bffd86'


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path = ROOT) -> list[str]:
    try:
        evidence = json.loads((root/EVIDENCE).read_text())
        rows = evidence.get('reviewed_runtime_changes', {})
        expected_metadata = {
            'package':'AI-006-GROUNDING-HARDENING',
            'release':'candidate-fit-grounding-successor',
            'source_main_sha':SOURCE_MAIN_SHA,
            'provider_calls':0,
            'REAL_DATA_SUPPORTED':False,
            'real_data_alice':'CLOSED',
            'legal_state':'DRAFT / NOT_ACTIVE',
            'production_schema':'unchanged',
        }
        if any(evidence.get(key) != value for key, value in expected_metadata.items()):
            raise ValueError('Invalid grounding successor metadata')
        if set(rows) != {CONTRACT}:
            raise ValueError('Invalid grounding successor scope')
        row = rows[CONTRACT]
        if (set(row) != {'previous_sha256','current_sha256'}
                or row['previous_sha256'] != PREVIOUS_SHA256
                or row['current_sha256'] != _sha256(root/CONTRACT)):
            raise ValueError('Invalid grounding hash transition')
        contract = (root/CONTRACT).read_text()
        required = (
            "'validation_candidate_claim_grounding'",
            "len(refs) != 1",
            "def _grounding_text(value: str) -> str:",
            "return ' '.join(value.split())",
            "_grounding_text(refs[0]['quote']) != _grounding_text(facts[refs[0]['id']])",
            "_grounding_text(prose) != _grounding_text(refs[0]['quote'])",
            'Each candidate_fit paragraph uses exactly one candidate fact.',
            'must copy the complete supporting candidate fact',
            'Preserve every non-whitespace character and token in the same order.',
            'Whitespace runs (spaces, tabs, and newlines) may be collapsed to one normal space',
            'whitespace-only normalization is the only permitted transformation',
            'excerpt, omit or reorder words, translate, paraphrase, or semantically rewrite',
            'paraphrase candidate experience',
            'Use a separate candidate_fit paragraph for each additional fact.',
            'requested language applies to model-authored framing',
            'Keep every candidate_fit fact in its source language',
            "if p['kind'] in ('opening','motivation','closing')",
            'MAX_PARAGRAPH_TEXT = 1800',
            "BODY_LIMITS = {'short':1800, 'full':6000}",
            "MAX_PARAGRAPHS = {'short':6, 'full':11}",
            "normalized_fact_lengths = [len(_grounding_text(f['text'])) for f in facts]",
            "any(fact_length > MAX_PARAGRAPH_TEXT for fact_length in normalized_fact_lengths)",
            "len(facts) + 2 > MAX_PARAGRAPHS[length]",
            "framing_min = 8 if language == 'ru' else 2",
            "sum(normalized_fact_lengths) + framing_min",
            "any(MARKUP.search(f['text']) or PRIOR_FAMILIARITY.search(f['text']) for f in facts)",
            "set(candidate_fit_ids) != set(facts)",
            "candidate_fit_ids.count(fact_id) != 1",
            "def _safe_framing(value: str, kind: str, language: str,",
            "FRAMING_PATTERNS[language][kind]",
            "candidate facts and qualifications must appear only in candidate_fit",
            "not _safe_framing(prose, p['kind'], contract.language",
            "not _safe_framing(subject, 'subject', contract.language",
            "elif refs:",
            "raise LetterError('input_limit')",
            "raise LetterError('invalid_source')",
        )
        if not all(fragment in contract for fragment in required):
            raise ValueError('Grounding contract is incomplete')
        return []
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return ['AI-006 grounding hardening successor boundary is not verified']


if __name__ == '__main__':
    errors = validate()
    print(json.dumps({'package':'AI-006-GROUNDING-HARDENING', 'ok':not errors,
                      'provider_calls':0, 'errors':errors}, indent=2))
    raise SystemExit(bool(errors))
