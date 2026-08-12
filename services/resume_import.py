"""Deterministic text-PDF extraction and editable review for PROF-002.

The extractor produces suggestions, never confirmed profile facts.  Uploads and
full extracted text stay in the request lifecycle.  The authenticated owner must
review and submit the ordinary PROF-001 form before anything is persisted.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from domain import ResumeImportConflict, ResumeImportProposal, ResumeImportSignal
from services.profile import CareerProfileView, normalise_profile_payload
from services.resume_parser import (
    COMMON_SKILLS,
    ROLE_PATTERNS,
    ParsedResume,
    ResumeParseError,
    parse_resume_pdf,
)

RESUME_IMPORT_SCHEMA_VERSION = 1
RESUME_EXTRACTOR_VERSION = "deterministic-text-v1"
REVIEW_TOKEN_MAX_AGE_SECONDS = 30 * 60
CONFIDENCE_VALUES = {"high", "medium", "low"}


class ResumeImportError(ValueError):
    """Raised when a resume cannot produce a safe editable proposal."""


class ResumeImportReviewTokenError(ValueError):
    """Raised when signed review metadata is invalid, expired, or foreign."""


@dataclass(frozen=True, slots=True)
class ResumeImportReviewMetadata:
    """Non-sensitive metadata carried from extraction to confirmation."""

    schema_version: int
    extractor_version: str
    page_count: int
    character_count: int
    detected_sections: tuple[str, ...]
    section_confidence: dict[str, str]
    warnings: tuple[str, ...]
    owner_fingerprint: str
    base_profile_version: int
    issued_at: int

    def provenance(self) -> dict[str, Any]:
        """Return bounded provenance stored only after owner confirmation."""

        return {
            "schema_version": self.schema_version,
            "extractor_version": self.extractor_version,
            "page_count": self.page_count,
            "character_count": self.character_count,
            "detected_sections": list(self.detected_sections),
            "section_confidence": dict(self.section_confidence),
            "reviewed_at": int(time.time()),
        }


class ResumeImportReviewSigner:
    """Sign review metadata without storing the unconfirmed proposal."""

    def __init__(self, secret_key: str) -> None:
        self._secret_key = str(secret_key).encode("utf-8")
        self._serializer = URLSafeTimedSerializer(
            secret_key,
            salt="prof002-resume-review-v1",
        )

    def _owner_fingerprint(self, owner_user_id: str) -> str:
        return hmac.new(
            self._secret_key,
            f"prof002-owner:{owner_user_id}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def dumps(
        self,
        proposal: ResumeImportProposal,
        *,
        owner_user_id: str,
        base_profile_version: int,
    ) -> str:
        return self._serializer.dumps(
            {
                "v": RESUME_IMPORT_SCHEMA_VERSION,
                "extractor": RESUME_EXTRACTOR_VERSION,
                "page_count": int(proposal.page_count),
                "character_count": int(proposal.character_count),
                "detected_sections": list(proposal.detected_sections),
                "section_confidence": dict(proposal.section_confidence),
                "warnings": list(proposal.warnings),
                "owner_fingerprint": self._owner_fingerprint(str(owner_user_id)),
                "base_profile_version": int(base_profile_version),
                "issued_at": int(time.time()),
            }
        )

    def loads(
        self,
        token: str,
        *,
        owner_user_id: str,
        max_age: int = REVIEW_TOKEN_MAX_AGE_SECONDS,
    ) -> ResumeImportReviewMetadata:
        try:
            raw = self._serializer.loads(token, max_age=max_age)
        except SignatureExpired as exc:
            raise ResumeImportReviewTokenError(
                "Срок проверки импорта истёк. Загрузите PDF ещё раз."
            ) from exc
        except BadSignature as exc:
            raise ResumeImportReviewTokenError(
                "Проверка импорта недействительна. Загрузите PDF ещё раз."
            ) from exc
        if not isinstance(raw, Mapping) or int(raw.get("v") or 0) != RESUME_IMPORT_SCHEMA_VERSION:
            raise ResumeImportReviewTokenError(
                "Проверка импорта имеет неподдерживаемый формат."
            )
        token_owner = str(raw.get("owner_fingerprint") or "")
        expected_owner = self._owner_fingerprint(str(owner_user_id))
        if not token_owner or not hmac.compare_digest(token_owner, expected_owner):
            raise ResumeImportReviewTokenError(
                "Проверка импорта принадлежит другому аккаунту."
            )
        section_confidence = {
            str(key): str(value)
            for key, value in dict(raw.get("section_confidence") or {}).items()
            if str(value) in CONFIDENCE_VALUES
        }
        return ResumeImportReviewMetadata(
            schema_version=RESUME_IMPORT_SCHEMA_VERSION,
            extractor_version=str(raw.get("extractor") or RESUME_EXTRACTOR_VERSION),
            page_count=max(int(raw.get("page_count") or 0), 0),
            character_count=max(int(raw.get("character_count") or 0), 0),
            detected_sections=tuple(
                str(item) for item in (raw.get("detected_sections") or [])
            ),
            section_confidence=section_confidence,
            warnings=tuple(str(item) for item in (raw.get("warnings") or [])),
            owner_fingerprint=token_owner,
            base_profile_version=max(int(raw.get("base_profile_version") or 0), 0),
            issued_at=int(raw.get("issued_at") or 0),
        )


_SECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "employment",
        re.compile(
            r"^(?:опыт работы|опыт|work experience|employment history|experience)$",
            re.I,
        ),
    ),
    ("education", re.compile(r"^(?:образование|education|academic background)$", re.I)),
    (
        "skills",
        re.compile(
            r"^(?:ключевые навыки|навыки|компетенции|skills|technical skills|competencies)$",
            re.I,
        ),
    ),
    (
        "languages",
        re.compile(r"^(?:языки|знание языков|languages|language skills)$", re.I),
    ),
    (
        "core",
        re.compile(
            r"^(?:о себе|обо мне|профиль|summary|professional summary|profile|about me)$",
            re.I,
        ),
    ),
    (
        "achievements",
        re.compile(r"^(?:достижения|achievement|achievements|projects|проекты)$", re.I),
    ),
    ("contacts", re.compile(r"^(?:контакты|contacts|contact information)$", re.I)),
)

_EMAIL_RE = re.compile(
    r"(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w.-])",
    re.I,
)
_URL_RE = re.compile(r"https?://[^\s<>()\[\]{}]+", re.I)
_TELEGRAM_RE = re.compile(r"(?:https?://t\.me/|(?<!\w)@)([A-Za-z0-9_]{5,32})", re.I)
_PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s().-]{7,}\d)(?!\d)")

_ROLE_WORDS = re.compile(
    r"(?:developer|engineer|manager|analyst|designer|architect|consultant|director|lead|head|"
    r"разработчик|инженер|менеджер|аналитик|дизайнер|архитектор|консультант|директор|"
    r"руководитель|специалист|бухгалтер|маркетолог|продакт|тестировщик|администратор)",
    re.I,
)
_INSTITUTION_WORDS = re.compile(
    r"(?:университет|институт|академи|колледж|техникум|школа|university|institute|academy|college|school)",
    re.I,
)
_DEGREE_WORDS = re.compile(
    r"(?:бакалавр|магистр|специалист|аспирант|bachelor|master|ph\.?d|degree)",
    re.I,
)

_LANGUAGE_NAMES = {
    "русский": "Русский",
    "russian": "Русский",
    "английский": "Английский",
    "english": "Английский",
    "немецкий": "Немецкий",
    "german": "Немецкий",
    "французский": "Французский",
    "french": "Французский",
    "испанский": "Испанский",
    "spanish": "Испанский",
    "итальянский": "Итальянский",
    "italian": "Итальянский",
    "китайский": "Китайский",
    "chinese": "Китайский",
    "белорусский": "Белорусский",
    "belarusian": "Белорусский",
    "украинский": "Украинский",
    "ukrainian": "Украинский",
}

_MONTHS = {
    "январь": 1,
    "января": 1,
    "февраль": 2,
    "февраля": 2,
    "март": 3,
    "марта": 3,
    "апрель": 4,
    "апреля": 4,
    "май": 5,
    "мая": 5,
    "июнь": 6,
    "июня": 6,
    "июль": 7,
    "июля": 7,
    "август": 8,
    "августа": 8,
    "сентябрь": 9,
    "сентября": 9,
    "октябрь": 10,
    "октября": 10,
    "ноябрь": 11,
    "ноября": 11,
    "декабрь": 12,
    "декабря": 12,
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_MONTH_WORDS = "|".join(sorted(_MONTHS, key=len, reverse=True))
_DATE_TOKEN = rf"(?:\d{{4}}-\d{{2}}|\d{{2}}[./]\d{{4}}|(?:{_MONTH_WORDS})\s+\d{{4}}|\d{{4}})"
_DATE_RANGE_RE = re.compile(
    rf"(?P<start>{_DATE_TOKEN})\s*(?:-|–|—|to|по)\s*(?P<end>{_DATE_TOKEN}|настоящее время|по настоящее время|present|current|сейчас)",
    re.I,
)


def _clean_line(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip(
        " \t•·▪◦-–—|"
    )


def _lines(text: str) -> list[str]:
    return [line for raw in text.splitlines() if (line := _clean_line(raw))]


def _heading_section(line: str) -> str | None:
    normalized = line.strip().rstrip(":").casefold()
    if len(normalized) > 80:
        return None
    for section, pattern in _SECTION_PATTERNS:
        if pattern.fullmatch(normalized):
            return section
    return None


def _split_sections(lines: Sequence[str]) -> tuple[dict[str, list[str]], list[str]]:
    sections: dict[str, list[str]] = {}
    preamble: list[str] = []
    current: str | None = None
    for line in lines:
        section = _heading_section(line)
        if section:
            current = section
            sections.setdefault(section, [])
            continue
        if current is None:
            preamble.append(line)
        else:
            sections[current].append(line)
    return sections, preamble


def _excerpt(value: str, maximum: int = 180) -> str:
    compact = " ".join(value.split())
    return compact if len(compact) <= maximum else compact[: maximum - 1].rstrip() + "…"


def _signal(
    signals: list[ResumeImportSignal],
    path: str,
    confidence: str,
    source: str,
) -> None:
    signals.append(
        ResumeImportSignal(
            path=path,
            confidence=confidence if confidence in CONFIDENCE_VALUES else "low",
            source_excerpt=_excerpt(source),
        )
    )


def _is_probable_name(line: str) -> bool:
    if len(line) > 80 or any(char.isdigit() for char in line):
        return False
    words = line.split()
    return 2 <= len(words) <= 4 and all(word[:1].isupper() for word in words)


def _is_contact_or_noise(line: str) -> bool:
    lower = line.casefold()
    return bool(
        _EMAIL_RE.search(line)
        or _PHONE_RE.search(line)
        or _URL_RE.search(line)
        or _TELEGRAM_RE.search(line)
        or re.search(
            r"\b(?:резюме|cv|curriculum vitae|возраст|лет|year old|обновлено)\b",
            lower,
        )
    )


def _extract_headline(
    text: str,
    preamble: Sequence[str],
    signals: list[ResumeImportSignal],
) -> str | None:
    lowered = text.casefold()
    for pattern, title in ROLE_PATTERNS:
        if re.search(pattern, lowered, flags=re.I | re.S):
            _signal(signals, "core.headline", "medium", title)
            return title
    for line in preamble[:12]:
        if _is_contact_or_noise(line) or _is_probable_name(line):
            continue
        if 2 <= len(line.split()) <= 12 and len(line) <= 160:
            confidence = "medium" if _ROLE_WORDS.search(line) else "low"
            _signal(signals, "core.headline", confidence, line)
            return line
    return None


def _extract_summary(
    sections: Mapping[str, Sequence[str]],
    signals: list[ResumeImportSignal],
) -> str | None:
    lines = list(sections.get("core") or [])
    if not lines:
        return None
    summary = "\n".join(lines[:12]).strip()[:4000]
    if summary:
        _signal(signals, "core.summary", "high", summary)
        return summary
    return None


def _extract_contacts(text: str, signals: list[ResumeImportSignal]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "contact_email": None,
        "phone": None,
        "telegram": None,
        "portfolio_url": None,
        "linkedin_url": None,
    }
    email = _EMAIL_RE.search(text)
    if email:
        result["contact_email"] = email.group(1)
        _signal(signals, "contacts.contact_email", "high", email.group(1))
    for match in _PHONE_RE.finditer(text):
        candidate = match.group(1).strip()
        digits = re.sub(r"\D", "", candidate)
        if 10 <= len(digits) <= 15:
            result["phone"] = candidate
            _signal(signals, "contacts.phone", "high", candidate)
            break
    telegram = _TELEGRAM_RE.search(text)
    if telegram:
        result["telegram"] = f"@{telegram.group(1)}"
        _signal(signals, "contacts.telegram", "high", telegram.group(0))
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip(".,;)")
        lower = url.casefold()
        if "t.me/" in lower:
            continue
        if "linkedin.com" in lower and result["linkedin_url"] is None:
            result["linkedin_url"] = url
            _signal(signals, "contacts.linkedin_url", "high", url)
        elif result["portfolio_url"] is None:
            result["portfolio_url"] = url
            _signal(signals, "contacts.portfolio_url", "medium", url)
    return result


def _extract_location(
    lines: Sequence[str],
    preamble: Sequence[str],
    signals: list[ResumeImportSignal],
) -> str | None:
    patterns = (
        re.compile(
            r"^(?:город|местоположение|проживает|location|city)\s*[:—-]\s*(.+)$",
            re.I,
        ),
        re.compile(r"^(?:location|city)\s+(.+)$", re.I),
    )
    for line in lines:
        for pattern in patterns:
            match = pattern.match(line)
            if match and 1 < len(match.group(1).strip()) <= 160:
                value = match.group(1).strip()
                _signal(signals, "geography.current_location", "high", line)
                return value
    for line in preamble[:10]:
        if (
            "," in line
            and len(line) <= 100
            and not _is_contact_or_noise(line)
            and not _is_probable_name(line)
            and not _ROLE_WORDS.search(line)
        ):
            _signal(signals, "geography.current_location", "low", line)
            return line
    return None


def _split_skill_items(lines: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for line in lines:
        for part in re.split(r"[,;|•·▪◦]+", line):
            item = _clean_line(part)
            key = item.casefold()
            if not item or len(item) > 80 or len(item.split()) > 8 or key in seen:
                continue
            if key in {name.casefold() for name in _LANGUAGE_NAMES.values()}:
                continue
            seen.add(key)
            result.append(item)
    return result


def _extract_skills(
    text: str,
    sections: Mapping[str, Sequence[str]],
    signals: list[ResumeImportSignal],
) -> list[dict[str, Any]]:
    result: list[str] = []
    seen: set[str] = set()
    for item in _split_skill_items(sections.get("skills") or []):
        key = item.casefold()
        if key not in seen:
            seen.add(key)
            result.append(item)
            _signal(signals, "skills", "high", item)
    lowered = text.casefold()
    for skill in COMMON_SKILLS:
        key = skill.casefold()
        if key in lowered and key not in seen:
            seen.add(key)
            result.append(skill)
            _signal(signals, "skills", "medium", skill)
    return [{"name": item, "level": "unspecified"} for item in result[:50]]


def _language_level(line: str) -> str:
    lower = line.casefold()
    direct = re.search(r"\b(a1|a2|b1|b2|c1|c2)\b", lower)
    if direct:
        return direct.group(1)
    if re.search(r"\b(?:родной|native)\b", lower):
        return "native"
    if re.search(r"\b(?:свободно|fluent|advanced)\b", lower):
        return "c1"
    if re.search(r"\b(?:upper[- ]intermediate|выше среднего)\b", lower):
        return "b2"
    if re.search(r"\b(?:intermediate|средний)\b", lower):
        return "b1"
    if re.search(r"\b(?:pre[- ]intermediate|элементарный)\b", lower):
        return "a2"
    if re.search(r"\b(?:basic|beginner|начальный|базовый)\b", lower):
        return "a1"
    return "unspecified"


def _extract_languages(
    text: str,
    sections: Mapping[str, Sequence[str]],
    signals: list[ResumeImportSignal],
) -> list[dict[str, Any]]:
    lines = list(sections.get("languages") or [])
    if not lines:
        lines = _lines(text)
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in lines:
        lower = line.casefold()
        for token, canonical in _LANGUAGE_NAMES.items():
            if re.search(rf"(?<!\w){re.escape(token)}(?!\w)", lower):
                key = canonical.casefold()
                if key in seen:
                    continue
                seen.add(key)
                result.append({"name": canonical, "level": _language_level(line)})
                _signal(
                    signals,
                    "languages",
                    "high" if sections.get("languages") else "medium",
                    line,
                )
    return result[:15]


def _month_value(token: str) -> str | None:
    value = token.strip().casefold()
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return value
    match = re.fullmatch(r"(\d{2})[./](\d{4})", value)
    if match:
        return f"{match.group(2)}-{match.group(1)}"
    if re.fullmatch(r"\d{4}", value):
        return f"{value}-01"
    match = re.fullmatch(rf"({_MONTH_WORDS})\s+(\d{{4}})", value, re.I)
    if match:
        month = _MONTHS.get(match.group(1).casefold())
        return f"{match.group(2)}-{month:02d}" if month else None
    return None


def _date_range(line: str) -> tuple[str | None, str | None, bool] | None:
    match = _DATE_RANGE_RE.search(line)
    if not match:
        return None
    start = _month_value(match.group("start"))
    end_token = match.group("end").casefold()
    current = bool(re.search(r"настоящее|present|current|сейчас", end_token))
    end = None if current else _month_value(match.group("end"))
    return start, end, current


def _meaningful_candidates(lines: Sequence[str]) -> list[str]:
    result: list[str] = []
    for line in lines:
        if _heading_section(line) or _date_range(line) or _is_contact_or_noise(line):
            continue
        if len(line) <= 220:
            result.append(line)
    return result


def _extract_employment(
    all_lines: Sequence[str],
    sections: Mapping[str, Sequence[str]],
    signals: list[ResumeImportSignal],
) -> list[dict[str, Any]]:
    lines = list(sections.get("employment") or []) or list(all_lines)
    section_based = bool(sections.get("employment"))
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str | None]] = set()
    for index, line in enumerate(lines):
        date = _date_range(line)
        if date is None:
            continue
        start, end, current = date
        nearby = _meaningful_candidates(
            lines[max(0, index - 3) : min(len(lines), index + 5)]
        )
        position = next((item for item in nearby if _ROLE_WORDS.search(item)), None)
        company = next(
            (
                item
                for item in nearby
                if item != position
                and not _ROLE_WORDS.search(item)
                and not _INSTITUTION_WORDS.search(item)
            ),
            None,
        )
        if not company or not position:
            continue
        description_lines: list[str] = []
        for candidate in lines[index + 1 : min(len(lines), index + 9)]:
            if _date_range(candidate) or _heading_section(candidate):
                break
            if candidate not in {company, position} and len(candidate) <= 500:
                description_lines.append(candidate)
        description = "\n".join(description_lines).strip()[:2500] or None
        key = (company.casefold(), position.casefold(), start)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "company": company[:160],
                "position": position[:160],
                "start": start,
                "end": end,
                "current": current,
                "description": description,
            }
        )
        _signal(
            signals,
            "employment",
            "high" if section_based and start else "medium",
            f"{line} | {company} | {position}",
        )
    return rows[:20]


def _extract_education(
    sections: Mapping[str, Sequence[str]],
    signals: list[ResumeImportSignal],
) -> list[dict[str, Any]]:
    lines = list(sections.get("education") or [])
    if not lines:
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, line in enumerate(lines):
        if not _INSTITUTION_WORDS.search(line):
            continue
        institution = line[:200]
        key = institution.casefold()
        if key in seen:
            continue
        seen.add(key)
        nearby = lines[max(0, index - 3) : min(len(lines), index + 5)]
        date_line = next((item for item in nearby if _date_range(item)), None)
        start_year = end_year = None
        if date_line:
            years = [int(item) for item in re.findall(r"\b(?:19|20)\d{2}\b", date_line)]
            if years:
                start_year = years[0]
                end_year = years[-1] if len(years) > 1 else None
        degree_line = next(
            (item for item in nearby if item != line and _DEGREE_WORDS.search(item)),
            None,
        )
        field_line = next(
            (
                item
                for item in nearby
                if item not in {line, date_line, degree_line}
                and not _heading_section(item)
                and len(item) <= 160
            ),
            None,
        )
        rows.append(
            {
                "institution": institution,
                "degree": degree_line[:120] if degree_line else None,
                "field": field_line[:160] if field_line else None,
                "start_year": start_year,
                "end_year": end_year,
                "description": None,
            }
        )
        _signal(signals, "education", "high", " | ".join(nearby))
    return rows[:15]


def _extract_achievements(
    sections: Mapping[str, Sequence[str]],
    signals: list[ResumeImportSignal],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line in list(sections.get("achievements") or []):
        if not line or len(line) > 180:
            continue
        year_match = re.search(r"\b(?:19|20)\d{2}\b", line)
        result.append(
            {
                "title": line[:180],
                "year": int(year_match.group(0)) if year_match else None,
                "description": None,
            }
        )
        _signal(signals, "achievements", "medium", line)
    return result[:20]


def _section_confidence(signals: Sequence[ResumeImportSignal]) -> dict[str, str]:
    rank = {"low": 1, "medium": 2, "high": 3}
    values: dict[str, list[str]] = {}
    for signal in signals:
        section = signal.path.split(".", 1)[0]
        values.setdefault(section, []).append(signal.confidence)
    return {
        section: max(levels, key=lambda item: rank.get(item, 0))
        for section, levels in values.items()
    }


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return str(value)
    return str(value)


def _merge_unique_strings(existing: Sequence[str], proposed: Sequence[str]) -> list[str]:
    result = list(existing)
    seen = {item.casefold() for item in result}
    for item in proposed:
        if item.casefold() not in seen:
            seen.add(item.casefold())
            result.append(item)
    return result


def _merge_rows(
    existing: Sequence[Mapping[str, Any]],
    proposed: Sequence[Mapping[str, Any]],
    *,
    key_fields: Sequence[str],
) -> list[dict[str, Any]]:
    result = [dict(item) for item in existing]
    seen = {
        tuple(_string_value(item.get(field)).casefold() for field in key_fields)
        for item in existing
    }
    for item in proposed:
        key = tuple(_string_value(item.get(field)).casefold() for field in key_fields)
        if key not in seen:
            seen.add(key)
            result.append(dict(item))
    return result


def _merge_with_current(
    current: Mapping[str, Any],
    extracted: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[ResumeImportConflict, ...]]:
    merged = copy.deepcopy(dict(current))
    conflicts: list[ResumeImportConflict] = []

    def scalar(path: str, current_value: Any, suggested: Any) -> Any:
        if suggested in (None, "", [], {}):
            return current_value
        if current_value in (None, "", [], {}):
            return suggested
        if current_value != suggested:
            conflicts.append(
                ResumeImportConflict(
                    path=path,
                    current_value=_string_value(current_value),
                    suggested_value=_string_value(suggested),
                )
            )
        return current_value

    merged["headline"] = scalar(
        "core.headline", current.get("headline"), extracted.get("headline")
    )
    merged["summary"] = scalar(
        "core.summary", current.get("summary"), extracted.get("summary")
    )
    for section, fields in {
        "contacts": (
            "contact_email",
            "phone",
            "telegram",
            "portfolio_url",
            "linkedin_url",
        ),
        "geography": ("current_location",),
    }.items():
        merged.setdefault(section, {})
        current_section = dict(current.get(section) or {})
        extracted_section = dict(extracted.get(section) or {})
        for field in fields:
            merged[section][field] = scalar(
                f"{section}.{field}",
                current_section.get(field),
                extracted_section.get(field),
            )

    current_goals = dict(current.get("goals") or {})
    extracted_goals = dict(extracted.get("goals") or {})
    merged.setdefault("goals", {})
    for field in ("target_roles", "industries", "employment_types", "work_formats"):
        merged["goals"][field] = _merge_unique_strings(
            list(current_goals.get(field) or []),
            list(extracted_goals.get(field) or []),
        )

    current_geography = dict(current.get("geography") or {})
    extracted_geography = dict(extracted.get("geography") or {})
    merged.setdefault("geography", {})
    merged["geography"]["preferred_locations"] = _merge_unique_strings(
        list(current_geography.get("preferred_locations") or []),
        list(extracted_geography.get("preferred_locations") or []),
    )
    merged["geography"]["relocation"] = (
        current_geography.get("relocation") or "consider"
    )

    for section, keys in {
        "skills": ("name",),
        "employment": ("company", "position", "start"),
        "achievements": ("title", "year"),
        "education": ("institution", "degree", "field"),
        "languages": ("name",),
    }.items():
        merged[section] = _merge_rows(
            list(current.get(section) or []),
            list(extracted.get(section) or []),
            key_fields=keys,
        )
    return merged, tuple(conflicts)


class ResumeImportService:
    """Create a bounded editable proposal from a text PDF."""

    def __init__(self, *, max_pages: int, max_text_characters: int) -> None:
        self.max_pages = max(1, int(max_pages))
        self.max_text_characters = max(1, int(max_text_characters))

    def extract(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        current_profile: CareerProfileView,
    ) -> ResumeImportProposal:
        try:
            parsed = parse_resume_pdf(
                file_bytes,
                filename,
                max_pages=self.max_pages,
                max_text_characters=self.max_text_characters,
            )
        except ResumeParseError as exc:
            raise ResumeImportError(str(exc)) from exc
        return self.propose(parsed=parsed, current_profile=current_profile)

    def propose(
        self,
        *,
        parsed: ParsedResume,
        current_profile: CareerProfileView,
    ) -> ResumeImportProposal:
        lines = _lines(parsed.text)
        sections, preamble = _split_sections(lines)
        signals: list[ResumeImportSignal] = []

        headline = _extract_headline(parsed.text, preamble, signals)
        summary = _extract_summary(sections, signals)
        contacts = _extract_contacts(parsed.text, signals)
        location = _extract_location(lines, preamble, signals)
        skills = _extract_skills(parsed.text, sections, signals)
        employment = _extract_employment(lines, sections, signals)
        achievements = _extract_achievements(sections, signals)
        education = _extract_education(sections, signals)
        languages = _extract_languages(parsed.text, sections, signals)

        extracted = normalise_profile_payload(
            {
                "headline": headline,
                "summary": summary,
                "contacts": contacts,
                "goals": {
                    "target_roles": [headline] if headline else [],
                    "industries": [],
                    "employment_types": [],
                    "work_formats": [],
                },
                "geography": {
                    "current_location": location,
                    "preferred_locations": [],
                    "relocation": "consider",
                },
                "salary": {
                    "minimum": None,
                    "maximum": None,
                    "currency": None,
                    "period": "month",
                    "tax_mode": "unspecified",
                },
                "skills": skills,
                "employment": employment,
                "achievements": achievements,
                "education": education,
                "languages": languages,
            }
        )
        merged_raw, conflicts = _merge_with_current(
            current_profile.snapshot(),
            extracted,
        )
        merged = normalise_profile_payload(merged_raw)
        confidence = _section_confidence(signals)
        section_order = (
            "core",
            "contacts",
            "geography",
            "skills",
            "employment",
            "achievements",
            "education",
            "languages",
        )
        detected_sections = tuple(
            section for section in section_order if section in confidence
        )
        warnings: list[str] = []
        if not employment:
            warnings.append(
                "Опыт работы не удалось надёжно разложить по строкам. Проверьте этот раздел вручную."
            )
        if not skills:
            warnings.append(
                "Навыки не найдены или записаны в необычном формате. Их можно добавить вручную."
            )
        if conflicts:
            warnings.append(
                "Некоторые предложения отличаются от подтверждённого профиля. Текущие значения сохранены и показаны рядом для сравнения."
            )
        if not signals:
            raise ResumeImportError(
                "Текст PDF прочитан, но структурированные данные не распознаны. Проверьте документ или заполните профиль вручную."
            )
        return ResumeImportProposal(
            filename=parsed.filename,
            page_count=parsed.page_count,
            character_count=parsed.character_count,
            payload=merged,
            extracted_payload=extracted,
            signals=tuple(signals),
            section_confidence=confidence,
            warnings=tuple(warnings),
            conflicts=conflicts,
            detected_sections=detected_sections,
        )
