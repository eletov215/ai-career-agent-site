from __future__ import annotations

from datetime import datetime
from typing import Any

from .vacancy_normalizer import (
    clean_text,
    infer_employment,
    infer_experience,
    infer_work_format,
)


CURRENCY_SYMBOLS = {
    "RUB": "₽",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "KZT": "₸",
    "BYN": "Br",
}

LABEL_TRANSLATIONS = {
    "full time": "Полная занятость",
    "full-time": "Полная занятость",
    "part time": "Частичная занятость",
    "part-time": "Частичная занятость",
    "permanent": "Постоянная работа",
    "contract": "Контракт",
    "temporary": "Временная работа",
    "temp": "Временная работа",
    "remote": "Удалённо",
    "remote working": "Удалённо",
    "work from home": "Удалённо",
    "hybrid": "Гибрид",
    "on site": "На месте",
    "on-site": "На месте",
    "no experience": "Без опыта",
}

WORK_FORMAT_LABELS = {
    "remote": "Удалённо",
    "hybrid": "Гибрид",
    "onsite": "На месте",
    "field": "Разъездная работа",
    "fly_in_fly_out": "Вахта",
}

EMPLOYMENT_LABELS = {
    "full": "Полная занятость",
    "part": "Частичная занятость",
    "project": "Проектная работа",
    "temporary": "Временная работа",
    "probation": "Стажировка",
    "volunteer": "Волонтёрство",
    "shift": "Сменная работа",
    "side_job": "Подработка",
}

EXPERIENCE_LABELS = {
    "no_experience": "Без опыта",
    "between_1_and_3": "Опыт 1–3 года",
    "between_3_and_6": "Опыт 3–6 лет",
    "more_than_6": "Опыт более 6 лет",
}


def _clean_text(value: Any) -> str:
    """Backward-compatible alias for the shared text normalizer."""

    return clean_text(value)


def _number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if number.is_integer():
        return f"{int(number):,}".replace(",", " ")
    return f"{number:,.2f}".replace(",", " ").rstrip("0").rstrip(".")


def format_salary(vacancy: dict[str, Any]) -> str:
    salary_from = vacancy.get("salary_from")
    salary_to = vacancy.get("salary_to")
    if salary_from is None and salary_to is None:
        return ""

    currency = str(vacancy.get("currency") or "").upper()
    symbol = CURRENCY_SYMBOLS.get(currency, currency)
    from_text = _number(salary_from)
    to_text = _number(salary_to)

    if from_text and to_text:
        amount = f"{from_text}–{to_text}"
    elif from_text:
        amount = f"от {from_text}"
    else:
        amount = f"до {to_text}"

    return f"{symbol}{amount}" if symbol in {"$", "€", "£"} else f"{amount} {symbol}".strip()


def localize_label(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return ""
    return LABEL_TRANSLATIONS.get(text.casefold(), text)


def format_published_at(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return parsed.strftime("%d.%m.%Y")


def _unique_labels(values: list[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        label = str(value or "").strip()
        if label and label.casefold() not in {item.casefold() for item in result}:
            result.append(label)
    return result



def _source_count_label(count: int) -> str:
    remainder_100 = count % 100
    remainder_10 = count % 10
    if 11 <= remainder_100 <= 14:
        noun = "источников"
    elif remainder_10 == 1:
        noun = "источник"
    elif 2 <= remainder_10 <= 4:
        noun = "источника"
    else:
        noun = "источников"
    return f"{count} {noun}"


def _source_records(vacancy: dict[str, Any]) -> list[dict[str, Any]]:
    raw_records = vacancy.get("source_records")
    if not isinstance(raw_records, list) or not raw_records:
        raw_records = [
            {
                "source": vacancy.get("source"),
                "source_title": vacancy.get("source_title"),
                "external_id": vacancy.get("external_id"),
                "url": vacancy.get("url"),
                "published_at": vacancy.get("published_at"),
            }
        ]

    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in raw_records:
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("source") or "").strip().casefold()
        source_title = _clean_text(raw.get("source_title")) or source
        external_id = _clean_text(raw.get("external_id"))
        url = _clean_text(raw.get("url"))
        key = (source, external_id, url)
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                **raw,
                "source": source,
                "source_title": source_title,
                "external_id": external_id,
                "url": url,
                "published_display": format_published_at(raw.get("published_at")),
            }
        )
    return result


def present_vacancy(raw: dict[str, Any]) -> dict[str, Any]:
    vacancy = dict(raw)
    vacancy["title"] = _clean_text(vacancy.get("title")) or "Без названия"
    vacancy["company"] = _clean_text(vacancy.get("company")) or "Компания не указана"
    vacancy["location"] = _clean_text(vacancy.get("location"))
    vacancy["description"] = _clean_text(vacancy.get("description"))
    vacancy["requirements"] = _clean_text(vacancy.get("requirements"))
    vacancy["salary_display"] = format_salary(vacancy)
    vacancy["schedule_display"] = localize_label(vacancy.get("schedule"))

    work_format = str(vacancy.get("work_format") or "").casefold()
    if not work_format or work_format == "unknown":
        work_format = infer_work_format(
            vacancy.get("schedule"),
            vacancy.get("employment"),
            remote_hint=True if vacancy.get("remote") is True else None,
        )
    employment_code = str(vacancy.get("employment_code") or "").casefold()
    if not employment_code or employment_code == "unknown":
        employment_code = infer_employment(
            vacancy.get("employment"), vacancy.get("schedule")
        )
    experience_code = str(vacancy.get("experience_code") or "").casefold()
    if not experience_code or experience_code == "unknown":
        experience_code = infer_experience(
            vacancy.get("experience"), vacancy.get("requirements")
        )

    vacancy["work_format"] = work_format
    vacancy["employment_code"] = employment_code
    vacancy["experience_code"] = experience_code
    vacancy["remote"] = work_format == "remote"
    vacancy["work_format_display"] = WORK_FORMAT_LABELS.get(work_format, "")
    vacancy["employment_display"] = EMPLOYMENT_LABELS.get(
        employment_code,
        localize_label(vacancy.get("employment")),
    )
    vacancy["experience_display"] = EXPERIENCE_LABELS.get(
        experience_code,
        localize_label(vacancy.get("experience")),
    )
    vacancy["published_display"] = format_published_at(vacancy.get("published_at"))

    source_records = _source_records(vacancy)
    vacancy["source_records"] = source_records
    vacancy["source_count"] = len({record["source"] for record in source_records if record["source"]}) or 1
    vacancy["source_links"] = [record for record in source_records if record.get("url")]
    vacancy["source_display"] = (
        _source_count_label(vacancy["source_count"])
        if vacancy["source_count"] > 1
        else (
            source_records[0]["source_title"]
            if source_records
            else vacancy.get("source_title", "")
        )
    )
    vacancy["save_key"] = (
        vacancy.get("dedup_group_id")
        or vacancy.get("url")
        or f"{vacancy.get('source', '')}:{vacancy.get('title', '')}:{vacancy.get('company', '')}"
    )

    format_label = vacancy["work_format_display"]
    if not format_label:
        format_label = vacancy["schedule_display"]
    vacancy["meta_labels"] = _unique_labels(
        [
            vacancy.get("location"),
            format_label,
            vacancy.get("employment_display"),
            vacancy.get("experience_display"),
        ]
    )
    return vacancy
