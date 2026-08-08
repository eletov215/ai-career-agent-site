"""Central vacancy normalization for SEARCH-001.

Provider adapters convert raw API payloads to one typed contract.  The module
is deliberately deterministic and conservative: explicit provider fields win;
text inference is used only when a provider has no structured equivalent, and
ambiguous values stay ``unknown``.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from domain import (
    EMPLOYMENT_VALUES,
    EXPERIENCE_VALUES,
    WORK_FORMAT_VALUES,
    EmploymentCode,
    ExperienceCode,
    NormalizedVacancy,
    WorkFormat,
)

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")

_CURRENCY_ALIASES = {
    "RUR": "RUB",
    "BYR": "BYN",
    "РУБ": "RUB",
    "РУБ.": "RUB",
}


def clean_text(value: Any) -> str:
    """Return plain single-spaced text suitable for storage and display."""

    text = html.unescape(str(value or ""))
    text = _TAG_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def canonical_currency(value: Any) -> str:
    code = clean_text(value).upper()
    return _CURRENCY_ALIASES.get(code, code)


def normalize_number(value: Any) -> float | None:
    """Normalize salary values; zero/negative/non-finite values mean unknown."""

    if value in (None, "", False):
        return None
    try:
        number = float(str(value).replace(" ", "").replace(",", "."))
    except (TypeError, ValueError):
        return None
    if number <= 0 or number != number or number in {float("inf"), float("-inf")}:
        return None
    return number


def normalize_datetime(value: Any) -> str | None:
    """Normalize epoch or ISO-8601 timestamps to UTC with a ``Z`` suffix."""

    if value in (None, ""):
        return None
    parsed: datetime
    if isinstance(value, (int, float)) or str(value).strip().isdigit():
        try:
            parsed = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        raw = str(value).strip()
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")


def _code(value: Any, allowed: frozenset[str]) -> str | None:
    candidate = str(value or "").strip().casefold()
    return candidate if candidate in allowed else None


def _structured_values(value: Any) -> list[tuple[str, str]]:
    """Flatten provider enum objects into ``(id, label)`` pairs."""

    if value in (None, ""):
        return []
    values = value if isinstance(value, list) else [value]
    result: list[tuple[str, str]] = []
    for item in values:
        if isinstance(item, Mapping):
            identifier = clean_text(
                item.get("id")
                or item.get("code")
                or item.get("value")
                or item.get("key")
            )
            label = clean_text(
                item.get("name")
                or item.get("title")
                or item.get("label")
                or item.get("value")
            )
        else:
            identifier = clean_text(item)
            label = clean_text(item)
        if identifier or label:
            result.append((identifier, label))
    return result


def _contains(text: str, terms: Iterable[str]) -> bool:
    folded = text.casefold()
    return any(term.casefold() in folded for term in terms)


def infer_work_format(
    *values: Any,
    remote_hint: bool | None = None,
    explicit: Any = None,
) -> str:
    """Map explicit IDs/labels and conservative text evidence to one code."""

    explicit_code = _code(explicit, WORK_FORMAT_VALUES)
    if explicit_code:
        return explicit_code

    pairs: list[tuple[str, str]] = []
    for value in values:
        pairs.extend(_structured_values(value))
    ids = " ".join(identifier.casefold().replace("-", "_") for identifier, _ in pairs)
    labels = " ".join(label.casefold() for _, label in pairs)
    text = f"{ids} {labels}".strip()

    if _contains(text, ("hybrid", "гибрид", "гибк")):
        return WorkFormat.HYBRID.value
    if _contains(
        text,
        (
            "fly_in_fly_out",
            "flyinflyout",
            "вахт",
            "rotation",
        ),
    ):
        return WorkFormat.FLY_IN_FLY_OUT.value
    if _contains(
        text,
        (
            "field_work",
            "fieldwork",
            "разъезд",
            "полев",
            "на объектах",
        ),
    ):
        return WorkFormat.FIELD.value
    if remote_hint is True or _contains(
        text,
        (
            "remote",
            "home based",
            "home-based",
            "work from home",
            "удален",
            "удалён",
            "дистанц",
            "на дому",
        ),
    ):
        return WorkFormat.REMOTE.value
    if _contains(
        text,
        (
            "on_site",
            "onsite",
            "on-site",
            "office based",
            "office-based",
            "на территории работодателя",
            "в офисе",
            "на месте",
            "стационар",
        ),
    ):
        return WorkFormat.ONSITE.value
    return WorkFormat.UNKNOWN.value


def infer_employment(*values: Any, explicit: Any = None) -> str:
    explicit_code = _code(explicit, EMPLOYMENT_VALUES)
    if explicit_code:
        return explicit_code
    pairs: list[tuple[str, str]] = []
    for value in values:
        pairs.extend(_structured_values(value))
    text = " ".join(
        f"{identifier.casefold().replace('-', '_')} {label.casefold()}"
        for identifier, label in pairs
    )

    if _contains(text, ("probation", "intern", "стажиров")):
        return EmploymentCode.PROBATION.value
    if _contains(text, ("volunteer", "волонт")):
        return EmploymentCode.VOLUNTEER.value
    if _contains(text, ("side_job", "side job", "подработ")):
        return EmploymentCode.SIDE_JOB.value
    if _contains(text, ("shift", "сменн")):
        return EmploymentCode.SHIFT.value
    if _contains(text, ("part", "part_time", "part-time", "неполн", "частич")):
        return EmploymentCode.PART.value
    if _contains(text, ("project", "contract", "проект", "договор")):
        return EmploymentCode.PROJECT.value
    if _contains(text, ("temporary", "temp", "временн", "сезон")):
        return EmploymentCode.TEMPORARY.value
    if _contains(text, ("full", "full_time", "full-time", "полная", "полный рабочий")):
        return EmploymentCode.FULL.value
    return EmploymentCode.UNKNOWN.value


def infer_experience(*values: Any, explicit: Any = None) -> str:
    explicit_code = _code(explicit, EXPERIENCE_VALUES)
    if explicit_code:
        return explicit_code
    pairs: list[tuple[str, str]] = []
    for value in values:
        pairs.extend(_structured_values(value))
    text = " ".join(
        f"{identifier.casefold().replace('-', '_')} {label.casefold()}"
        for identifier, label in pairs
    )
    compact = text.replace("–", "-").replace("—", "-")

    if _contains(compact, ("noexperience", "no_experience", "без опыта", "не требуется")):
        return ExperienceCode.NO_EXPERIENCE.value
    if _contains(compact, ("morethan6", "more_than_6", "более 6", "от 6", "6+")):
        return ExperienceCode.MORE_THAN_6.value
    if _contains(compact, ("between1and3", "between_1_and_3", "1-3", "от 1", "1 год")):
        return ExperienceCode.BETWEEN_1_AND_3.value
    if _contains(compact, ("between3and6", "between_3_and_6", "3-6", "от 3", "3 года")):
        return ExperienceCode.BETWEEN_3_AND_6.value
    return ExperienceCode.UNKNOWN.value


def _salary_pair(salary_from: Any, salary_to: Any) -> tuple[float | None, float | None]:
    lower = normalize_number(salary_from)
    upper = normalize_number(salary_to)
    if lower is not None and upper is not None and lower > upper:
        lower, upper = upper, lower
    return lower, upper


def _status(value: Any) -> str:
    candidate = clean_text(value).casefold()
    return candidate if candidate in {"active", "closed"} else "active"


def _make_contract(
    *,
    external_id: Any,
    source: str,
    source_title: str,
    title: Any,
    company: Any,
    salary_from: Any,
    salary_to: Any,
    currency: Any,
    location: Any,
    work_format: str,
    employment_code: str,
    experience_code: str,
    schedule: Any = "",
    employment: Any = "",
    experience: Any = "",
    description: Any = "",
    requirements: Any = "",
    published_at: Any = None,
    url: Any = "",
    source_status: Any = "active",
    source_modified_at: Any = None,
    closed_reason: Any = None,
    closed_at: Any = None,
) -> NormalizedVacancy:
    lower, upper = _salary_pair(salary_from, salary_to)
    status = _status(source_status)
    try:
        normalized_closed_at = int(closed_at) if closed_at not in (None, "") else None
    except (TypeError, ValueError):
        normalized_closed_at = None
    return NormalizedVacancy(
        external_id=clean_text(external_id),
        source=clean_text(source).casefold(),
        source_title=clean_text(source_title),
        title=clean_text(title) or "Без названия",
        company=clean_text(company) or "Компания не указана",
        salary_from=lower,
        salary_to=upper,
        currency=canonical_currency(currency),
        location=clean_text(location),
        work_format=_code(work_format, WORK_FORMAT_VALUES) or WorkFormat.UNKNOWN.value,
        employment_code=(
            _code(employment_code, EMPLOYMENT_VALUES)
            or EmploymentCode.UNKNOWN.value
        ),
        experience_code=(
            _code(experience_code, EXPERIENCE_VALUES)
            or ExperienceCode.UNKNOWN.value
        ),
        schedule=clean_text(schedule),
        employment=clean_text(employment),
        experience=clean_text(experience),
        description=clean_text(description),
        requirements=clean_text(requirements),
        published_at=normalize_datetime(published_at),
        url=clean_text(url),
        source_status=status,
        source_modified_at=normalize_datetime(source_modified_at),
        closed_reason=clean_text(closed_reason) or None,
        closed_at=normalized_closed_at,
    )


def normalize_hh_vacancy(raw: Mapping[str, Any]) -> NormalizedVacancy:
    area = raw.get("area") or {}
    employer = raw.get("employer") or {}
    salary = raw.get("salary") or {}
    schedule = raw.get("schedule") or {}
    work_formats = raw.get("work_format") or raw.get("work_formats")
    employment = raw.get("employment_form") or raw.get("employment") or {}
    experience = raw.get("experience") or {}
    snippet = raw.get("snippet") or {}

    schedule_label = clean_text(
        schedule.get("name") if isinstance(schedule, Mapping) else schedule
    )
    employment_label = clean_text(
        employment.get("name") if isinstance(employment, Mapping) else employment
    )
    experience_label = clean_text(
        experience.get("name") if isinstance(experience, Mapping) else experience
    )
    description = " ".join(
        part
        for part in (
            clean_text(snippet.get("requirement") if isinstance(snippet, Mapping) else ""),
            clean_text(snippet.get("responsibility") if isinstance(snippet, Mapping) else ""),
        )
        if part
    )
    return _make_contract(
        external_id=raw.get("id"),
        source="hh",
        source_title="HeadHunter",
        title=raw.get("name"),
        company=(employer.get("name") if isinstance(employer, Mapping) else employer),
        salary_from=(salary.get("from") if isinstance(salary, Mapping) else None),
        salary_to=(salary.get("to") if isinstance(salary, Mapping) else None),
        currency=(salary.get("currency") if isinstance(salary, Mapping) else None),
        location=(area.get("name") if isinstance(area, Mapping) else area),
        work_format=infer_work_format(work_formats, schedule),
        employment_code=infer_employment(employment),
        experience_code=infer_experience(experience),
        schedule=schedule_label,
        employment=employment_label,
        experience=experience_label,
        description=description,
        requirements=clean_text(
            snippet.get("requirement") if isinstance(snippet, Mapping) else ""
        ) or experience_label,
        published_at=raw.get("published_at"),
        url=raw.get("alternate_url") or raw.get("apply_alternate_url"),
    )


def normalize_reed_vacancy(raw: Mapping[str, Any]) -> NormalizedVacancy:
    description = raw.get("jobDescription") or raw.get("description")
    location = raw.get("locationName") or raw.get("location")
    title = raw.get("jobTitle") or raw.get("title")
    job_type = raw.get("jobType") or raw.get("employmentType")
    contract_type = raw.get("contractType") or raw.get("contract")
    work_evidence = " ".join(
        clean_text(value)
        for value in (
            raw.get("workFormat"),
            raw.get("workingPattern"),
            raw.get("remoteWorking"),
            title,
            description,
            location,
        )
        if value not in (None, "")
    )
    return _make_contract(
        external_id=raw.get("jobId") or raw.get("id"),
        source="reed",
        source_title="Reed.co.uk",
        title=title,
        company=raw.get("employerName"),
        salary_from=raw.get("minimumSalary"),
        salary_to=raw.get("maximumSalary"),
        currency=raw.get("currency") or "GBP",
        location=location,
        work_format=infer_work_format(work_evidence),
        employment_code=infer_employment(job_type, contract_type),
        experience_code=infer_experience(
            raw.get("experience") or raw.get("minimumExperience")
        ),
        schedule=job_type,
        employment=contract_type or job_type,
        experience=raw.get("experience") or raw.get("minimumExperience"),
        description=description,
        requirements=raw.get("requirements"),
        published_at=raw.get("date") or raw.get("datePosted"),
        url=raw.get("jobUrl") or raw.get("externalUrl"),
    )


def normalize_superjob_vacancy(raw: Mapping[str, Any]) -> NormalizedVacancy:
    town = raw.get("town") or {}
    type_of_work = raw.get("type_of_work") or {}
    place_of_work = raw.get("place_of_work") or {}
    experience = raw.get("experience") or {}
    type_label = clean_text(
        type_of_work.get("title") if isinstance(type_of_work, Mapping) else type_of_work
    )
    place_label = clean_text(
        place_of_work.get("title") if isinstance(place_of_work, Mapping) else place_of_work
    )
    experience_label = clean_text(
        experience.get("title") if isinstance(experience, Mapping) else experience
    )
    return _make_contract(
        external_id=raw.get("id"),
        source="superjob",
        source_title="SuperJob",
        title=raw.get("profession"),
        company=raw.get("firm_name"),
        salary_from=raw.get("payment_from"),
        salary_to=raw.get("payment_to"),
        currency=raw.get("currency") or "RUB",
        location=(town.get("title") if isinstance(town, Mapping) else town),
        work_format=infer_work_format(
            place_of_work,
            type_of_work,
            remote_hint=bool(raw.get("is_remote_work")),
        ),
        employment_code=infer_employment(type_of_work),
        experience_code=infer_experience(experience),
        schedule=place_label,
        employment=type_label,
        experience=experience_label,
        description=raw.get("candidat") or raw.get("work"),
        requirements=experience_label,
        published_at=raw.get("date_published"),
        url=raw.get("link"),
    )


def _trudvsem_lifecycle(raw: Mapping[str, Any]) -> tuple[str, str | None, str | None]:
    closed_tokens = {
        "closed",
        "archived",
        "archive",
        "inactive",
        "deleted",
        "invalid",
        "removed",
        "expired",
        "закрыта",
        "закрыто",
        "архив",
        "неактивна",
        "удалена",
    }
    status_values = [
        raw.get("status"),
        raw.get("state"),
        raw.get("vacancy-status"),
        raw.get("status-name"),
    ]
    explicitly_closed = any(
        clean_text(value).casefold() in closed_tokens
        for value in status_values
        if value not in (None, "")
    )
    boolean_closed = any(
        raw.get(name) is True
        or clean_text(raw.get(name)).casefold() in {"true", "1", "yes"}
        for name in ("is-invalid", "deleted", "archived", "is-archived", "is_closed")
    )
    explicitly_inactive = any(
        raw.get(name) is False
        or clean_text(raw.get(name)).casefold() in {"false", "0", "no"}
        for name in ("active", "is-active", "is_active")
        if name in raw
    )

    expires_at: str | None = None
    for name in (
        "expiration-date",
        "date-expiration",
        "expiry-date",
        "valid-through",
        "validTo",
    ):
        expires_at = normalize_datetime(raw.get(name))
        if expires_at:
            break
    expired = False
    if expires_at:
        try:
            expired = datetime.fromisoformat(expires_at.replace("Z", "+00:00")) <= datetime.now(
                timezone.utc
            )
        except ValueError:
            expired = False

    modified_at: str | None = None
    for name in (
        "modified-date",
        "date-modification",
        "modification-date",
        "last-modified",
        "update-date",
        "change-date",
    ):
        modified_at = normalize_datetime(raw.get(name))
        if modified_at:
            break

    if explicitly_closed or boolean_closed or explicitly_inactive or expired:
        return "closed", modified_at, "provider_expired" if expired else "provider_status"
    return "active", modified_at, None


def normalize_trudvsem_vacancy(item: Mapping[str, Any]) -> NormalizedVacancy | None:
    raw = item.get("vacancy") or item
    if not isinstance(raw, Mapping):
        return None
    company = raw.get("company") or {}
    region = raw.get("region") or {}
    addresses = raw.get("addresses") or {}
    address = addresses.get("address") if isinstance(addresses, Mapping) else None
    if isinstance(address, list):
        address = ", ".join(
            clean_text(entry.get("location") if isinstance(entry, Mapping) else entry)
            for entry in address
            if entry
        )
    elif isinstance(address, Mapping):
        address = address.get("location") or address.get("address")

    schedule = clean_text(raw.get("schedule"))
    employment = clean_text(raw.get("employment"))
    requirement = raw.get("requirement") or {}
    qualification = requirement.get("qualification", "") if isinstance(requirement, Mapping) else ""
    education = requirement.get("education", "") if isinstance(requirement, Mapping) else ""
    requirements = " ".join(
        part
        for part in (
            clean_text(raw.get("requirements")),
            clean_text(qualification),
            clean_text(education),
        )
        if part
    )
    external_id = clean_text(raw.get("id") or raw.get("vacancy-id"))
    url = clean_text(raw.get("vac_url") or raw.get("url"))
    if not url and external_id:
        url = f"https://trudvsem.ru/vacancy/card/{external_id}"
    source_status, source_modified_at, closed_reason = _trudvsem_lifecycle(raw)

    return _make_contract(
        external_id=external_id,
        source="trudvsem",
        source_title="Работа России",
        title=raw.get("job-name") or raw.get("name"),
        company=(company.get("name") if isinstance(company, Mapping) else company),
        salary_from=raw.get("salary_min"),
        salary_to=raw.get("salary_max"),
        currency=raw.get("currency") or "RUB",
        location=(region.get("name") if isinstance(region, Mapping) else region) or address,
        work_format=infer_work_format(
            raw.get("work-format"),
            raw.get("work_places"),
            schedule,
            employment,
        ),
        employment_code=infer_employment(employment, raw.get("employment-type")),
        experience_code=infer_experience(
            raw.get("experience"), raw.get("required_experience")
        ),
        schedule=schedule,
        employment=employment,
        experience=raw.get("experience") or raw.get("required_experience"),
        description=raw.get("duty") or raw.get("job-description") or qualification,
        requirements=requirements,
        published_at=raw.get("creation-date") or raw.get("date"),
        source_modified_at=source_modified_at,
        source_status=source_status,
        closed_reason=closed_reason,
        url=url,
    )


def normalize_vacancy_mapping(item: Mapping[str, Any]) -> NormalizedVacancy:
    """Normalize a provider-shaped or legacy cached mapping.

    Provider adapters should be preferred for raw API responses.  This generic
    path is used by VacancyStore and by old cache rows during the additive
    migration period.
    """

    source = clean_text(item.get("source")).casefold()
    explicit_work = _code(item.get("work_format"), WORK_FORMAT_VALUES)
    explicit_employment = _code(item.get("employment_code"), EMPLOYMENT_VALUES)
    explicit_experience = _code(item.get("experience_code"), EXPERIENCE_VALUES)
    return _make_contract(
        external_id=item.get("external_id") or item.get("id"),
        source=source,
        source_title=item.get("source_title") or source,
        title=item.get("title"),
        company=item.get("company"),
        salary_from=item.get("salary_from"),
        salary_to=item.get("salary_to"),
        currency=item.get("currency"),
        location=item.get("location"),
        work_format=explicit_work
        or infer_work_format(
            item.get("work_format_label"),
            item.get("schedule"),
            item.get("employment"),
            remote_hint=(True if item.get("remote") is True else None),
        ),
        employment_code=explicit_employment
        or infer_employment(item.get("employment"), item.get("schedule")),
        experience_code=explicit_experience
        or infer_experience(item.get("experience"), item.get("requirements")),
        schedule=item.get("schedule"),
        employment=item.get("employment"),
        experience=item.get("experience"),
        description=item.get("description"),
        requirements=item.get("requirements"),
        published_at=item.get("published_at"),
        url=item.get("url"),
        source_status=item.get("source_status") or "active",
        source_modified_at=item.get("source_modified_at"),
        closed_reason=item.get("closed_reason"),
        closed_at=item.get("closed_at"),
    )
