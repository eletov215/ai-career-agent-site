"""Structured career-profile policy, validation, and versioning for PROF-001."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from domain import CareerProfileRecord, CareerProfileVersionRecord
from repositories.profiles import (
    CareerProfileRepository,
    CareerProfileVersionConflictError,
)
from services.auth import AuthValidationError, normalize_email

PROFILE_SCHEMA_VERSION = 1
PROFILE_SECTION_NAMES = (
    "core",
    "contacts",
    "goals",
    "geography",
    "salary",
    "skills",
    "employment",
    "achievements",
    "education",
    "languages",
)

EMPLOYMENT_TYPES = {
    "full": "Полная занятость",
    "part": "Частичная занятость",
    "project": "Проектная работа",
    "temporary": "Временная работа",
    "internship": "Стажировка",
}
WORK_FORMATS = {
    "onsite": "В офисе",
    "remote": "Удалённо",
    "hybrid": "Гибрид",
    "flexible": "Готов рассматривать варианты",
}
RELOCATION_VALUES = {
    "not_ready": "Не готов к переезду",
    "ready": "Готов к переезду",
    "consider": "Готов обсуждать",
}
SALARY_CURRENCIES = {code: code for code in ("RUB", "BYN", "USD", "EUR", "KZT")}
SALARY_PERIODS = {"month": "в месяц", "year": "в год", "hour": "в час"}
SALARY_TAX_MODES = {
    "unspecified": "Не указано",
    "gross": "До вычета налогов",
    "net": "На руки",
}
SKILL_LEVELS = {
    "unspecified": "Не указано",
    "basic": "Базовый",
    "intermediate": "Уверенный",
    "advanced": "Продвинутый",
    "expert": "Экспертный",
}
LANGUAGE_LEVELS = {
    "unspecified": "Не указано",
    "a1": "A1 — начальный",
    "a2": "A2 — элементарный",
    "b1": "B1 — средний",
    "b2": "B2 — выше среднего",
    "c1": "C1 — продвинутый",
    "c2": "C2 — владение в совершенстве",
    "native": "Родной",
}


class ProfileValidationError(ValueError):
    """Raised when submitted profile facts fail bounded validation."""


class ProfileConflictError(RuntimeError):
    """Raised when optimistic profile versioning detects a stale editor."""


@dataclass(frozen=True, slots=True)
class CareerProfileView:
    exists: bool
    user_id: str
    version: int
    schema_version: int
    headline: str | None
    summary: str | None
    contacts: dict[str, Any]
    goals: dict[str, Any]
    geography: dict[str, Any]
    salary: dict[str, Any]
    skills: tuple[dict[str, Any], ...]
    employment: tuple[dict[str, Any], ...]
    achievements: tuple[dict[str, Any], ...]
    education: tuple[dict[str, Any], ...]
    languages: tuple[dict[str, Any], ...]
    completion_percent: int
    confirmed_at: int | None
    created_at: int | None
    updated_at: int | None

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "headline": self.headline,
            "summary": self.summary,
            "contacts": dict(self.contacts),
            "goals": dict(self.goals),
            "geography": dict(self.geography),
            "salary": dict(self.salary),
            "skills": [dict(item) for item in self.skills],
            "employment": [dict(item) for item in self.employment],
            "achievements": [dict(item) for item in self.achievements],
            "education": [dict(item) for item in self.education],
            "languages": [dict(item) for item in self.languages],
        }


@dataclass(frozen=True, slots=True)
class CareerProfileVersionView:
    version: int
    schema_version: int
    snapshot: dict[str, Any]
    changed_sections: tuple[str, ...]
    created_at: int


@dataclass(frozen=True, slots=True)
class ProfileSaveResult:
    profile: CareerProfileView
    changed: bool


def _default_snapshot() -> dict[str, Any]:
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "headline": None,
        "summary": None,
        "contacts": {
            "contact_email": None,
            "phone": None,
            "telegram": None,
            "portfolio_url": None,
            "linkedin_url": None,
        },
        "goals": {
            "target_roles": [],
            "industries": [],
            "employment_types": [],
            "work_formats": [],
        },
        "geography": {
            "current_location": None,
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
        "skills": [],
        "employment": [],
        "achievements": [],
        "education": [],
        "languages": [],
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decode_json(raw: str, default: Any) -> Any:
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def _clean_text(
    value: Any,
    *,
    label: str,
    maximum: int,
    multiline: bool = False,
) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\x00", "").strip()
    if not text:
        return None
    text = (
        "\n".join(line.rstrip() for line in text.splitlines()).strip()
        if multiline
        else " ".join(text.split())
    )
    if len(text) > maximum:
        raise ProfileValidationError(f"{label} не должно превышать {maximum} символов.")
    if any(ord(char) < 32 and char not in "\n\t" for char in text):
        raise ProfileValidationError(f"{label} содержит недопустимые символы.")
    return text


def _string_list(
    value: Any,
    *,
    label: str,
    maximum_items: int,
    maximum_length: int,
) -> list[str]:
    if value is None:
        raw_items: list[Any] = []
    elif isinstance(value, str):
        raw_items = re.split(r"[,;\n]+", value)
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        raw_items = list(value)
    else:
        raise ProfileValidationError(f"{label} имеет неверный формат.")
    result: list[str] = []
    seen: set[str] = set()
    for raw in raw_items:
        item = _clean_text(raw, label=label, maximum=maximum_length)
        if not item or item.casefold() in seen:
            continue
        seen.add(item.casefold())
        result.append(item)
    if len(result) > maximum_items:
        raise ProfileValidationError(
            f"{label}: можно указать не более {maximum_items} значений."
        )
    return result


def _enum_list(value: Any, *, label: str, allowed: Mapping[str, str]) -> list[str]:
    values = [value] if isinstance(value, str) else list(value or [])
    result: list[str] = []
    for raw in values:
        code = str(raw or "").strip()
        if not code:
            continue
        if code not in allowed:
            raise ProfileValidationError(f"{label} содержит неизвестное значение.")
        if code not in result:
            result.append(code)
    return result


def _enum_value(
    value: Any,
    *,
    label: str,
    allowed: Mapping[str, str],
    default: str,
) -> str:
    code = str(value or default).strip() or default
    if code not in allowed:
        raise ProfileValidationError(f"{label} содержит неизвестное значение.")
    return code


def _normalise_url(value: Any, *, label: str) -> str | None:
    url = _clean_text(value, label=label, maximum=500)
    if not url:
        return None
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or "\\" in url
    ):
        raise ProfileValidationError(
            f"{label}: используйте полный безопасный адрес http:// или https://."
        )
    return url


def _normalise_phone(value: Any) -> str | None:
    phone = _clean_text(value, label="Телефон", maximum=40)
    if not phone:
        return None
    if not re.fullmatch(r"[0-9+().\-\s]{5,40}", phone):
        raise ProfileValidationError("Введите корректный номер телефона.")
    return phone


def _normalise_telegram(value: Any) -> str | None:
    telegram = _clean_text(value, label="Telegram", maximum=64)
    if not telegram:
        return None
    username = (
        telegram.removeprefix("https://t.me/").strip("/")
        if telegram.startswith("https://t.me/")
        else telegram.lstrip("@")
    )
    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", username):
        raise ProfileValidationError("Введите корректный username Telegram.")
    return f"@{username}"


def _normalise_contact_email(value: Any) -> str | None:
    raw = _clean_text(value, label="Контактный email", maximum=320)
    if not raw:
        return None
    try:
        public_email, _normalised = normalize_email(raw)
    except AuthValidationError as exc:
        raise ProfileValidationError("Введите корректный контактный email.") from exc
    return public_email


def _integer(
    value: Any,
    *,
    label: str,
    minimum: int,
    maximum: int,
) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = int(str(value).replace(" ", ""))
    except (TypeError, ValueError) as exc:
        raise ProfileValidationError(f"{label} должно быть целым числом.") from exc
    if number < minimum or number > maximum:
        raise ProfileValidationError(f"{label} должно быть от {minimum} до {maximum}.")
    return number


def _month(value: Any, *, label: str) -> str | None:
    month = _clean_text(value, label=label, maximum=7)
    if not month:
        return None
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ProfileValidationError(f"{label} имеет неверный формат.")
    return month


def _rows(value: Any, *, label: str, maximum_items: int) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ProfileValidationError(f"{label} имеет неверный формат.")
    rows = list(value)
    if len(rows) > maximum_items:
        raise ProfileValidationError(
            f"{label}: можно добавить не более {maximum_items} записей."
        )
    if any(not isinstance(item, Mapping) for item in rows):
        raise ProfileValidationError(f"{label} имеет неверный формат.")
    return rows


def _row_has_values(row: Mapping[str, Any]) -> bool:
    return any(
        (isinstance(value, bool) and value)
        or (value is not None and str(value).strip())
        for value in row.values()
    )


def _normalise_skills(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in _rows(value, label="Навыки", maximum_items=50):
        if not _row_has_values(row):
            continue
        name = _clean_text(row.get("name"), label="Название навыка", maximum=80)
        if not name:
            raise ProfileValidationError("Укажите название навыка.")
        level = _enum_value(
            row.get("level"),
            label="Уровень навыка",
            allowed=SKILL_LEVELS,
            default="unspecified",
        )
        key = name.casefold()
        if key in seen:
            raise ProfileValidationError(f"Навык «{name}» указан дважды.")
        seen.add(key)
        result.append({"name": name, "level": level})
    return result


def _normalise_languages(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in _rows(value, label="Языки", maximum_items=15):
        if not _row_has_values(row):
            continue
        name = _clean_text(row.get("name"), label="Название языка", maximum=80)
        if not name:
            raise ProfileValidationError("Укажите название языка.")
        level = _enum_value(
            row.get("level"),
            label="Уровень языка",
            allowed=LANGUAGE_LEVELS,
            default="unspecified",
        )
        key = name.casefold()
        if key in seen:
            raise ProfileValidationError(f"Язык «{name}» указан дважды.")
        seen.add(key)
        result.append({"name": name, "level": level})
    return result


def _normalise_employment(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in _rows(value, label="Опыт работы", maximum_items=20):
        if not _row_has_values(row):
            continue
        company = _clean_text(row.get("company"), label="Компания", maximum=160)
        position = _clean_text(row.get("position"), label="Должность", maximum=160)
        if not company or not position:
            raise ProfileValidationError("Для опыта работы укажите компанию и должность.")
        start = _month(row.get("start"), label="Дата начала работы")
        current = str(row.get("current") or "").strip().casefold() in {
            "1",
            "true",
            "yes",
            "on",
        }
        end = None if current else _month(row.get("end"), label="Дата окончания работы")
        if start and end and end < start:
            raise ProfileValidationError(
                "Дата окончания работы не может быть раньше даты начала."
            )
        description = _clean_text(
            row.get("description"),
            label="Описание опыта",
            maximum=2500,
            multiline=True,
        )
        result.append(
            {
                "company": company,
                "position": position,
                "start": start,
                "end": end,
                "current": current,
                "description": description,
            }
        )
    return result


def _normalise_achievements(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    current_year = time.gmtime().tm_year
    for row in _rows(value, label="Достижения", maximum_items=20):
        if not _row_has_values(row):
            continue
        title = _clean_text(row.get("title"), label="Название достижения", maximum=180)
        if not title:
            raise ProfileValidationError("Укажите название достижения.")
        year = _integer(
            row.get("year"),
            label="Год достижения",
            minimum=1900,
            maximum=current_year + 10,
        )
        description = _clean_text(
            row.get("description"),
            label="Описание достижения",
            maximum=2000,
            multiline=True,
        )
        result.append({"title": title, "year": year, "description": description})
    return result


def _normalise_education(value: Any) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    current_year = time.gmtime().tm_year
    for row in _rows(value, label="Образование", maximum_items=15):
        if not _row_has_values(row):
            continue
        institution = _clean_text(
            row.get("institution"),
            label="Учебное заведение",
            maximum=200,
        )
        if not institution:
            raise ProfileValidationError("Укажите учебное заведение.")
        start_year = _integer(
            row.get("start_year"),
            label="Год начала обучения",
            minimum=1900,
            maximum=current_year + 10,
        )
        end_year = _integer(
            row.get("end_year"),
            label="Год окончания обучения",
            minimum=1900,
            maximum=current_year + 10,
        )
        if start_year and end_year and end_year < start_year:
            raise ProfileValidationError(
                "Год окончания обучения не может быть раньше года начала."
            )
        result.append(
            {
                "institution": institution,
                "degree": _clean_text(row.get("degree"), label="Степень", maximum=120),
                "field": _clean_text(
                    row.get("field"), label="Специальность", maximum=160
                ),
                "start_year": start_year,
                "end_year": end_year,
                "description": _clean_text(
                    row.get("description"),
                    label="Описание образования",
                    maximum=1500,
                    multiline=True,
                ),
            }
        )
    return result


def normalise_profile_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and canonicalise a partial, user-confirmed profile payload."""

    headline = _clean_text(
        payload.get("headline"),
        label="Профессиональный заголовок",
        maximum=160,
    )
    summary = _clean_text(
        payload.get("summary"),
        label="О себе",
        maximum=4000,
        multiline=True,
    )

    contacts_raw = payload.get("contacts") or {}
    goals_raw = payload.get("goals") or {}
    geography_raw = payload.get("geography") or {}
    salary_raw = payload.get("salary") or {}
    if not all(
        isinstance(item, Mapping)
        for item in (contacts_raw, goals_raw, geography_raw, salary_raw)
    ):
        raise ProfileValidationError("Профиль имеет неверный формат.")

    contacts = {
        "contact_email": _normalise_contact_email(contacts_raw.get("contact_email")),
        "phone": _normalise_phone(contacts_raw.get("phone")),
        "telegram": _normalise_telegram(contacts_raw.get("telegram")),
        "portfolio_url": _normalise_url(
            contacts_raw.get("portfolio_url"), label="Ссылка на портфолио"
        ),
        "linkedin_url": _normalise_url(
            contacts_raw.get("linkedin_url"),
            label="Ссылка на профессиональный профиль",
        ),
    }
    goals = {
        "target_roles": _string_list(
            goals_raw.get("target_roles"),
            label="Целевые роли",
            maximum_items=10,
            maximum_length=120,
        ),
        "industries": _string_list(
            goals_raw.get("industries"),
            label="Отрасли",
            maximum_items=10,
            maximum_length=120,
        ),
        "employment_types": _enum_list(
            goals_raw.get("employment_types"),
            label="Тип занятости",
            allowed=EMPLOYMENT_TYPES,
        ),
        "work_formats": _enum_list(
            goals_raw.get("work_formats"),
            label="Формат работы",
            allowed=WORK_FORMATS,
        ),
    }
    geography = {
        "current_location": _clean_text(
            geography_raw.get("current_location"),
            label="Текущее местоположение",
            maximum=160,
        ),
        "preferred_locations": _string_list(
            geography_raw.get("preferred_locations"),
            label="Предпочтительные локации",
            maximum_items=10,
            maximum_length=160,
        ),
        "relocation": _enum_value(
            geography_raw.get("relocation"),
            label="Готовность к переезду",
            allowed=RELOCATION_VALUES,
            default="consider",
        ),
    }

    salary_minimum = _integer(
        salary_raw.get("minimum"),
        label="Минимальная зарплата",
        minimum=0,
        maximum=1_000_000_000,
    )
    salary_maximum = _integer(
        salary_raw.get("maximum"),
        label="Максимальная зарплата",
        minimum=0,
        maximum=1_000_000_000,
    )
    if (
        salary_minimum is not None
        and salary_maximum is not None
        and salary_maximum < salary_minimum
    ):
        raise ProfileValidationError(
            "Максимальная зарплата не может быть меньше минимальной."
        )
    currency_raw = str(salary_raw.get("currency") or "").strip().upper()
    if salary_minimum is None and salary_maximum is None:
        currency = None
    else:
        if currency_raw not in SALARY_CURRENCIES:
            raise ProfileValidationError("Выберите валюту зарплатных ожиданий.")
        currency = currency_raw
    salary = {
        "minimum": salary_minimum,
        "maximum": salary_maximum,
        "currency": currency,
        "period": _enum_value(
            salary_raw.get("period"),
            label="Период зарплаты",
            allowed=SALARY_PERIODS,
            default="month",
        ),
        "tax_mode": _enum_value(
            salary_raw.get("tax_mode"),
            label="Тип зарплаты",
            allowed=SALARY_TAX_MODES,
            default="unspecified",
        ),
    }

    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "headline": headline,
        "summary": summary,
        "contacts": contacts,
        "goals": goals,
        "geography": geography,
        "salary": salary,
        "skills": _normalise_skills(payload.get("skills")),
        "employment": _normalise_employment(payload.get("employment")),
        "achievements": _normalise_achievements(payload.get("achievements")),
        "education": _normalise_education(payload.get("education")),
        "languages": _normalise_languages(payload.get("languages")),
    }


