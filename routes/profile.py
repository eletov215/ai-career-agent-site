"""Owner-scoped structured career-profile routes for PROF-001."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from typing import Any

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from routes.auth import login_required
from security import limiter
from services.profile import (
    EMPLOYMENT_TYPES,
    LANGUAGE_LEVELS,
    RELOCATION_VALUES,
    SALARY_CURRENCIES,
    SALARY_PERIODS,
    SALARY_TAX_MODES,
    SKILL_LEVELS,
    WORK_FORMATS,
    CareerProfileService,
    CareerProfileView,
    ProfileConflictError,
    ProfileValidationError,
)

logger = logging.getLogger(__name__)

_SECTION_LABELS = {
    "profile": "Создание профиля",
    "core": "О себе",
    "contacts": "Контакты",
    "goals": "Карьерные цели",
    "geography": "География",
    "salary": "Зарплатные ожидания",
    "skills": "Навыки",
    "employment": "Опыт работы",
    "achievements": "Достижения",
    "education": "Образование",
    "languages": "Языки",
}


def _format_timestamp(value: int | None) -> str | None:
    if value is None:
        return None
    return time.strftime("%d.%m.%Y %H:%M UTC", time.gmtime(value))


def _rows_from_form(prefix: str, fields: Iterable[str]) -> list[dict[str, str]]:
    field_names = tuple(fields)
    columns = {
        field: request.form.getlist(f"{prefix}_{field}")
        for field in field_names
    }
    row_count = max((len(values) for values in columns.values()), default=0)
    return [
        {
            field: columns[field][index] if index < len(columns[field]) else ""
            for field in field_names
        }
        for index in range(row_count)
    ]


def _payload_from_form() -> dict[str, Any]:
    return {
        "headline": request.form.get("headline", ""),
        "summary": request.form.get("summary", ""),
        "contacts": {
            "contact_email": request.form.get("contact_email", ""),
            "phone": request.form.get("phone", ""),
            "telegram": request.form.get("telegram", ""),
            "portfolio_url": request.form.get("portfolio_url", ""),
            "linkedin_url": request.form.get("linkedin_url", ""),
        },
        "goals": {
            "target_roles": request.form.get("target_roles", ""),
            "industries": request.form.get("industries", ""),
            "employment_types": request.form.getlist("employment_types"),
            "work_formats": request.form.getlist("work_formats"),
        },
        "geography": {
            "current_location": request.form.get("current_location", ""),
            "preferred_locations": request.form.get("preferred_locations", ""),
            "relocation": request.form.get("relocation", "consider"),
        },
        "salary": {
            "minimum": request.form.get("salary_minimum", ""),
            "maximum": request.form.get("salary_maximum", ""),
            "currency": request.form.get("salary_currency", ""),
            "period": request.form.get("salary_period", "month"),
            "tax_mode": request.form.get("salary_tax_mode", "unspecified"),
        },
        "skills": _rows_from_form("skill", ("name", "level")),
        "employment": _rows_from_form(
            "employment",
            ("company", "position", "start", "end", "current", "description"),
        ),
        "achievements": _rows_from_form(
            "achievement",
            ("title", "year", "description"),
        ),
        "education": _rows_from_form(
            "education",
            (
                "institution",
                "degree",
                "field",
                "start_year",
                "end_year",
                "description",
            ),
        ),
        "languages": _rows_from_form("language", ("name", "level")),
    }


def _at_least_one(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return rows or [{}]


def _values_from_profile(profile: CareerProfileView) -> dict[str, Any]:
    return {
        "headline": profile.headline or "",
        "summary": profile.summary or "",
        "contact_email": profile.contacts.get("contact_email") or "",
        "phone": profile.contacts.get("phone") or "",
        "telegram": profile.contacts.get("telegram") or "",
        "portfolio_url": profile.contacts.get("portfolio_url") or "",
        "linkedin_url": profile.contacts.get("linkedin_url") or "",
        "target_roles": "\n".join(profile.goals.get("target_roles") or []),
        "industries": "\n".join(profile.goals.get("industries") or []),
        "employment_types": list(profile.goals.get("employment_types") or []),
        "work_formats": list(profile.goals.get("work_formats") or []),
        "current_location": profile.geography.get("current_location") or "",
        "preferred_locations": "\n".join(
            profile.geography.get("preferred_locations") or []
        ),
        "relocation": profile.geography.get("relocation") or "consider",
        "salary_minimum": ""
        if profile.salary.get("minimum") is None
        else str(profile.salary.get("minimum")),
        "salary_maximum": ""
        if profile.salary.get("maximum") is None
        else str(profile.salary.get("maximum")),
        "salary_currency": profile.salary.get("currency") or "",
        "salary_period": profile.salary.get("period") or "month",
        "salary_tax_mode": profile.salary.get("tax_mode") or "unspecified",
        "skills": _at_least_one([dict(item) for item in profile.skills]),
        "employment": _at_least_one([dict(item) for item in profile.employment]),
        "achievements": _at_least_one([dict(item) for item in profile.achievements]),
        "education": _at_least_one([dict(item) for item in profile.education]),
        "languages": _at_least_one([dict(item) for item in profile.languages]),
    }


def _values_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    contacts = payload.get("contacts") or {}
    goals = payload.get("goals") or {}
    geography = payload.get("geography") or {}
    salary = payload.get("salary") or {}
    return {
        "headline": payload.get("headline") or "",
        "summary": payload.get("summary") or "",
        "contact_email": contacts.get("contact_email") or "",
        "phone": contacts.get("phone") or "",
        "telegram": contacts.get("telegram") or "",
        "portfolio_url": contacts.get("portfolio_url") or "",
        "linkedin_url": contacts.get("linkedin_url") or "",
        "target_roles": goals.get("target_roles") or "",
        "industries": goals.get("industries") or "",
        "employment_types": list(goals.get("employment_types") or []),
        "work_formats": list(goals.get("work_formats") or []),
        "current_location": geography.get("current_location") or "",
        "preferred_locations": geography.get("preferred_locations") or "",
        "relocation": geography.get("relocation") or "consider",
        "salary_minimum": ""
        if salary.get("minimum") is None
        else str(salary.get("minimum")),
        "salary_maximum": ""
        if salary.get("maximum") is None
        else str(salary.get("maximum")),
        "salary_currency": salary.get("currency") or "",
        "salary_period": salary.get("period") or "month",
        "salary_tax_mode": salary.get("tax_mode") or "unspecified",
        "skills": _at_least_one(list(payload.get("skills") or [])),
        "employment": _at_least_one(list(payload.get("employment") or [])),
        "achievements": _at_least_one(list(payload.get("achievements") or [])),
        "education": _at_least_one(list(payload.get("education") or [])),
        "languages": _at_least_one(list(payload.get("languages") or [])),
    }


def _template_options() -> dict[str, Any]:
    return {
        "employment_type_options": EMPLOYMENT_TYPES,
        "work_format_options": WORK_FORMATS,
        "relocation_options": RELOCATION_VALUES,
        "salary_currency_options": SALARY_CURRENCIES,
        "salary_period_options": SALARY_PERIODS,
        "salary_tax_options": SALARY_TAX_MODES,
        "skill_level_options": SKILL_LEVELS,
        "language_level_options": LANGUAGE_LEVELS,
    }


def create_profile_blueprint(profile_service: CareerProfileService) -> Blueprint:
    bp = Blueprint("profile", __name__, url_prefix="/profile")

    @bp.after_request
    def protect_profile_responses(response):  # noqa: ANN001
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    @bp.get("")
    @limiter.limit("120 per 5 minutes")
    @login_required
    def view_profile():
        profile = profile_service.get(g.current_user.id)
        versions = profile_service.list_versions(user_id=g.current_user.id, limit=5)
        return render_template(
            "profile/view.html",
            profile=profile,
            versions=[
                {
                    "version": item.version,
                    "created_at": _format_timestamp(item.created_at),
                    "changed_sections": [
                        _SECTION_LABELS.get(section, section)
                        for section in item.changed_sections
                    ],
                }
                for item in versions
            ],
            updated_at=_format_timestamp(profile.updated_at),
            confirmed_at=_format_timestamp(profile.confirmed_at),
            **_template_options(),
        )

    @bp.route("/edit", methods=["GET", "POST"])
    @limiter.limit("30 per hour", methods=["POST"])
    @login_required
    def edit_profile():
        current = profile_service.get(g.current_user.id)
        values = _values_from_profile(current)
        error = None
        status_code = 200
        expected_version = current.version

        if request.method == "POST":
            payload = _payload_from_form()
            values = _values_from_payload(payload)
            try:
                expected_version = int(request.form.get("expected_version", "0"))
            except ValueError:
                expected_version = -1
            try:
                result = profile_service.save(
                    user_id=g.current_user.id,
                    payload=payload,
                    expected_version=expected_version,
                )
            except ProfileValidationError as exc:
                error = str(exc)
                status_code = 400
            except ProfileConflictError as exc:
                error = str(exc)
                status_code = 409
            else:
                logger.info(
                    "Career profile saved",
                    extra={
                        "event": "career_profile_saved",
                        "changed": result.changed,
                        "profile_version": result.profile.version,
                        "completion_percent": result.profile.completion_percent,
                    },
                )
                flash(
                    "Профиль обновлён и сохранён как новая версия."
                    if result.changed
                    else "Изменений в профиле не обнаружено.",
                    "success",
                )
                return redirect(url_for("profile.view_profile"))

        return (
            render_template(
                "profile/edit.html",
                profile=current,
                values=values,
                expected_version=expected_version,
                error=error,
                **_template_options(),
            ),
            status_code,
        )

    @bp.get("/history")
    @limiter.limit("120 per 5 minutes")
    @login_required
    def profile_history():
        profile = profile_service.get(g.current_user.id)
        versions = profile_service.list_versions(user_id=g.current_user.id, limit=50)
        return render_template(
            "profile/history.html",
            profile=profile,
            versions=[
                {
                    "version": item.version,
                    "created_at": _format_timestamp(item.created_at),
                    "changed_sections": [
                        _SECTION_LABELS.get(section, section)
                        for section in item.changed_sections
                    ],
                }
                for item in versions
            ],
        )

    @bp.get("/history/<int:version>")
    @limiter.limit("120 per 5 minutes")
    @login_required
    def profile_version(version: int):
        result = profile_service.get_version_profile(
            user_id=g.current_user.id,
            version=version,
        )
        if result is None:
            abort(404)
        item, profile = result
        return render_template(
            "profile/version.html",
            profile=profile,
            version=item,
            created_at=_format_timestamp(item.created_at),
            changed_sections=[
                _SECTION_LABELS.get(section, section)
                for section in item.changed_sections
            ],
            **_template_options(),
        )

    return bp
