"""AI-003 application boundary: synthetic references, never arbitrary user text."""
from __future__ import annotations

from dataclasses import asdict
import copy
import hashlib
import hmac
import re
import time
from uuid import UUID

from domain.resume_interview import (
    FIXTURE_IDS, InterviewCommand, InterviewError, StartInterviewRequest, final_text, replay_path,
)
from repositories.resume_interview import ResumeInterviewRepository
from services.ai.interview_reference import InterviewReferenceRegistry, canonical_json, content_hash
from services.resume_drafts import (
    RESUME_QUESTIONS, default_resume_state, normalise_resume_state, resume_completion_percent,
)

_KEY_RE = re.compile(r'^[A-Za-z0-9_-]{16,96}$')
_HASH_RE = re.compile(r'^[a-f0-9]{64}$')


def _uuid(value) -> str:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
        return value
    except (ValueError, TypeError, AttributeError):
        raise InterviewError('invalid_request') from None


def _draft_payload(state: dict) -> dict:
    normalized = normalise_resume_state(state)
    return {'state_json': canonical_json(normalized), 'content_hash': content_hash(normalized),
            'completion_percent': resume_completion_percent(normalized)}


class ResumeInterviewService:
    def __init__(self, repository: ResumeInterviewRepository, *, fingerprint_key: str,
                 registry: InterviewReferenceRegistry | None = None, clock=time.time):
        self.repository = repository
        self.registry = registry or InterviewReferenceRegistry()
        self.clock = clock
        self._key = fingerprint_key.encode('utf-8')

    def _operation(self, user_id: str, key: str, scope: str) -> str:
        _uuid(user_id)
        if not isinstance(key, str) or not _KEY_RE.fullmatch(key):
            raise InterviewError('invalid_request')
        return hmac.new(self._key, f'AI-003:{scope}:{user_id}:{key}'.encode('utf-8'), hashlib.sha256).hexdigest()

    def choices(self) -> list[dict]:
        result = []
        for fid in FIXTURE_IDS:
            source, digest = self.registry.load(fid)
            result.append({'fixture_id': fid, 'source_hash': digest, 'title': source['title'],
                           'language': source['language'], 'facts': list(source['draft_answers'].values())})
        return result

    def _present(self, raw: dict) -> dict:
        source = self.registry.validate_snapshot(raw['source'], raw['source_hash'])
        current, conversation, available = replay_path(source, raw['answers'])
        if raw['status'] == 'confirmed':
            confirmation = next((e for e in reversed(raw['events']) if e['kind'] == 'confirmed'), None)
            if confirmation is None or confirmation['revision'] != raw['revision']:
                raise InterviewError('invalid_history')
            selected = confirmation['payload'].get('selected_fact_ids', [])
            try:
                expected_text = final_text(source, raw['answers'], tuple(selected))
            except (InterviewError, TypeError):
                raise InterviewError('invalid_history') from None
            if expected_text != raw['confirmed_text']:
                raise InterviewError('invalid_history')
            available = [fid for fid in available if fid in selected]
        suggestions = []
        for fid in available:
            evidence = next(item for item in conversation if fid in item['fact_ids'])
            suggestions.append({'id': fid, 'text': source['facts'][fid]['text'],
                                'evidence': evidence['answer'], 'question': evidence['question']})
        return {k: raw[k] for k in ('id', 'draft_id', 'fixture_id', 'source_hash', 'contract_version',
                                   'language', 'origin', 'revision', 'status', 'created_at', 'updated_at',
                                   'confirmed_text', 'confirmed_version_id', 'events')} | {
            'title': source['title'], 'source_facts': list(source['draft_answers'].values()),
            'conversation': conversation, 'suggestions': suggestions, 'current_node_id': current,
            'current_question': source['nodes'][current] if current != 'review' else None,
        }

    def start(self, request: StartInterviewRequest) -> dict:
        if not isinstance(request, StartInterviewRequest):
            raise InterviewError('invalid_request')
        operation = self._operation(request.user_id, request.operation_key, 'start')
        source, digest = self.registry.load(request.fixture_id)
        if request.expected_source_hash != digest:
            raise InterviewError('stale_source')
        state = default_resume_state()
        state['answers'] = copy.deepcopy(source['draft_answers'])
        # A fresh synthetic draft only. This also prevents the manual builder's
        # initial greeting from silently autosaving and changing our base revision.
        state['index'] = 3
        state['messages'] = [{'type': 'ai', 'text': RESUME_QUESTIONS[3]}]
        raw = self.repository.start(user_id=request.user_id, operation_hash=operation, source=source,
            source_hash=digest, seed=_draft_payload(state), now=int(self.clock()))
        return self._present(raw)

    def history(self, user_id: str) -> list[dict]:
        return self.repository.list(_uuid(user_id))

    def for_draft(self, user_id: str, draft_id: str) -> str | None:
        return self.repository.for_draft(_uuid(user_id), _uuid(draft_id))

    def get(self, user_id: str, session_id: str) -> dict:
        raw = self.repository.get(_uuid(user_id), _uuid(session_id))
        if raw is None:
            raise InterviewError('not_found')
        return self._present(raw)

    def execute(self, command: InterviewCommand) -> dict:
        if not isinstance(command, InterviewCommand):
            raise InterviewError('invalid_request')
        _uuid(command.session_id)
        operation = self._operation(command.user_id, command.operation_key, 'command')
        if type(command.expected_revision) is not int or command.expected_revision < 1:
            raise InterviewError('invalid_request')
        if not isinstance(command.source_hash, str) or not _HASH_RE.fullmatch(command.source_hash):
            raise InterviewError('invalid_request')
        if not isinstance(command.action, str) or command.action not in {'answer', 'rewind', 'confirm'} or type(command.confirm) is not bool:
            raise InterviewError('invalid_request')
        if not isinstance(command.selected_fact_ids, tuple) or len(command.selected_fact_ids) > 12 or any(
            not isinstance(fid, str) or len(fid) > 48 for fid in command.selected_fact_ids
        ):
            raise InterviewError('invalid_request')
        if command.action == 'answer':
            if not isinstance(command.node_id, str) or not isinstance(command.choice_id, str) or len(command.node_id) > 48 or len(command.choice_id) > 48:
                raise InterviewError('invalid_request')
            if command.answer_index is not None or command.selected_fact_ids or command.confirm:
                raise InterviewError('invalid_request')
        elif command.action == 'rewind':
            if type(command.answer_index) is not int or command.node_id is not None or command.choice_id is not None or command.selected_fact_ids or command.confirm:
                raise InterviewError('invalid_request')
        elif command.node_id is not None or command.choice_id is not None or command.answer_index is not None:
            raise InterviewError('invalid_request')
        # Include the optimistic revision and confirmation semantics in the key's
        # request binding. Reusing a key for another action must never succeed.
        fingerprint = asdict(command)
        fingerprint.pop('operation_key')
        request_digest = content_hash(fingerprint)

        def change(raw: dict, draft_state: dict) -> dict:
            source, current_hash = self.registry.load(raw['fixture_id'])
            if current_hash != raw['source_hash']:
                raise InterviewError('stale_source')
            self.registry.validate_snapshot(raw['source'], raw['source_hash'])
            answers = copy.deepcopy(raw['answers'])
            current, conversation, _facts = replay_path(source, answers)
            if command.action == 'answer':
                if current == 'review' or command.node_id != current:
                    raise InterviewError('unexpected_question')
                node = source['nodes'][current]
                choice = next((c for c in node['choices'] if c['id'] == command.choice_id), None)
                if choice is None:
                    raise InterviewError('invalid_choice')
                answers.append({'node_id': current, 'choice_id': choice['id']})
                next_node, updated, _facts = replay_path(source, answers)
                return {'answers': answers, 'status': 'review' if next_node == 'review' else 'active',
                        'kind': 'skipped' if choice['kind'] == 'skip' else 'answered', 'event': updated[-1]}
            if command.action == 'rewind':
                if command.answer_index < 0 or command.answer_index >= len(answers):
                    raise InterviewError('invalid_request')
                return {'answers': answers[:command.answer_index], 'status': 'active', 'kind': 'rewound',
                        'event': {'answer_index': command.answer_index, 'question': conversation[command.answer_index]['question']}}
            if not command.confirm:
                raise InterviewError('confirmation_required')
            result = final_text(source, answers, command.selected_fact_ids)
            # Explicitly confirmed result changes only achievements in this isolated
            # draft. Profile facts, other resumes and source snapshots are untouched.
            updated_state = copy.deepcopy(draft_state)
            updated_state['answers']['achievements'] = result
            payload = _draft_payload(updated_state)
            return {'answers': answers, 'status': 'confirmed', 'kind': 'confirmed',
                    'confirmed_text': result, 'draft_change': payload,
                    'event': {'selected_fact_ids': list(command.selected_fact_ids), 'text': result}}

        raw = self.repository.transition(user_id=command.user_id, session_id=command.session_id,
            operation_hash=operation, request_hash=request_digest, expected_revision=command.expected_revision,
            source_hash=command.source_hash, change=change, now=int(self.clock()))
        return self._present(raw)