def profile_completion(snapshot: Mapping[str, Any]) -> int:
    """Return a deterministic, non-blocking completion indicator."""

    score = 0
    if snapshot.get("headline") or snapshot.get("summary"):
        score += 10
    if any((snapshot.get("contacts") or {}).values()):
        score += 10
    goals = snapshot.get("goals") or {}
    if goals.get("target_roles"):
        score += 15
    if goals.get("employment_types") or goals.get("work_formats"):
        score += 5
    geography = snapshot.get("geography") or {}
    if geography.get("current_location") or geography.get("preferred_locations"):
        score += 10
    salary = snapshot.get("salary") or {}
    if salary.get("minimum") is not None or salary.get("maximum") is not None:
        score += 10
    if snapshot.get("skills"):
        score += 15
    if snapshot.get("employment"):
        score += 15
    if snapshot.get("education"):
        score += 5
    if snapshot.get("languages"):
        score += 3
    if snapshot.get("achievements"):
        score += 2
    return min(score, 100)


def _record_snapshot(record: CareerProfileRecord) -> dict[str, Any]:
    return {
        "schema_version": record.schema_version,
        "headline": record.headline,
        "summary": record.summary,
        "contacts": _decode_json(record.contacts_json, {}),
        "goals": _decode_json(record.goals_json, {}),
        "geography": _decode_json(record.geography_json, {}),
        "salary": _decode_json(record.salary_json, {}),
        "skills": _decode_json(record.skills_json, []),
        "employment": _decode_json(record.employment_json, []),
        "achievements": _decode_json(record.achievements_json, []),
        "education": _decode_json(record.education_json, []),
        "languages": _decode_json(record.languages_json, []),
    }


