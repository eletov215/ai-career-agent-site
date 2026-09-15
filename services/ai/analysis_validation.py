"""Feature checks for the two pinned resume cases, not a general truth oracle.

No rewriting/repair of model facts. Missing evidence is not missing skill.
Existing prompt/schema hashes and accepted benchmark code are unchanged.
"""
import json
import re
import unicodedata
from domain.resume_analysis import FIXTURE_IDS
from services.ai.registry import ContractError, validate_output

_NEGATION = re.compile(r"not (?:verified|confirmed)|unverified|no (?:verified|confirmed)|\u043d\u0435 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434|\u043d\u0435\u0442 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434|\u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0438\u0435 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434", re.I)
_TECH = re.compile(r"\b[recsvi]\d+\b|evidence_ids|facts_not_verified|<[^>]+>|https?://|\S+@\S+", re.I)
_ABSOLUTE_GAP = re.compile(r"(?:has|have) no (?:experience|skill)|does not (?:know|have)|cannot|\u043d\u0435 \u0443\u043c\u0435\u0435\u0442|\u043d\u0435 \u0437\u043d\u0430\u0435\u0442|\u043d\u0435 \u0438\u043c\u0435\u0435\u0442 \u043e\u043f\u044b\u0442\u0430", re.I)
_IMPACT = re.compile(r"\b(?:increased|reduced|boosted|saved|achieved|improved|managed|led)\b|\u0443\u0432\u0435\u043b\u0438\u0447\u0438\u043b|\u0441\u043e\u043a\u0440\u0430\u0442\u0438\u043b|\u0441\u043d\u0438\u0437\u0438\u043b|\u0440\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u043b", re.I)
_STOP = {"the", "and", "with", "for", "not", "has", "have", "this", "that", "verified", "confirmed", "experience", "years", "\u043e\u043f\u044b\u0442", "\u043d\u0435\u0442", "\u0433\u043e\u0434\u0430", "\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u043e", "\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u043d\u043e\u0433\u043e"}

def _norm(text):
    return unicodedata.normalize("NFKC", text).casefold().replace("\u0451", "\u0435")

def _words(text):
    text = re.sub(r"\u043a\u043e\u043e\u0440\u0434\u0438\u043d\w*|\u043b\u0438\u0434\u0435\u0440\w*|\u0440\u0443\u043a\u043e\u0432\u043e\u0434\w*|\u0443\u043f\u0440\u0430\u0432\u043b\w*", "leadership", _norm(text))
    return {w[:5] for w in re.findall(r"[^\W_]+", _norm(text)) if len(w) >= 3 and w not in _STOP}

def _numbers(text):
    value = _norm(text)
    for word, number in {"one":"1", "two":"2", "three":"3", "four":"4", "five":"5", "ten":"10", "\u0434\u0432\u0430":"2", "\u0434\u0432\u0443\u0445":"2", "\u0442\u0440\u0438":"3", "\u0442\u0440\u0435\u0445":"3", "\u043f\u044f\u0442\u044c":"5"}.items():
        value = re.sub(r"\b" + word + r"\b", number, value)
    return set(re.findall(r"(?<![\w])\d+(?:[.,]\d+)?(?:\s*%)?", value))

def validate_analysis(content, fixture, schema):
    """Reject structural or fixed-case evidence violations before settlement."""
    if fixture.get("case_id") not in FIXTURE_IDS or fixture.get("synthetic") is not True:
        raise ContractError("Unsupported analysis source")
    output = validate_output(json.dumps(content, ensure_ascii=False, allow_nan=False), schema)
    sources = {f["id"]: f["text"] for f in fixture["source_facts"]}
    unverified = set(fixture["required_unverified_evidence_ids"])
    factual = [output["summary"]]
    all_text = [output["summary"]]
    seen = set()
    for section in ("strengths", "gaps", "recommendations", "facts_not_verified"):
        section_seen = set()
        for row in output[section]:
            ids = row["evidence_ids"]
            if len(ids) != len(set(ids)) or not set(ids) <= sources.keys():
                raise ContractError("Invalid analysis evidence")
            text = " ".join(v for k,v in row.items() if k != "evidence_ids")
            all_text.append(text)
            if not (_words(text) & _words(" ".join(sources[i] for i in ids))):
                raise ContractError("Unlinked analysis finding")
            if section == "strengths":
                cited = _norm(" ".join(sources[i] for i in ids))
                for skill in ("python", "fastapi", "postgresql", "sql", "power bi", "excel", "b1"):
                    pattern = r"\b" + re.escape(skill) + r"\b"
                    if re.search(pattern, _norm(text)) and not re.search(pattern, cited):
                        raise ContractError("Unlinked skill claim")
            if section == "strengths" and set(ids) & unverified:
                raise ContractError("Unverified strength")
            if section in {"gaps", "facts_not_verified"}:
                if not set(ids) & unverified or not _NEGATION.search(_norm(text)) or _ABSOLUTE_GAP.search(text):
                    raise ContractError("Missing evidence is not absence of skill")
            if section != "recommendations":
                factual.append(text)
                if _numbers(text) - _numbers(" ".join(sources[i] for i in ids)):
                    raise ContractError("Unsupported analysis number")
            seen.update(ids);section_seen.update(ids)
        if section in {"gaps", "facts_not_verified"} and not unverified <= section_seen:
            raise ContractError("Missing unverified disclosure")
    if set(sources) - seen:
        raise ContractError("Incomplete analysis evidence")
    if _numbers(output["summary"]) - _numbers(" ".join(sources.values())):
        raise ContractError("Unsupported summary number")
    for text in all_text:
        if _TECH.search(text):
            raise ContractError("Technical or unsafe presentation")
    for text in factual:
        if _IMPACT.search(text):
            raise ContractError("Unsupported analysis impact")
        if fixture["language"] == "en" and re.search(r"[\u0400-\u04ff]", text):
            raise ContractError("Unexpected analysis language")
    flattened = _norm(" ".join(all_text))
    for item in fixture["forbidden_claims"]:
        if any(_norm(term) in flattened for term in item["terms"]):
            raise ContractError("Forbidden analysis claim")
    # The summary has no evidence_ids in the accepted schema. Require the
    # explicitly missing capability to remain unverified in every factual mention.
    gap_pattern = r"python" if fixture["language"] == "en" else r"\u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d|\u0440\u0443\u043a\u043e\u0432\u043e\u0434|\u043b\u0438\u0434\u0435\u0440"
    for text in factual:
        for sentence in re.split(r"[.!?;]", text):
            if re.search(gap_pattern, sentence, re.I) and not _NEGATION.search(_norm(sentence)):
                raise ContractError("Positive claim about unverified experience")
    return output
