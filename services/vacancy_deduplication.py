"""Conservative cross-source vacancy deduplication for SEARCH-002.

The service groups provider publications only when the available canonical
signals agree.  It is intentionally non-destructive: source publications stay
independent records and the search layer receives one representative card with
all matching source links attached.  Ambiguous pairs remain separate.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit

from .vacancy_normalizer import canonical_currency, clean_text, normalize_datetime


DEDUP_VERSION = 1
MAX_IDENTITY_TEXT = 512
MAX_DESCRIPTION_TOKENS = 96

_LEGAL_COMPANY_TOKENS = {
    "ao",
    "corp",
    "corporation",
    "gmbh",
    "inc",
    "ip",
    "llc",
    "ltd",
    "limited",
    "oao",
    "pao",
    "plc",
    "zao",
    "ао",
    "зао",
    "ип",
    "оао",
    "ооо",
    "пао",
}

_TITLE_STOP_TOKENS = {
    "a",
    "an",
    "at",
    "for",
    "in",
    "job",
    "of",
    "the",
    "to",
    "vacancy",
    "в",
    "вакансия",
    "для",
    "и",
    "к",
    "на",
    "от",
    "по",
    "работа",
    "срочно",
    "требуется",
}

_GENERIC_ROLE_TOKENS = {
    "administrator",
    "analyst",
    "consultant",
    "developer",
    "driver",
    "engineer",
    "manager",
    "operator",
    "seller",
    "specialist",
    "администратор",
    "аналитик",
    "водитель",
    "инженер",
    "консультант",
    "менеджер",
    "оператор",
    "продавец",
    "разработчик",
    "специалист",
}


_TOKEN_ALIASES = {
    "backend": "backend",
    "back_end": "backend",
    "back-end": "backend",
    "бэкенд": "backend",
    "бекенд": "backend",
    "developer": "developer",
    "программист": "developer",
    "разработчик": "developer",
    "frontend": "frontend",
    "front_end": "frontend",
    "front-end": "frontend",
    "фронтенд": "frontend",
    "аналитик": "analyst",
    "analyst": "analyst",
}

_SENIORITY_ALIASES = {
    "chief": "head",
    "director": "head",
    "head": "head",
    "jr": "junior",
    "junior": "junior",
    "lead": "lead",
    "middle": "middle",
    "mid": "middle",
    "senior": "senior",
    "sr": "senior",
    "ведущий": "senior",
    "главный": "lead",
    "директор": "head",
    "младший": "junior",
    "начальник": "head",
    "руководитель": "head",
    "сеньор": "senior",
    "старший": "senior",
    "тимлид": "lead",
}

_LOCATION_ALIASES = {
    "moscow": "moscow",
    "москва": "moscow",
    "saint petersburg": "saint_petersburg",
    "st petersburg": "saint_petersburg",
    "st peterburg": "saint_petersburg",
    "spb": "saint_petersburg",
    "санкт петербург": "saint_petersburg",
    "питер": "saint_petersburg",
}

_PLACEHOLDER_COMPANIES = {
    "",
    "company not specified",
    "unknown",
    "работодатель не указан",
    "employer not specified",
    "компания не указана",
    "не указано",
}

_SOURCE_TITLES = {
    "hh": "HeadHunter",
    "reed": "Reed.co.uk",
    "superjob": "SuperJob",
    "trudvsem": "Работа России",
}

_SOURCE_PRIORITY = {
    "hh": 40,
    "superjob": 30,
    "trudvsem": 20,
    "reed": 10,
}


@dataclass(frozen=True, slots=True)
class DedupIdentity:
    title_key: str
    company_key: str
    location_key: str
    title_tokens: frozenset[str]
    company_tokens: frozenset[str]
    description_tokens: frozenset[str]
    seniority: frozenset[str]
    strict_key: str | None
    generic_title: bool


@dataclass(frozen=True, slots=True)
class DuplicateDecision:
    matched: bool
    confidence: float
    method: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeduplicationStats:
    input_count: int
    output_count: int
    duplicate_count: int
    identity_duplicate_count: int
    cross_source_duplicate_count: int
    cross_source_groups: int
    exact_groups: int
    similarity_groups: int

    def as_dict(self) -> dict[str, int]:
        return {
            "input_count": self.input_count,
            "output_count": self.output_count,
            "duplicate_count": self.duplicate_count,
            "identity_duplicate_count": self.identity_duplicate_count,
            "cross_source_duplicate_count": self.cross_source_duplicate_count,
            "cross_source_groups": self.cross_source_groups,
            "exact_groups": self.exact_groups,
            "similarity_groups": self.similarity_groups,
        }


@dataclass(frozen=True, slots=True)
class DeduplicationResult:
    items: list[dict[str, Any]]
    stats: DeduplicationStats


def _identity_text(value: Any) -> str:
    text = clean_text(value)[:MAX_IDENTITY_TEXT]
    text = unicodedata.normalize("NFKC", text).casefold().replace("ё", "е")
    text = text.replace("c++", " cpp ").replace("c#", " csharp ")
    text = re.sub(r"[^0-9a-zа-я+#]+", " ", text, flags=re.IGNORECASE)
    return " ".join(text.split())


def _tokens(value: Any, *, stop: set[str] | None = None, limit: int = 64) -> tuple[str, ...]:
    result: list[str] = []
    for token in _identity_text(value).split():
        token = _TOKEN_ALIASES.get(token, token)
        if stop and token in stop:
            continue
        if len(token) == 1 and not token.isdigit():
            continue
        if token not in result:
            result.append(token)
        if len(result) >= limit:
            break
    return tuple(result)


def _company_key(value: Any) -> tuple[str, frozenset[str]]:
    tokens = [token for token in _tokens(value) if token not in _LEGAL_COMPANY_TOKENS]
    key = " ".join(tokens)
    if key in _PLACEHOLDER_COMPANIES:
        return "", frozenset()
    return key, frozenset(tokens)


def _location_key(value: Any) -> str:
    text = _identity_text(value)
    text = re.sub(r"^(г|город)\s+", "", text).strip()
    if text in _LOCATION_ALIASES:
        return _LOCATION_ALIASES[text]
    for alias, canonical in _LOCATION_ALIASES.items():
        if text.startswith(f"{alias} ") or text.endswith(f" {alias}"):
            return canonical
    return text


def _seniority(tokens: Sequence[str]) -> frozenset[str]:
    return frozenset(
        _SENIORITY_ALIASES[token]
        for token in tokens
        if token in _SENIORITY_ALIASES
    )


def _description_tokens(item: Mapping[str, Any]) -> frozenset[str]:
    text = " ".join(
        str(item.get(name) or "")
        for name in ("description", "requirements")
    )
    return frozenset(
        _tokens(text, stop=_TITLE_STOP_TOKENS, limit=MAX_DESCRIPTION_TOKENS)
    )


def _hash_key(*parts: str) -> str:
    body = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def build_dedup_identity(item: Mapping[str, Any]) -> DedupIdentity:
    title_tokens = _tokens(item.get("title"), stop=_TITLE_STOP_TOKENS)
    title_key = " ".join(title_tokens)
    company_key, company_tokens = _company_key(item.get("company"))
    location_key = _location_key(item.get("location"))
    significant = [
        token
        for token in title_tokens
        if token not in _SENIORITY_ALIASES and token not in _TITLE_STOP_TOKENS
    ]
    generic_title = bool(significant) and set(significant).issubset(_GENERIC_ROLE_TOKENS)
    generic_title = generic_title or len(significant) <= 1

    strict_key: str | None = None
    if title_key and company_key:
        location_scope = location_key
        if str(item.get("work_format") or "").casefold() in {"remote", "hybrid"}:
            location_scope = "distributed"
        strict_key = _hash_key(
            f"v{DEDUP_VERSION}",
            title_key,
            company_key,
            location_scope,
        )

    return DedupIdentity(
        title_key=title_key,
        company_key=company_key,
        location_key=location_key,
        title_tokens=frozenset(title_tokens),
        company_tokens=company_tokens,
        description_tokens=_description_tokens(item),
        seniority=_seniority(title_tokens),
        strict_key=strict_key,
        generic_title=generic_title,
    )


def dedup_key_for(item: Mapping[str, Any]) -> str | None:
    """Return the non-unique SEARCH-002 candidate key stored with a source row."""

    return build_dedup_identity(item).strict_key


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _sequence(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left[:256], right[:256], autojunk=False).ratio()


def _known_code(item: Mapping[str, Any], field: str) -> str:
    value = str(item.get(field) or "").strip().casefold()
    return "" if value in {"", "unknown"} else value


def _same_source_identity(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if str(left.get("source") or "") != str(right.get("source") or ""):
        return False
    left_id = str(left.get("external_id") or "").strip()
    right_id = str(right.get("external_id") or "").strip()
    if left_id and right_id:
        return left_id == right_id
    left_url = str(left.get("url") or "").strip()
    right_url = str(right.get("url") or "").strip()
    return bool(left_url and right_url and left_url == right_url)


def _source(item: Mapping[str, Any]) -> str:
    return str(item.get("source") or "").strip().casefold()


def _location_compatibility(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
    left_identity: DedupIdentity,
    right_identity: DedupIdentity,
) -> tuple[bool, float, str]:
    left_format = _known_code(left, "work_format")
    right_format = _known_code(right, "work_format")
    if left_format in {"remote", "hybrid"} and right_format in {"remote", "hybrid"}:
        return True, 1.0, "distributed_location"
    if not left_identity.location_key or not right_identity.location_key:
        return True, 0.55, "location_missing"
    if left_identity.location_key == right_identity.location_key:
        return True, 1.0, "same_location"
    if (
        left_identity.location_key in right_identity.location_key
        or right_identity.location_key in left_identity.location_key
    ):
        return True, 0.85, "compatible_location"
    return False, 0.0, "location_conflict"


def _salary_range(item: Mapping[str, Any]) -> tuple[float | None, float | None]:
    values: list[float | None] = []
    for name in ("salary_from", "salary_to"):
        try:
            raw = item.get(name)
            value = float(raw) if raw not in (None, "") else None
            if value is not None and value <= 0:
                value = None
        except (TypeError, ValueError):
            value = None
        values.append(value)
    lower, upper = values
    if lower is not None and upper is not None and lower > upper:
        lower, upper = upper, lower
    return lower, upper


def _salary_compatibility(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> tuple[bool, float, str]:
    left_currency = canonical_currency(left.get("currency"))
    right_currency = canonical_currency(right.get("currency"))
    if left_currency and right_currency and left_currency != right_currency:
        return False, 0.0, "currency_conflict"

    left_lower, left_upper = _salary_range(left)
    right_lower, right_upper = _salary_range(right)
    if left_lower is None and left_upper is None and right_lower is None and right_upper is None:
        return True, 0.6, "salary_missing"
    if (left_lower is None and left_upper is None) or (right_lower is None and right_upper is None):
        return True, 0.7, "salary_partial"

    left_low = left_lower if left_lower is not None else left_upper
    left_high = left_upper if left_upper is not None else left_lower
    right_low = right_lower if right_lower is not None else right_upper
    right_high = right_upper if right_upper is not None else right_lower
    assert left_low is not None and left_high is not None
    assert right_low is not None and right_high is not None

    if max(left_low, right_low) <= min(left_high, right_high):
        return True, 1.0, "salary_overlap"
    left_mid = (left_low + left_high) / 2
    right_mid = (right_low + right_high) / 2
    ratio = max(left_mid, right_mid) / max(min(left_mid, right_mid), 1.0)
    if ratio <= 1.25:
        return True, 0.8, "salary_close"
    return False, 0.0, "salary_conflict"


def _published_compatibility(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> tuple[bool, float, str]:
    left_text = normalize_datetime(left.get("published_at"))
    right_text = normalize_datetime(right.get("published_at"))
    if not left_text or not right_text:
        return True, 0.55, "published_missing"
    try:
        left_date = datetime.fromisoformat(left_text.replace("Z", "+00:00"))
        right_date = datetime.fromisoformat(right_text.replace("Z", "+00:00"))
    except ValueError:
        return True, 0.55, "published_invalid"
    days = abs((left_date - right_date).total_seconds()) / 86_400
    if days > 45:
        return False, 0.0, "published_conflict"
    return True, max(0.6, 1.0 - days / 60), "published_close"


def compare_vacancies(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> DuplicateDecision:
    """Return a conservative, explainable cross-source duplicate decision."""

    if _same_source_identity(left, right):
        return DuplicateDecision(True, 1.0, "provider_identity", ("same_provider_identity",))
    if _source(left) == _source(right):
        return DuplicateDecision(False, 0.0, "rejected", ("same_source_distinct_publications",))

    left_identity = build_dedup_identity(left)
    right_identity = build_dedup_identity(right)
    if not left_identity.title_key or not right_identity.title_key:
        return DuplicateDecision(False, 0.0, "rejected", ("title_missing",))
    if not left_identity.company_key or not right_identity.company_key:
        return DuplicateDecision(False, 0.0, "rejected", ("company_missing",))

    reasons: list[str] = []
    for field in ("work_format", "employment_code", "experience_code"):
        left_code = _known_code(left, field)
        right_code = _known_code(right, field)
        if left_code and right_code and left_code != right_code:
            return DuplicateDecision(False, 0.0, "rejected", (f"{field}_conflict",))
        if left_code and right_code:
            reasons.append(f"same_{field}")

    if left_identity.seniority and right_identity.seniority:
        if left_identity.seniority != right_identity.seniority:
            return DuplicateDecision(False, 0.0, "rejected", ("seniority_conflict",))
        reasons.append("same_seniority")

    location_ok, location_score, location_reason = _location_compatibility(
        left,
        right,
        left_identity,
        right_identity,
    )
    if not location_ok:
        return DuplicateDecision(False, 0.0, "rejected", (location_reason,))
    reasons.append(location_reason)

    salary_ok, salary_score, salary_reason = _salary_compatibility(left, right)
    if not salary_ok:
        return DuplicateDecision(False, 0.0, "rejected", (salary_reason,))
    reasons.append(salary_reason)

    published_ok, published_score, published_reason = _published_compatibility(left, right)
    if not published_ok:
        return DuplicateDecision(False, 0.0, "rejected", (published_reason,))
    reasons.append(published_reason)

    company_seq = _sequence(left_identity.company_key, right_identity.company_key)
    company_tokens = _jaccard(left_identity.company_tokens, right_identity.company_tokens)
    company_exact = left_identity.company_key == right_identity.company_key
    company_score = 1.0 if company_exact else (company_seq * 0.65 + company_tokens * 0.35)
    if company_exact:
        reasons.append("same_company")
    elif company_seq >= 0.96 and company_tokens >= 0.80:
        reasons.append("similar_company")
    else:
        return DuplicateDecision(False, company_score, "rejected", ("company_mismatch",))

    title_seq = _sequence(left_identity.title_key, right_identity.title_key)
    title_tokens = _jaccard(left_identity.title_tokens, right_identity.title_tokens)
    title_exact = left_identity.title_key == right_identity.title_key
    title_score = 1.0 if title_exact else (title_seq * 0.55 + title_tokens * 0.45)
    if title_exact:
        reasons.append("same_title")
    elif title_seq >= 0.92 and title_tokens >= 0.75:
        reasons.append("similar_title")
    else:
        return DuplicateDecision(False, title_score, "rejected", ("title_mismatch",))

    description_score = _jaccard(
        left_identity.description_tokens,
        right_identity.description_tokens,
    )
    if left_identity.generic_title or right_identity.generic_title:
        if description_score < 0.55 or salary_score < 0.75:
            return DuplicateDecision(
                False,
                min(title_score, company_score),
                "rejected",
                ("generic_title_insufficient_evidence",),
            )
        reasons.append("generic_title_description_overlap")
    elif description_score >= 0.35:
        reasons.append("description_overlap")

    confidence = (
        title_score * 0.42
        + company_score * 0.28
        + location_score * 0.10
        + salary_score * 0.08
        + published_score * 0.07
        + min(description_score, 1.0) * 0.05
    )
    exact_fingerprint = bool(
        left_identity.strict_key
        and left_identity.strict_key == right_identity.strict_key
        and title_exact
        and company_exact
    )
    method = "exact_fingerprint" if exact_fingerprint else "conservative_similarity"
    threshold = 0.88 if exact_fingerprint else 0.90
    matched = confidence >= threshold
    if not matched:
        return DuplicateDecision(False, round(confidence, 4), "rejected", ("score_below_threshold",))
    return DuplicateDecision(
        True,
        round(min(confidence, 1.0), 4),
        method,
        tuple(dict.fromkeys(reasons)),
    )


def _published_timestamp(item: Mapping[str, Any]) -> float:
    normalized = normalize_datetime(item.get("published_at"))
    if not normalized:
        return 0.0
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _completeness_score(
    item: Mapping[str, Any],
) -> tuple[float, float, int, str, str]:
    company = _company_key(item.get("company"))[0]
    source = _source(item)
    score = 0.0
    score += 2.0 if _safe_public_url(item.get("url")) else 0.0
    score += (
        2.0
        if item.get("salary_from") is not None or item.get("salary_to") is not None
        else 0.0
    )
    score += 1.0 if company else 0.0
    score += 1.0 if str(item.get("location") or "").strip() else 0.0
    score += min(len(clean_text(item.get("description"))) / 600, 2.0)
    score += min(len(clean_text(item.get("requirements"))) / 400, 1.0)
    for field in ("work_format", "employment_code", "experience_code"):
        score += 0.5 if _known_code(item, field) else 0.0
    external_id = clean_text(item.get("external_id") or item.get("id"))
    return (
        score,
        _published_timestamp(item),
        _SOURCE_PRIORITY.get(source, 0),
        source,
        external_id,
    )


def _safe_public_url(value: Any) -> str:
    """Return a bounded public HTTP(S) URL safe for rendering."""

    raw = clean_text(value)
    if not raw or len(raw) > 2_048:
        return ""
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return ""
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        return ""
    if parsed.username is not None or parsed.password is not None:
        return ""
    return raw


def _source_record(item: Mapping[str, Any]) -> dict[str, Any]:
    source = _source(item)
    return {
        "source": source,
        "source_title": clean_text(item.get("source_title")) or _SOURCE_TITLES.get(source, source),
        "external_id": clean_text(item.get("external_id") or item.get("id")),
        "url": _safe_public_url(item.get("url")),
        "published_at": normalize_datetime(item.get("published_at")),
        "salary_from": item.get("salary_from"),
        "salary_to": item.get("salary_to"),
        "currency": canonical_currency(item.get("currency")),
        "work_format": str(item.get("work_format") or "unknown").casefold(),
        "employment_code": str(item.get("employment_code") or "unknown").casefold(),
        "experience_code": str(item.get("experience_code") or "unknown").casefold(),
    }


def _group_id(items: Sequence[Mapping[str, Any]]) -> str:
    identities: list[str] = []
    for index, item in enumerate(items):
        stable_identity = clean_text(item.get("external_id") or item.get("url"))
        if not stable_identity:
            identity = build_dedup_identity(item)
            anonymous_key = clean_text(item.get("_dedup_anonymous_key"))
            if anonymous_key:
                stable_identity = (
                    f"{anonymous_key}:"
                    f"{identity.strict_key or identity.title_key}"
                )
            else:
                # Defensive fallback for callers that bypass identity collapse.
                stable_identity = (
                    f"anonymous:{index}:"
                    f"{identity.strict_key or f'{identity.title_key}:{identity.company_key}'}"
                )
        identities.append(f"{_source(item)}:{stable_identity}")
    return f"dedup-v{DEDUP_VERSION}-{_hash_key(*sorted(identities))[:20]}"


def _merge_group(
    items: list[dict[str, Any]],
    decisions: list[DuplicateDecision],
) -> dict[str, Any]:
    representative = max(items, key=_completeness_score)
    merged = dict(representative)

    fill_fields = (
        "company",
        "location",
        "description",
        "requirements",
        "salary_from",
        "salary_to",
        "currency",
        "schedule",
        "employment",
        "experience",
        "work_format",
        "employment_code",
        "experience_code",
        "published_at",
        "url",
    )
    for field in fill_fields:
        current = merged.get(field)
        if current not in (None, "", "unknown"):
            continue
        for item in sorted(items, key=_completeness_score, reverse=True):
            candidate = item.get(field)
            if candidate not in (None, "", "unknown"):
                merged[field] = candidate
                break

    records = [_source_record(item) for item in items]
    safe_primary_url = _safe_public_url(merged.get("url"))
    if not safe_primary_url:
        safe_primary_url = next(
            (record["url"] for record in records if record.get("url")),
            "",
        )
    merged["url"] = safe_primary_url
    primary_source = _source(representative)
    records.sort(
        key=lambda record: (
            record["source"] != primary_source,
            record["source_title"].casefold(),
            record["external_id"],
        )
    )
    sources = list(dict.fromkeys(record["source"] for record in records if record["source"]))
    source_titles = list(
        dict.fromkeys(record["source_title"] for record in records if record["source_title"])
    )
    confidence = min((decision.confidence for decision in decisions), default=1.0)
    methods = {decision.method for decision in decisions}
    method = "conservative_similarity" if "conservative_similarity" in methods else "exact_fingerprint"
    if methods == {"provider_identity"}:
        method = "provider_identity"
    reasons = sorted({reason for decision in decisions for reason in decision.reasons})
    identity = build_dedup_identity(merged)
    group_id = _group_id(items)

    merged.pop("_dedup_anonymous_key", None)
    merged.update(
        {
            "dedup_key": identity.strict_key,
            "dedup_version": DEDUP_VERSION,
            "dedup_group_id": group_id,
            "source_records": records,
            "sources": sources,
            "source_titles": source_titles,
            "source_count": len(sources),
            "duplicate_count": max(len(items) - 1, 0),
            "is_cross_source_duplicate": len(sources) > 1,
            "alternative_sources": records[1:],
            "deduplication": {
                "group_id": group_id,
                "version": DEDUP_VERSION,
                "method": method,
                "confidence": round(confidence, 4),
                "reasons": reasons,
            },
        }
    )
    return merged


def _identity_key(
    item: Mapping[str, Any],
    index: int,
) -> tuple[str, str]:
    source = _source(item) or "unknown"
    stable = clean_text(item.get("external_id") or item.get("url"))
    if not stable:
        # Same-provider identity collapsing must never infer identity from a
        # semantic fingerprint. Two anonymous publications from one provider
        # can legitimately share title/company/location signals, especially
        # for remote roles. Snapshot page/position is preferred because it
        # survives repeated materialization; the input ordinal is a deterministic
        # fallback for non-snapshot callers.
        provider_page = item.get("_snapshot_provider_page")
        provider_position = item.get("_snapshot_provider_position")
        if provider_page is not None or provider_position is not None:
            stable = f"anonymous:{int(provider_page or 0)}:{int(provider_position or 0)}"
        else:
            stable = f"anonymous:{index}"
    return source, stable


def _collapse_identity_duplicates(
    items: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    by_identity: dict[tuple[str, str], dict[str, Any]] = {}
    duplicates = 0
    for index, item in enumerate(items):
        key = _identity_key(item, index)
        candidate = dict(item)
        if key[1].startswith("anonymous:"):
            candidate["_dedup_anonymous_key"] = key[1]
        existing = by_identity.get(key)
        if existing is None:
            by_identity[key] = candidate
            continue
        duplicates += 1
        if _completeness_score(candidate) > _completeness_score(existing):
            by_identity[key] = candidate
    return list(by_identity.values()), duplicates


def deduplicate_vacancies(items: Iterable[Mapping[str, Any]]) -> DeduplicationResult:
    """Group high-confidence duplicates while preserving every source record."""

    source_items = [dict(item) for item in items]
    unique_items, identity_duplicate_count = _collapse_identity_duplicates(source_items)
    groups: list[dict[str, Any]] = []

    for item in unique_items:
        best_index: int | None = None
        best_confidence = -math.inf
        best_decisions: list[DuplicateDecision] = []

        for index, group in enumerate(groups):
            group_items: list[dict[str, Any]] = group["items"]
            if any(
                _source(existing) == _source(item)
                and not _same_source_identity(existing, item)
                for existing in group_items
            ):
                continue
            decisions = [compare_vacancies(existing, item) for existing in group_items]
            if not decisions or not all(decision.matched for decision in decisions):
                continue
            confidence = min(decision.confidence for decision in decisions)
            if confidence > best_confidence:
                best_index = index
                best_confidence = confidence
                best_decisions = decisions

        if best_index is None:
            groups.append({"items": [item], "decisions": []})
            continue
        groups[best_index]["items"].append(item)
        groups[best_index]["decisions"].extend(best_decisions)

    merged_items = [
        _merge_group(group["items"], group["decisions"])
        for group in groups
    ]
    duplicate_count = len(source_items) - len(merged_items)
    cross_source_duplicate_count = len(unique_items) - len(merged_items)
    cross_source_groups = sum(
        1 for item in merged_items if item.get("is_cross_source_duplicate")
    )
    exact_groups = sum(
        1
        for item in merged_items
        if item.get("is_cross_source_duplicate")
        and item.get("deduplication", {}).get("method") == "exact_fingerprint"
    )
    similarity_groups = sum(
        1
        for item in merged_items
        if item.get("is_cross_source_duplicate")
        and item.get("deduplication", {}).get("method") == "conservative_similarity"
    )
    return DeduplicationResult(
        items=merged_items,
        stats=DeduplicationStats(
            input_count=len(source_items),
            output_count=len(merged_items),
            duplicate_count=duplicate_count,
            identity_duplicate_count=identity_duplicate_count,
            cross_source_duplicate_count=cross_source_duplicate_count,
            cross_source_groups=cross_source_groups,
            exact_groups=exact_groups,
            similarity_groups=similarity_groups,
        ),
    )
