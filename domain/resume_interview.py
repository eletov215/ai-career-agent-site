"""AI-003 typed requests and pure, bounded conversation transitions.

Only reference answer IDs are accepted. An answer is not a canonical career fact.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

INTERVIEW_VERSION = 'reference-interview-v1'
FIXTURE_IDS = ('resume-interview-ru-01', 'resume-interview-en-01')
MAX_SESSIONS_PER_OWNER = 50
MAX_EVENTS_PER_SESSION = 60


class InterviewError(ValueError):
    """A safe machine reason; routes translate it without leaking input."""


@dataclass(frozen=True, slots=True)
class StartInterviewRequest:
    user_id: str
    fixture_id: str
    expected_source_hash: str
    operation_key: str


@dataclass(frozen=True, slots=True)
class InterviewCommand:
    user_id: str
    session_id: str
    expected_revision: int
    source_hash: str
    operation_key: str
    action: str
    node_id: str | None = None
    choice_id: str | None = None
    answer_index: int | None = None
    selected_fact_ids: tuple[str, ...] = ()
    confirm: bool = False


def replay_path(source: dict, answers: list[dict]) -> tuple[str, list[dict], list[str]]:
    """Rebuild from the pinned graph, never trust client or stored derived facts."""
    if not isinstance(answers, list) or len(answers) > 8:
        raise InterviewError('invalid_history')
    current = source['start_node']
    conversation: list[dict[str, Any]] = []
    facts: list[str] = []
    for item in answers:
        if not isinstance(item, dict) or set(item) != {'node_id', 'choice_id'}:
            raise InterviewError('invalid_history')
        if current == 'review' or item['node_id'] != current:
            raise InterviewError('invalid_history')
        node = source['nodes'][current]
        choice = next((c for c in node['choices'] if c['id'] == item['choice_id']), None)
        if choice is None:
            raise InterviewError('invalid_history')
        conversation.append({'node_id': current, 'choice_id': choice['id'],
                             'question': node['question'], 'goal': node['goal'],
                             'answer': choice['text'], 'kind': choice['kind'],
                             'fact_ids': list(choice['fact_ids'])})
        for fact in choice['fact_ids']:
            if fact not in facts:
                facts.append(fact)
        current = choice['next']
    return current, conversation, facts


def final_text(source: dict, answers: list[dict], selected: tuple[str, ...]) -> str:
    node, _conversation, available = replay_path(source, answers)
    if node != 'review':
        raise InterviewError('review_required')
    if not selected or len(selected) != len(set(selected)) or not set(selected) <= set(available):
        raise InterviewError('invalid_selection')
    # Preserve source ordering rather than client ordering. No paraphrase, inferred
    # benefit or unverified number can enter this deterministic reference result.
    return '\n'.join(source['facts'][fid]['text'] for fid in available if fid in selected)
