"""AI-003 offline state, grounding, ownership, confirmation and concurrency tests."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
import copy
import json
from uuid import uuid4

import pytest
from sqlalchemy import delete, event, func, select
from models import Base, User, ResumeDraft, ResumeVersion, CareerProfile
from models.ai import AIUsageEvent
from models.resume_interview import ResumeInterviewSession, ResumeInterviewEvent
from database import create_database
from domain.resume_interview import InterviewCommand, InterviewError, StartInterviewRequest, replay_path
from repositories.resume_interview import ResumeInterviewRepository
from repositories.privacy import PrivacyRepository
from services.resume_interview import ResumeInterviewService
from services.resume_drafts import ResumeDraftService
from repositories.resume_drafts import ResumeDraftRepository
from services.ai.interview_reference import InterviewReferenceRegistry, content_hash, ROOT

NOW = 1789560000


@pytest.fixture
def env(tmp_path):
    db = create_database(f'sqlite:///{tmp_path}/interview.db')
    Base.metadata.create_all(db.engine)
    owner, other = str(uuid4()), str(uuid4())
    with db.session() as session, session.begin():
        for uid in (owner, other):
            session.add(User(id=uid, status='active', email_verified_at=NOW, password_hash='test-only', created_at=NOW, updated_at=NOW))
    service = ResumeInterviewService(ResumeInterviewRepository(db), fingerprint_key='test-only', clock=lambda: NOW)
    yield db, owner, other, service
    db.dispose()


def start(env, language='ru', key=None, owner=None):
    service = env[-1]
    fid = f'resume-interview-{language}-01'
    return service.start(StartInterviewRequest(owner or env[1], fid, service.registry.load(fid)[1], key or str(uuid4())))


def command(env, result, action='answer', **kwargs):
    return InterviewCommand(user_id=env[1], session_id=result['id'], expected_revision=result['revision'],
        source_hash=result['source_hash'], operation_key=str(uuid4()), action=action, **kwargs)


def answer(env, result, choice):
    return env[-1].execute(command(env, result, node_id=result['current_node_id'], choice_id=choice))


def review(env, language='ru', path=('specific', 'measured', 'verified')):
    result = start(env, language)
    for choice in path:
        result = answer(env, result, choice)
    assert result['status'] == 'review'
    return result


def confirm_command(env, result, selected=None, key=None):
    cmd = command(env, result, 'confirm', selected_fact_ids=tuple(selected or [f['id'] for f in result['suggestions']]), confirm=True)
    return replace(cmd, operation_key=key) if key else cmd


@pytest.mark.parametrize('language', ['ru', 'en'])
def test_adaptive_weak_answer_and_metric_branches(env, language):
    first = start(env, language)
    weak = answer(env, first, 'vague')
    assert weak['current_node_id'] == 'clarify' and not weak['suggestions']
    strong = answer(env, weak, 'specific')
    assert strong['current_node_id'] == 'outcome'
    metric = answer(env, strong, 'measured')
    assert metric['current_node_id'] == 'metric'
    assert 'metric' not in [f['id'] for f in metric['suggestions']]
    uncertain = answer(env, metric, 'uncertain')
    assert uncertain['current_node_id'] == 'qualitative'
    final = answer(env, uncertain, 'documented')
    assert final['status'] == 'review' and not any(f['id'] == 'metric' for f in final['suggestions'])
    assert all(f['text'] in f['evidence'] for f in final['suggestions'])
    db, owner, _, _ = env
    with db.session() as session:
        draft = session.get(ResumeDraft, first['draft_id'])
        assert 'achievements' not in json.loads(draft.state_json)['answers']
        assert draft.revision == 1
        assert session.scalar(select(func.count()).select_from(CareerProfile)) == 0
        assert session.scalar(select(func.count()).select_from(AIUsageEvent)) == 0


@pytest.mark.parametrize('language', ['ru', 'en'])
def test_confirm_is_atomic_versioned_extractive_and_idempotent(env, language):
    result = review(env, language)
    cmd = confirm_command(env, result)
    final = env[-1].execute(cmd)
    again = env[-1].execute(cmd)
    assert final == again and final['status'] == 'confirmed'
    expected = '\n'.join(f['text'] for f in result['suggestions'])
    assert final['confirmed_text'] == expected
    with env[0].session() as session:
        draft = session.get(ResumeDraft, result['draft_id'])
        version = session.get(ResumeVersion, final['confirmed_version_id'])
        assert json.loads(draft.state_json)['answers']['achievements'] == expected
        assert draft.revision == 2 and version.snapshot_json == draft.state_json
        assert session.scalar(select(func.count()).select_from(ResumeVersion)) == 1
        assert session.scalar(select(func.count()).select_from(CareerProfile)) == 0
    env[0].dispose()
    assert env[-1].get(env[1], final['id'])['confirmed_text'] == expected
    with pytest.raises(InterviewError, match='already_confirmed'):
        env[-1].execute(command(env, final, 'rewind', answer_index=0))


def test_user_can_exclude_statement_before_confirmation(env):
    result = review(env)
    final = env[-1].execute(confirm_command(env, result, ['contribution']))
    assert final['confirmed_text'] == result['suggestions'][0]['text']
    assert '12' not in final['confirmed_text']
    assert [f['id'] for f in final['suggestions']] == ['contribution']


def test_source_and_references_never_use_provider(env, monkeypatch):
    from services.ai.service import AIService
    def forbidden(*args, **kwargs):
        raise AssertionError('AI-003 reference mode must not dispatch a provider')
    monkeypatch.setattr(AIService, 'generate', forbidden)
    result = review(env)
    assert env[-1].execute(confirm_command(env, result))['status'] == 'confirmed'


def test_existing_real_resume_and_profile_are_not_modified(env):
    db, owner, _, svc = env
    drafts = ResumeDraftService(ResumeDraftRepository(db))
    original = drafts.create(user_id=owner, title='Real draft', display_name='Private Name')
    before = drafts.get(user_id=owner, draft_id=original.id)
    result = review(env)
    assert result['draft_id'] != original.id
    svc.execute(confirm_command(env, result))
    after = drafts.get(user_id=owner, draft_id=original.id)
    assert before.state == after.state and before.revision == after.revision
    assert 'Private Name' not in json.dumps(svc.get(owner, result['id']))


def test_rewind_keeps_audit_but_drops_old_answers_and_numbers(env):
    result = review(env)
    previous_events = copy.deepcopy(result['events'])
    revised = env[-1].execute(command(env, result, 'rewind', answer_index=1))
    assert revised['status'] == 'active' and revised['current_node_id'] == 'outcome'
    assert len(revised['conversation']) == 1
    revised = answer(env, revised, 'unknown')
    revised = answer(env, revised, 'documented')
    assert revised['events'][:len(previous_events)] == previous_events
    final = env[-1].execute(confirm_command(env, revised))
    assert '12' not in final['confirmed_text']
    assert [f['id'] for f in final['suggestions']] == ['contribution', 'qualitative']
    assert any('12' in str(e) for e in final['events'])  # Historical evidence is not erased.


def test_all_skips_create_no_fake_achievement(env):
    result = review(env, path=('skip', 'skip', 'skip'))
    assert not result['suggestions']
    with pytest.raises(InterviewError, match='invalid_selection'):
        env[-1].execute(command(env, result, 'confirm', confirm=True))
    assert env[-1].get(env[1], result['id'])['status'] == 'review'


def test_needs_confirmation_and_only_selected_supported_facts(env):
    result = review(env)
    cmd = confirm_command(env, result)
    for changes, error in (
        ({'confirm': False}, 'confirmation_required'),
        ({'selected_fact_ids': ('qualitative',)}, 'invalid_selection'),
        ({'selected_fact_ids': ('contribution', 'contribution')}, 'invalid_selection'),
        ({'selected_fact_ids': ()}, 'invalid_selection'),
    ):
        with pytest.raises(InterviewError, match=error):
            env[-1].execute(replace(cmd, **changes))
    with env[0].session() as session:
        assert session.scalar(select(func.count()).select_from(ResumeVersion)) == 0


def test_cannot_confirm_before_review_or_answer_future_question(env):
    result = start(env)
    with pytest.raises(InterviewError, match='review_required'):
        env[-1].execute(command(env, result, 'confirm', selected_fact_ids=('contribution',), confirm=True))
    with pytest.raises(InterviewError, match='unexpected_question'):
        env[-1].execute(command(env, result, node_id='metric', choice_id='verified'))


@pytest.mark.parametrize('changes', [
    {'user_id': 'bad'}, {'fixture_id': '../../etc/passwd'}, {'expected_source_hash': '0'*64},
    {'operation_key': ''}, {'operation_key': 'contains spaces and text'},
])
def test_invalid_start_is_fail_closed(env, changes):
    svc = env[-1];fid = 'resume-interview-ru-01'
    request = StartInterviewRequest(env[1], fid, svc.registry.load(fid)[1], str(uuid4()))
    with pytest.raises(InterviewError):
        svc.start(replace(request, **changes))
    assert not svc.history(env[1])
    with env[0].session() as session:
        assert session.scalar(select(func.count()).select_from(ResumeDraft)) == 0


@pytest.mark.parametrize('changes', [
    {'action': []}, {'action': 'invent'}, {'expected_revision': True}, {'expected_revision': -1},
    {'source_hash': None}, {'confirm': 'yes'}, {'node_id': []}, {'choice_id': {}},
    {'selected_fact_ids': ['contribution']}, {'answer_index': 1}, {'selected_fact_ids': ('metric',)},
])
def test_invalid_command_never_mutates(env, changes):
    result = start(env)
    cmd = command(env, result, node_id='contribution', choice_id='specific')
    with pytest.raises(InterviewError):
        env[-1].execute(replace(cmd, **changes))
    assert env[-1].get(env[1], result['id'])['revision'] == 1


def test_arbitrary_dict_and_text_are_not_requests(env):
    for method in (env[-1].start, env[-1].execute):
        with pytest.raises(InterviewError, match='invalid_request'):
            method({'resume': 'private user text'})


@pytest.mark.parametrize('status, verified', [('pending', True), ('active', False), ('deleted', True)])
def test_start_requires_active_verified_user(env, status, verified):
    with env[0].session() as session, session.begin():
        user = session.get(User, env[1]);user.status = status;user.email_verified_at = NOW if verified else None
    with pytest.raises(InterviewError, match='verified_account_required'):
        start(env)


def test_other_owner_cannot_read_write_or_attach_draft(env):
    result = start(env)
    with pytest.raises(InterviewError, match='not_found'):
        env[-1].get(env[2], result['id'])
    assert not env[-1].for_draft(env[2], result['draft_id'])
    cmd = replace(command(env, result, node_id='contribution', choice_id='specific'), user_id=env[2])
    with pytest.raises(InterviewError, match='not_found'):
        env[-1].execute(cmd)


def test_duplicate_start_and_parallel_turn_are_serialized(env):
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: start(env, key=key), range(3)))
    assert len({r['id'] for r in results}) == 1
    result = results[0]
    cmd = command(env, result, node_id='contribution', choice_id='specific')
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda _: env[-1].execute(cmd), range(3)))
    assert {r['revision'] for r in results} == {2}
    with pytest.raises(InterviewError, match='idempotency_conflict'):
        env[-1].execute(replace(cmd, choice_id='vague'))
    with pytest.raises(InterviewError, match='stale_interview'):
        env[-1].execute(replace(cmd, operation_key=str(uuid4())))
    # Same start key cannot choose a different language/fixture; different owners are independent.
    with pytest.raises(InterviewError, match='idempotency_conflict'):
        start(env, 'en', key=key)
    assert start(env, key=key, owner=env[2])['id'] != result['id']


def test_parallel_different_answers_have_one_winner(env):
    result = start(env)
    def attempt(choice):
        try:
            return answer(env, result, choice)
        except InterviewError as e:
            return str(e)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ['vague', 'specific']))
    assert sum(isinstance(x, dict) for x in results) == 1
    assert 'stale_interview' in results


def test_manual_draft_edit_blocks_final_overwrite(env):
    result = review(env)
    drafts = ResumeDraftService(ResumeDraftRepository(env[0]))
    draft = drafts.get(user_id=env[1], draft_id=result['draft_id'])
    state = copy.deepcopy(draft.state);state['answers']['achievements'] = 'Manually edited content'
    drafts.save(user_id=env[1], draft_id=draft.id, expected_revision=draft.revision, state=state)
    with pytest.raises(InterviewError, match='stale_draft'):
        env[-1].execute(confirm_command(env, result))
    after = drafts.get(user_id=env[1], draft_id=draft.id)
    assert after.state['answers']['achievements'] == 'Manually edited content'
    assert env[-1].get(env[1], result['id'])['status'] == 'review'


def test_event_failure_rolls_back_draft_version_and_confirmation(env):
    result = review(env)
    def fail(mapper, connection, target):
        if target.kind == 'confirmed':
            raise RuntimeError('simulated transaction failure')
    event.listen(ResumeInterviewEvent, 'before_insert', fail)
    try:
        with pytest.raises(RuntimeError, match='simulated'):
            env[-1].execute(confirm_command(env, result))
    finally:
        event.remove(ResumeInterviewEvent, 'before_insert', fail)
    with env[0].session() as session:
        assert session.get(ResumeDraft, result['draft_id']).revision == 1
        assert session.scalar(select(func.count()).select_from(ResumeVersion)) == 0
    assert env[-1].get(env[1], result['id'])['status'] == 'review'


def test_manifest_tamper_and_unknown_fact_fail_closed(env, tmp_path):
    import shutil
    for folder in ('prompts/interview', 'schemas/interview'):
        shutil.copytree(ROOT/folder, tmp_path/folder)
    (tmp_path/'services/ai').mkdir(parents=True)
    shutil.copy2(ROOT/'services/ai/interview_reference_manifest.json', tmp_path/'services/ai')
    file = tmp_path/'prompts/interview/reference/resume-interview-ru-01.json'
    file.write_text('{}')
    with pytest.raises(InterviewError, match='invalid_reference'):
        InterviewReferenceRegistry(tmp_path).load('resume-interview-ru-01')
    source, digest = env[-1].registry.load('resume-interview-ru-01')
    source['nodes']['contribution']['choices'][0]['fact_ids'] = ['metric']
    with pytest.raises(InterviewError, match='invalid_reference'):
        env[-1].registry.validate_snapshot(source, content_hash(source))
    source, digest = env[-1].registry.load('resume-interview-ru-01')
    source['nodes']['metric']['choices'][0]['next'] = 'contribution'
    with pytest.raises(InterviewError, match='invalid_reference'):
        env[-1].registry.validate_snapshot(source, content_hash(source))


def test_stale_source_does_not_change_history(env):
    result = start(env)
    cmd = command(env, result, node_id='contribution', choice_id='specific')
    with pytest.raises(InterviewError, match='stale_source'):
        env[-1].execute(replace(cmd, source_hash='0'*64))
    assert env[-1].get(env[1], result['id'])['revision'] == 1


def test_privacy_exports_interview_history_without_keys_and_deletes_owner_only(env):
    result = review(env);env[-1].execute(confirm_command(env, result))
    other = start(env, owner=env[2])
    privacy = PrivacyRepository(env[0])
    exported, _ = privacy.export_snapshot(env[1], expected_password_hash='test-only')
    entries = exported['resume_interviews']
    assert len(entries) == 1 and entries[0]['id'] == result['id']
    assert len(entries[0]['events']) == 5 and entries[0]['confirmed_version_id']
    assert not any(key in json.dumps(entries) for key in ('operation_hash', 'request_hash', 'operation_key'))
    counts = privacy.delete_account(env[1], expected_password_hash='test-only', now=NOW)
    assert counts['resume_interview_sessions'] == 1
    assert env[-1].get(env[2], other['id'])
    with env[0].session() as session:
        assert session.scalar(select(func.count()).select_from(ResumeInterviewEvent).where(ResumeInterviewEvent.session_id == result['id'])) == 0
        assert not session.get(ResumeDraft, result['draft_id'])


def test_delete_draft_cascades_interview_and_events(env):
    result = start(env)
    assert ResumeDraftRepository(env[0]).delete(user_id=env[1], draft_id=result['draft_id'])
    assert not env[-1].history(env[1])
    with env[0].session() as session:
        assert session.scalar(select(func.count()).select_from(ResumeInterviewEvent)) == 0


def test_event_limit_is_bounded_without_losing_history(env):
    result = start(env)
    for _ in range(29):
        result = answer(env, result, 'vague')
        result = env[-1].execute(command(env, result, 'rewind', answer_index=0))
    assert result['revision'] == 59
    result = answer(env, result, 'vague')
    with pytest.raises(InterviewError, match='history_limit'):
        env[-1].execute(command(env, result, 'rewind', answer_index=0))
    assert len(env[-1].get(env[1], result['id'])['events']) == 60
