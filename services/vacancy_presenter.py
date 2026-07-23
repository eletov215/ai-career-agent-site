from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Any


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

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def _clean_text(value: Any) -> str:
    text = html.unescape(str(value or ""))
    text = _TAG_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


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


def present_vacancy(raw: dict[str, Any]) -> dict[str, Any]:
    vacancy = dict(raw)
    vacancy["title"] = _clean_text(vacancy.get("title")) or "Без названия"
    vacancy["company"] = _clean_text(vacancy.get("company")) or "Компания не указана"
    vacancy["location"] = _clean_text(vacancy.get("location"))
    vacancy["description"] = _clean_text(vacancy.get("description"))
    vacancy["requirements"] = _clean_text(vacancy.get("requirements"))
    vacancy["salary_display"] = format_salary(vacancy)
    vacancy["schedule_display"] = localize_label(vacancy.get("schedule"))
    vacancy["employment_display"] = localize_label(vacancy.get("employment"))
    vacancy["experience_display"] = localize_label(vacancy.get("experience"))
    vacancy["published_display"] = format_published_at(vacancy.get("published_at"))

    labels: list[str] = []
    for candidate in (
        vacancy.get("location"),
        vacancy.get("schedule_display"),
        vacancy.get("employment_display"),
        vacancy.get("experience_display"),
    ):
        candidate = str(candidate or "").strip()
        if candidate and candidate.casefold() not in {label.casefold() for label in labels}:
            labels.append(candidate)
    if vacancy.get("remote") and not any(label.casefold() == "удалённо" for label in labels):
        labels.append("Удалённо")
    vacancy["meta_labels"] = labels
    return vacancy
