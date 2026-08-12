"""Owner-scoped career profile and resume-import review routes."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from routes.auth import login_required
from security import limiter
from services.resume_import import (
    ResumeImportError,
    ResumeImportReviewMetadata,
    ResumeImportReviewSigner,
    ResumeImportReviewTokenError,
    ResumeImportService,
)
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

_CONFIDENCE_LABELS = {
    "high": "Высокая уверенность",
    "medium": "Нужна проверка",
    "low": "Низкая уверенность",
}

_IMPORT_PATH_LABELS = {
    "core.headline": "Профессиональный заголовок",
    "core.summary": "О себе",
    "contacts.contact_email": "Контактный email",
    "contacts.phone": "Телефон",
    "contacts.telegram": "Telegram",
    "contacts.portfolio_url": "Портфолио",
    "contacts.linkedin_url": "Профессиональный профиль",
    "geography.current_location": "Текущее местоположение",
    "skills": "Навыки",
    "employment": "Опыт работы",
    "achievements": "Достижения",
    "education": "Образование",
    "languages": "Языки",
}

_SOURCE_LABELS = {
    "manual": "Ручное подтверждение",
    "resume_import": "Импорт резюме",
}

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


def _safe_upload_filename(filename: str) -> str:
    candidate = secure_filename(Path(filename or "").name)
    return candidate or "resume.pdf"


def _list_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Iterable):
        return "\n".join(str(item) for item in value if str(item).strip())
    return ""


def _review_context_from_metadata(metadata: ResumeImportReviewMetadata) -> dict[str, Any]:
    confidence_values = set(metadata.section_confidence.values())
    overall = (
        "low"
        if "low" in confidence_values
        else "medium"
        if "medium" in confidence_values
        else "high"
    )
    return {
        "page_count": metadata.page_count,
        "character_count": metadata.character_count,
        "overall_confidence": overall,
        "sections": [
            {
                "code": section,
                "label": _SECTION_LABELS.get(section, section),
                "confidence": metadata.section_confidence.get(section, "low"),
                "confidence_label": _CONFIDENCE_LABELS.get(
                    metadata.section_confidence.get(section, "low"),
                    "Нужна проверка",
                ),
            }
            for section in metadata.detected_sections
        ],
        "warnings": list(metadata.warnings),
        "conflicts": [],
        "signals": [],
    }


def _review_context_from_proposal(proposal) -> dict[str, Any]:  # noqa: ANN001
    metadata = ResumeImportReviewMetadata(
        schema_version=1,
        extractor_version="deterministic-text-v1",
        page_count=proposal.page_count,
        character_count=proposal.character_count,
        detected_sections=proposal.detected_sections,
        section_confidence=dict(proposal.section_confidence),
        warnings=proposal.warnings,
        owner_fingerprint="",
        base_profile_version=0,
        issued_at=0,
    )
    context = _review_context_from_metadata(metadata)
    context.update(
        {
            "filename": proposal.filename,
            "overall_confidence": proposal.overall_confidence,
            "conflicts": [
                {
                    "path": item.path,
                    "label": _IMPORT_PATH_LABELS.get(item.path, item.path),
                    "current_value": item.current_value,
                    "suggested_value": item.suggested_value,
                }
                for item in proposal.conflicts
            ],
            "signals": [
                {
                    "path": item.path,
                    "label": _IMPORT_PATH_LABELS.get(item.path, item.path),
                    "confidence": item.confidence,
                    "confidence_label": _CONFIDENCE_LABELS.get(
                        item.confidence,
                        "Нужна проверка",
                    ),
                    "source_excerpt": item.source_excerpt,
                }
                for item in proposal.signals[:30]
            ],
        }
    )
    return context


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
        "target_roles": _list_text(goals.get("target_roles")),
        "industries": _list_text(goals.get("industries")),
        "employment_types": list(goals.get("employment_types") or []),
        "work_formats": list(goals.get("work_formats") or []),
        "current_location": geography.get("current_location") or "",
        "preferred_locations": _list_text(geography.get("preferred_locations")),
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


def create_profile_blueprint(
    profile_service: CareerProfileService,
    resume_import_service: ResumeImportService,
    review_signer: ResumeImportReviewSigner,
    *,
    max_resume_upload_mb: int,
) -> Blueprint:
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
                    "source_kind": item.source_kind,
                    "source_label": _SOURCE_LABELS.get(item.source_kind, item.source_kind),
                }
                for item in versions
            ],
            updated_at=_format_timestamp(profile.updated_at),
            confirmed_at=_format_timestamp(profile.confirmed_at),
            **_template_options(),
        )

    @bp.route("/import", methods=["GET", "POST"])
    @limiter.limit("8 per 10 minutes", methods=["POST"])
    @login_required
    def import_resume():
        current = profile_service.get(g.current_user.id)
        error = None
        status_code = 200
        if request.method == "POST":
            uploaded = request.files.get("resume")
            if not uploaded or not uploaded.filename:
                error = "Выберите PDF-файл с резюме."
                status_code = 400
            else:
                safe_name = _safe_upload_filename(uploaded.filename)
                if not safe_name.lower().endswith(".pdf"):
                    error = "Поддерживаются только файлы PDF."
                    status_code = 400
                else:
                    max_bytes = max(1, int(max_resume_upload_mb)) * 1024 * 1024
                    file_bytes = uploaded.stream.read(max_bytes + 1)
                    if len(file_bytes) > max_bytes:
                        error = f"Размер PDF не должен превышать {max_resume_upload_mb} МБ."
                        status_code = 413
                    else:
                        try:
                            proposal = resume_import_service.extract(
                                file_bytes=file_bytes,
                                filename=safe_name,
                                current_profile=current,
                            )
                        except ResumeImportError as exc:
                            error = str(exc)
                            status_code = 400
                        else:
                            review_token = review_signer.dumps(
                                proposal,
                                owner_user_id=g.current_user.id,
                                base_profile_version=current.version,
                            )
                            logger.info(
                                "Resume import review prepared",
                                extra={
                                    "event": "resume_import_review_prepared",
                                    "page_count": proposal.page_count,
                                    "character_count": proposal.character_count,
                                    "detected_section_count": len(proposal.detected_sections),
                                    "conflict_count": len(proposal.conflicts),
                                },
                            )
                            return render_template(
                                "profile/edit.html",
                                profile=current,
                                values=_values_from_payload(proposal.payload),
                                expected_version=current.version,
                                error=None,
                                import_review=_review_context_from_proposal(proposal),
                                confidence_labels=_CONFIDENCE_LABELS,
                                import_token=review_token,
                                form_action=url_for("profile.confirm_resume_import"),
                                cancel_url=url_for("profile.import_resume"),
                                submit_label="Подтвердить и сохранить",
                                **_template_options(),
                            )
        return (
            render_template(
                "profile/import_upload.html",
                profile=current,
                error=error,
                max_resume_upload_mb=max_resume_upload_mb,
            ),
            status_code,
        )

    @bp.post("/import/confirm")
    @limiter.limit("20 per hour")
    @login_required
    def confirm_resume_import():
        token = str(request.form.get("import_token") or "")
        try:
            metadata = review_signer.loads(
                token,
                owner_user_id=g.current_user.id,
            )
        except ResumeImportReviewTokenError as exc:
            return (
                render_template(
                    "profile/import_upload.html",
                    profile=profile_service.get(g.current_user.id),
                    error=str(exc),
                    max_resume_upload_mb=max_resume_upload_mb,
                ),
                400,
            )

        payload = _payload_from_form()
        values = _values_from_payload(payload)
        try:
            submitted_version = int(request.form.get("expected_version", "-1"))
        except ValueError:
            submitted_version = -1
        if submitted_version != metadata.base_profile_version:
            error = "Профиль был изменён в другой сессии. Загрузите резюме заново."
            status_code = 409
        else:
            try:
                result = profile_service.save(
                    user_id=g.current_user.id,
                    payload=payload,
                    expected_version=metadata.base_profile_version,
                    source_kind="resume_import",
                    provenance=metadata.provenance(),
                )
            except ProfileValidationError as exc:
                error = str(exc)
                status_code = 400
            except ProfileConflictError as exc:
                error = str(exc)
                status_code = 409
            else:
                logger.info(
                    "Resume import confirmed",
                    extra={
                        "event": "resume_import_confirmed",
                        "changed": result.changed,
                        "profile_version": result.profile.version,
                        "completion_percent": result.profile.completion_percent,
                        "detected_section_count": len(metadata.detected_sections),
                    },
                )
                flash(
                    "Данные резюме проверены и сохранены как новая версия профиля."
                    if result.changed
                    else "После проверки новых изменений в профиле не обнаружено.",
                    "success",
                )
                return redirect(url_for("profile.view_profile"))

        return (
            render_template(
                "profile/edit.html",
                profile=profile_service.get(g.current_user.id),
                values=values,
                expected_version=metadata.base_profile_version,
                error=error,
                import_review=_review_context_from_metadata(metadata),
                confidence_labels=_CONFIDENCE_LABELS,
                import_token=token,
                form_action=url_for("profile.confirm_resume_import"),
                cancel_url=url_for("profile.import_resume"),
                submit_label="Подтвердить и сохранить",
                **_template_options(),
            ),
            status_code,
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
                    "source_kind": item.source_kind,
                    "source_label": _SOURCE_LABELS.get(item.source_kind, item.source_kind),
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
            source_label=_SOURCE_LABELS.get(item.source_kind, item.source_kind),
            provenance=item.provenance,
            **_template_options(),
        )

    return bp