def _view_from_snapshot(
    *,
    user_id: str,
    snapshot: Mapping[str, Any],
    exists: bool,
    version: int,
    completion_percent: int,
    confirmed_at: int | None,
    created_at: int | None,
    updated_at: int | None,
) -> CareerProfileView:
    default = _default_snapshot()
    contacts = dict(default["contacts"])
    contacts.update(dict(snapshot.get("contacts") or {}))
    goals = dict(default["goals"])
    goals.update(dict(snapshot.get("goals") or {}))
    geography = dict(default["geography"])
    geography.update(dict(snapshot.get("geography") or {}))
    salary = dict(default["salary"])
    salary.update(dict(snapshot.get("salary") or {}))
    return CareerProfileView(
        exists=exists,
        user_id=str(user_id),
        version=int(version),
        schema_version=int(snapshot.get("schema_version") or PROFILE_SCHEMA_VERSION),
        headline=snapshot.get("headline"),
        summary=snapshot.get("summary"),
        contacts=contacts,
        goals=goals,
        geography=geography,
        salary=salary,
        skills=tuple(dict(item) for item in (snapshot.get("skills") or [])),
        employment=tuple(dict(item) for item in (snapshot.get("employment") or [])),
        achievements=tuple(dict(item) for item in (snapshot.get("achievements") or [])),
        education=tuple(dict(item) for item in (snapshot.get("education") or [])),
        languages=tuple(dict(item) for item in (snapshot.get("languages") or [])),
        completion_percent=int(completion_percent),
        confirmed_at=confirmed_at,
        created_at=created_at,
        updated_at=updated_at,
    )


