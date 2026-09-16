"""Deterministic mathematics, pinned evidence semantics and prose isolation."""
from dataclasses import replace
from itertools import permutations
from pathlib import Path
import copy
import json
import pytest
from domain.vacancy_match import MatchRequirement, MatchError, calculate_match
from services.ai.match_validation import validate_match
from services.ai.registry import ContractRegistry, ContractError, ROOT


def case(language='ru'):
    fid = 'vacancy-match-'+language+'-01'
    fixture, schema = ContractRegistry().load(fid)
    return json.loads((ROOT/('prompts/matching/reference/'+fid+'.json')).read_text()), fixture, schema


@pytest.mark.parametrize('language,score,matched,total,mandatory', [('ru',67,6,9,['v4']),('en',71,5,7,['v3'])])
def test_fixed_examples_match_accepted_benchmark(language, score, matched, total, mandatory):
    output = validate_match(*case(language))
    assert output['summary']['score_percent'] == score
    assert output['summary']['matched_weight'] == matched
    assert output['summary']['total_weight'] == total
    assert output['summary']['mandatory_unresolved_ids'] == mandatory
    assert output['summary']['verdict'] == 'partial'
    assert {r['status'] for r in output['requirements']} == {'matched','unverified'}
    assert output['summary']['mismatch_weight'] == 0  # Unknown is not lack of skill.


def test_score_is_order_independent_and_uses_exact_half_even_rounding():
    rows = [MatchRequirement('v1','mandatory',1,'matched'), MatchRequirement('v2','preferred',7,'unverified')]
    results = [calculate_match(list(order)) for order in permutations(rows)]
    assert results[0] == results[1] and results[0]['score_percent'] == 12  # 12.5, banker's rounding.
    other = [replace(rows[0], weight=3), replace(rows[1], weight=5)]
    assert calculate_match(other)['score_percent'] == 38  # 37.5


def test_mandatory_unknown_never_hidden_by_high_score():
    rows = [MatchRequirement('v1','preferred',99,'matched'), MatchRequirement('v2','mandatory',1,'unverified')]
    output = calculate_match(rows)
    assert output['score_percent'] == 99 and output['verdict'] != 'strong'
    assert output['mandatory_unresolved_ids'] == ['v2']


def test_explicit_mismatch_and_unknown_have_different_coverage():
    rows = [MatchRequirement('v1','mandatory',2,'mismatch'), MatchRequirement('v2','preferred',1,'unverified')]
    output = calculate_match(rows)
    assert output['score_percent'] == 0 and output['evidence_coverage_percent'] == 67
    assert output['mismatch_weight'] == 2 and output['unverified_weight'] == 1
    known = calculate_match([MatchRequirement('v1','mandatory',1,'matched')])
    assert known['verdict'] == 'strong' and known['score_percent'] == 100


@pytest.mark.parametrize('rows', [[], [MatchRequirement('v1','mandatory',True,'matched')],
    [MatchRequirement('v1','mandatory',0,'matched')], [MatchRequirement('v1','mandatory',101,'matched')],
    [MatchRequirement('v1','mandatory',1.5,'matched')], [MatchRequirement('v1','optional',1,'matched')],
    [MatchRequirement('v1','mandatory',1,'probable')],
    [MatchRequirement('v1','mandatory',1,'matched')]*2,
    [MatchRequirement(str(i),'mandatory',1,'matched') for i in range(65)]])
def test_invalid_weight_empty_duplicate_unknown_status_fail_closed(rows):
    with pytest.raises(MatchError):
        calculate_match(rows)


@pytest.mark.parametrize('defect', ['missing','duplicate','unknown','wrong_source','missing_candidate','duplicate_evidence','invented_skill','extra_score'])
def test_classifier_contract_rejects_unsafe_structures(defect):
    raw, fixture, schema = case()
    if defect == 'missing': raw['gaps'].pop()
    elif defect == 'duplicate': raw['matched_requirements'].append(copy.deepcopy(raw['matched_requirements'][0]))
    elif defect == 'unknown': raw['gaps'][0]['requirement_id'] = 'v999'
    elif defect == 'wrong_source': raw['matched_requirements'][0]['evidence_ids'] = ['v1','c4']
    elif defect == 'missing_candidate': raw['matched_requirements'][0]['evidence_ids'] = ['v1']
    elif defect == 'duplicate_evidence': raw['gaps'][0]['evidence_ids'].append(raw['gaps'][0]['evidence_ids'][0])
    elif defect == 'invented_skill': raw['matched_requirements'].append(raw['gaps'].pop(0))
    elif defect == 'extra_score': raw['match_score'] = 100
    with pytest.raises(ContractError):
        validate_match(raw,fixture,schema)


def test_model_prose_and_verdict_cannot_override_source_evidence():
    raw, fixture, schema = case('en')
    expected = validate_match(raw, fixture, schema)
    raw['verdict'] = 'strong'
    raw['recommendation'] = 'SECRET MODEL TEXT: guaranteed offer at 100 percent, invented skills.'
    for row in raw['matched_requirements'] + raw['gaps']:
        row['explanation'] = 'SECRET MODEL TEXT <script>alert(1)</script> invented skill'
        row['requirement'] = 'SECRET MODEL TEXT'
    raw['caveats'] = [{'text':'SECRET MODEL TEXT', 'evidence_ids':['c1']}]
    actual = validate_match(raw, fixture, schema)
    assert actual == expected
    assert 'SECRET MODEL TEXT' not in json.dumps(actual)
    assert actual['summary']['score_percent'] == 71
    assert actual['summary']['mandatory_unresolved_ids'] == ['v3']


def test_requirement_rows_are_verbatim_source_quotes_not_model_claims():
    output, fixture, schema = case('ru')
    result = validate_match(output, fixture, schema)
    facts = {f['id']:f['text'] for f in fixture['source_facts']}
    for row in result['requirements']:
        assert row['requirement'] == facts[row['requirement_id']]
        for item in row['evidence']:
            assert item['text'] == facts[item['id']]
