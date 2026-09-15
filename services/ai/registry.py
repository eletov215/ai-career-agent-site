"""Immutable fixture-only registry. No arbitrary user text is accepted in AI-001."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from domain.ai import CONTRACT, TASKS

ROOT = Path(__file__).resolve().parents[2]

class ContractError(ValueError):
    pass

class ContractRegistry:
    def __init__(self, root: Path = ROOT):
        self.root = root
        self.manifest = json.loads((root/"services/ai/contract_manifest.json").read_text())

    def _read(self, relative: str):
        expected = self.manifest["files"].get(relative)
        if not expected:
            raise ContractError("Unknown contract")
        raw = (self.root/relative).read_bytes()
        # Windows Git checkout is allowed; content is still pinned.
        if hashlib.sha256(raw).hexdigest()!=expected and hashlib.sha256(raw.replace(b"\r\n",b"\n")).hexdigest()!=expected:
            raise ContractError("Contract checksum mismatch")
        return json.loads(raw)

    def load(self, fixture_id: str) -> tuple[dict, dict]:
        if not isinstance(fixture_id,str) or not re.fullmatch(r"[a-z-]{5,45}-[0-9]{2}",fixture_id):
            raise ContractError("Unknown synthetic fixture")
        fixture=self._read(f"prompts/ai/{CONTRACT}/{fixture_id}.json")
        if fixture.get("synthetic") is not True or fixture.get("case_id")!=fixture_id or fixture.get("task") not in TASKS or fixture.get("language") not in {"ru","en"}:
            raise ContractError("Invalid synthetic fixture")
        schema=self._read(f"schemas/ai/{CONTRACT}/{fixture['task']}.schema.json")
        return fixture,schema

def validate_output(content: str, schema: dict) -> dict:
    # Full JSON Schema implementation; duplicate keys and NaN are not JSON contracts.
    from jsonschema import Draft202012Validator
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError
            result[key]=value
        return result
    try:
        if not isinstance(content,str) or len(content.encode("utf-8"))>131072:
            raise ValueError
        value=json.loads(content,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if not isinstance(value,dict) or not Draft202012Validator(schema).is_valid(value):
            raise ValueError
        return value
    except (ValueError,TypeError,RecursionError):
        raise ContractError("Invalid structured output") from None