class CareerProfileService:
    """Own structured facts, validation, completion, and immutable versioning."""

    def __init__(self, repository: CareerProfileRepository) -> None:
        self.repository = repository

    def get(self, user_id: str) -> CareerProfileView:
        record = self.repository.get_by_user(str(user_id))
        if record is None:
            snapshot = _default_snapshot()
            return _view_from_snapshot(
                user_id=str(user_id),
                snapshot=snapshot,
                exists=False,
                version=0,
                completion_percent=0,
                confirmed_at=None,
                created_at=None,
                updated_at=None,
            )
        return _view_from_snapshot(
            user_id=record.user_id,
            snapshot=_record_snapshot(record),
            exists=True,
            version=record.version,
            completion_percent=record.completion_percent,
            confirmed_at=record.confirmed_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def save(
        self,
        *,
        user_id: str,
        payload: Mapping[str, Any],
        expected_version: int,
        now: int | None = None,
    ) -> ProfileSaveResult:
        try:
            expected = int(expected_version)
        except (TypeError, ValueError) as exc:
            raise ProfileValidationError("Версия профиля имеет неверный формат.") from exc
        if expected < 0:
            raise ProfileValidationError("Версия профиля имеет неверный формат.")

        current = self.get(str(user_id))
        normalised = normalise_profile_payload(payload)
        snapshot_json = _canonical_json(normalised)
        content_hash = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
        old_snapshot = current.snapshot()
        changed_sections: list[str] = []
        if (
            old_snapshot.get("headline") != normalised.get("headline")
            or old_snapshot.get("summary") != normalised.get("summary")
        ):
            changed_sections.append("core")
        for section in PROFILE_SECTION_NAMES[1:]:
            if old_snapshot.get(section) != normalised.get(section):
                changed_sections.append(section)
        if not current.exists and not changed_sections:
            changed_sections.append("profile")

        section_json = {
            section: _canonical_json(normalised[section])
            for section in PROFILE_SECTION_NAMES[1:]
        }
        try:
            record, changed = self.repository.save_snapshot(
                user_id=str(user_id),
                expected_version=expected,
                schema_version=PROFILE_SCHEMA_VERSION,
                headline=normalised["headline"],
                summary=normalised["summary"],
                section_json=section_json,
                snapshot_json=snapshot_json,
                content_hash=content_hash,
                completion_percent=profile_completion(normalised),
                changed_sections=changed_sections,
                now=now,
            )
        except CareerProfileVersionConflictError as exc:
            raise ProfileConflictError(str(exc)) from exc
        return ProfileSaveResult(
            profile=_view_from_snapshot(
                user_id=record.user_id,
                snapshot=_record_snapshot(record),
                exists=True,
                version=record.version,
                completion_percent=record.completion_percent,
                confirmed_at=record.confirmed_at,
                created_at=record.created_at,
                updated_at=record.updated_at,
            ),
            changed=changed,
        )

    def list_versions(
        self,
        *,
        user_id: str,
        limit: int = 20,
    ) -> list[CareerProfileVersionView]:
        return [
            self._version_view(item)
            for item in self.repository.list_versions(user_id=str(user_id), limit=limit)
        ]

    def get_version(
        self,
        *,
        user_id: str,
        version: int,
    ) -> CareerProfileVersionView | None:
        record = self.repository.get_version(
            user_id=str(user_id),
            version=int(version),
        )
        return self._version_view(record) if record else None

    def get_version_profile(
        self,
        *,
        user_id: str,
        version: int,
    ) -> tuple[CareerProfileVersionView, CareerProfileView] | None:
        item = self.get_version(user_id=str(user_id), version=int(version))
        if item is None:
            return None
        return item, _view_from_snapshot(
            user_id=str(user_id),
            snapshot=item.snapshot,
            exists=True,
            version=item.version,
            completion_percent=profile_completion(item.snapshot),
            confirmed_at=item.created_at,
            created_at=None,
            updated_at=item.created_at,
        )

    @staticmethod
    def _version_view(record: CareerProfileVersionRecord) -> CareerProfileVersionView:
        snapshot = _decode_json(record.snapshot_json, _default_snapshot())
        changed = _decode_json(record.changed_sections_json, [])
        return CareerProfileVersionView(
            version=record.version,
            schema_version=record.schema_version,
            snapshot=dict(snapshot),
            changed_sections=tuple(str(item) for item in changed),
            created_at=record.created_at,
        )
