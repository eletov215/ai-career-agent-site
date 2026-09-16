"""Pinned AI-003 reference graphs. This module has no network/provider access."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator
from domain.resume_interview import FIXTURE_IDS, INTERVIEW_VERSION, InterviewError

ROOT = Path(__file__).resolve().parents[2]


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def content_hash(value) -> str:
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()


class InterviewReferenceRegistry:
    def __init__(self, root: Path = ROOT):
        self.root = Path(root)

    def _read(self, relative: str) -> dict:
        try:
            manifest = json.loads((self.root / 'services/ai/interview_reference_manifest.json').read_text())
            expected = manifest['files'][relative]
            raw = (self.root / relative).read_bytes().replace(b'\r\n', b'\n')
            if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError
            return json.loads(raw)
        except (OSError, KeyError, ValueError, TypeError):
            raise InterviewError('invalid_reference') from None

    def validate_snapshot(self, source: dict, expected_hash: str) -> dict:
        schema = self._read('schemas/interview/reference_v1.schema.json')
        if not Draft202012Validator(schema).is_valid(source) or content_hash(source) != expected_hash:
            raise InterviewError('invalid_reference')
        nodes = source['nodes']
        if source['contract_version'] != INTERVIEW_VERSION or source['start_node'] not in nodes or 'review' in nodes:
            raise InterviewError('invalid_reference')
        visited = set()

        def walk(node_id: str, trail: tuple[str, ...]):
            if node_id == 'review':
                return
            if node_id not in nodes or node_id in trail or len(trail) >= 8:
                raise InterviewError('invalid_reference')
            visited.add(node_id)
            node = nodes[node_id]
            ids = [c['id'] for c in node['choices']]
            if len(ids) != len(set(ids)) or not any(c['kind'] == 'skip' for c in node['choices']):
                raise InterviewError('invalid_reference')
            for choice in node['choices']:
                if choice['kind'] == 'skip' and choice['fact_ids']:
                    raise InterviewError('invalid_reference')
                for fid in choice['fact_ids']:
                    fact = source['facts'].get(fid)
                    # Extractive-only final statements: each is explicitly present
                    # in the selected synthetic answer, not inferred from a hint.
                    if fact is None or fact['text'] not in choice['text']:
                        raise InterviewError('invalid_reference')
                walk(choice['next'], (*trail, node_id))

        walk(source['start_node'], ())
        if visited != set(nodes):
            raise InterviewError('invalid_reference')
        return source

    def load(self, fixture_id: str) -> tuple[dict, str]:
        if fixture_id not in FIXTURE_IDS:
            raise InterviewError('invalid_reference')
        source = self._read(f'prompts/interview/reference/{fixture_id}.json')
        if source.get('fixture_id') != fixture_id:
            raise InterviewError('invalid_reference')
        digest = content_hash(source)
        return self.validate_snapshot(source, digest), digest
