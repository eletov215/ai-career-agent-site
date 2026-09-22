"""Owner-facing privacy controls for PRIV-001."""

from __future__ import annotations

import io
import logging
from datetime import datetime, timezone

from flask import Blueprint, current_app, g, render_template, request, send_file, session

from routes.auth import login_required
from security import limiter
from services.auth import AuthService
from services.consent import ConsentService, ConsentStaleStateError
from services.privacy import (
    PrivacyAccountNotFoundError,
    PrivacyExportTooLargeError,
    PrivacyOwnershipIntegrityError,
    PrivacyReauthenticationRequiredError,
    PrivacyService,
)

logger = logging.getLogger(__name__)
_DELETE_CONFIRMATION = "УДАЛИТЬ АККАУНТ"


def create_privacy_blueprint(
    privacy_service: PrivacyService,
    auth_service: AuthService,
    consent_service: ConsentService,
) -> Blueprint:
    bp = Blueprint("privacy_controls", __name__, url_prefix="/privacy-center")

    def render_center(*, status: int = 200, **context):
        return (
            render_template(
                "privacy/center.html",
                retention=privacy_service.retention_policy,
                delete_confirmation=_DELETE_CONFIRMATION,
                **context,
            ),
            status,
        )

    def consent_context(*, error: str | None = None) -> dict:
        state = consent_service.state(g.current_user.id)
        def decorate(row):
            if row is None:
                return None
            item = dict(row)
            for key in ("accepted_at", "withdrawn_at", "created_at", "updated_at"):
                value = item.get(key)
                item[key + "_iso"] = (
                    datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat(timespec="seconds")
                    if value is not None else None
                )
            return item
        state["current"] = decorate(state.get("current"))
        state["history"] = [decorate(row) for row in state.get("history", [])]
        state["error"] = error
        state["consent_form_token"] = consent_service.issue_form_token(
            g.current_user.id, state["current"], signing_key=current_app.secret_key,
        )
        return state

    def strict_consent_form(action: str) -> tuple[str | None, str]:
        if request.is_json or request.files or (request.content_length or 0) > 16384:
            raise ConsentStaleStateError("invalid_form")
        allowed = {"csrf_token", "expected_record_id", "expected_revision", "consent_form_token"}
        if set(request.form) != allowed or any(len(request.form.getlist(key)) != 1 for key in allowed):
            raise ConsentStaleStateError("invalid_form")
        record_id = request.form.get("expected_record_id") or None
        revision = request.form["expected_revision"]
        consent_service.validate_form_token(
            g.current_user.id, request.form["consent_form_token"], action=action,
            expected_record_id=record_id, expected_revision=revision,
            signing_key=current_app.secret_key,
        )
        return record_id, revision

    @bp.after_request
    def protect_privacy_responses(response):  # noqa: ANN001
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers.pop("ETag", None)
        return response

    @bp.get("")
    @login_required
    def center():
        return render_template(
            "privacy/center.html",
            retention=privacy_service.retention_policy,
            delete_confirmation=_DELETE_CONFIRMATION,
        )

    @bp.get("/ai-consent")
    @login_required
    @limiter.limit("60 per 5 minutes")
    def ai_consent():
        return render_template("privacy/ai_consent.html", **consent_context())

    @bp.post("/ai-consent/accept")
    @login_required
    @limiter.limit("10 per hour")
    def accept_ai_consent():
        try:
            record_id, revision = strict_consent_form("accept")
            consent_service.accept(
                g.current_user.id,
                expected_record_id=record_id,
                expected_revision=revision,
            )
        except ConsentStaleStateError:
            return render_template(
                "privacy/ai_consent.html",
                **consent_context(error="Состояние согласия изменилось. Обновите страницу и повторите явное действие."),
            ), 409
        return render_template("privacy/ai_consent.html", **consent_context()), 200

    @bp.post("/ai-consent/withdraw")
    @login_required
    @limiter.limit("10 per hour")
    def withdraw_ai_consent():
        try:
            record_id, revision = strict_consent_form("withdraw")
            consent_service.withdraw(
                g.current_user.id,
                expected_record_id=record_id,
                expected_revision=revision,
            )
        except ConsentStaleStateError:
            return render_template(
                "privacy/ai_consent.html",
                **consent_context(error="Состояние согласия изменилось. Обновите страницу и повторите явное действие."),
            ), 409
        return render_template("privacy/ai_consent.html", **consent_context()), 200

    @bp.post("/export")
    @login_required
    @limiter.limit("6 per hour")
    def export_data():
        password = request.form.get("password", "")
        expected_hash = auth_service.verified_current_password_hash(
            g.current_user.id, password
        )
        if expected_hash is None:
            return render_center(
                status=400,
                export_error="Пароль не подтверждён. Экспорт не сформирован.",
            )
        try:
            artifact = privacy_service.export_user_data(
                g.current_user.id,
                expected_password_hash=expected_hash,
            )
        except PrivacyAccountNotFoundError:
            return render_template("privacy/not_found.html"), 404
        except PrivacyReauthenticationRequiredError:
            return render_center(
                status=409,
                export_error="Пароль изменился во время операции. Повторите экспорт.",
            )
        except PrivacyExportTooLargeError as exc:
            return render_center(status=413, export_error=str(exc))
        except PrivacyOwnershipIntegrityError:
            logger.warning(
                "Privacy export blocked by ownership integrity check",
                extra={"event": "privacy_export_integrity_blocked"},
            )
            return render_center(
                status=409,
                export_error="Экспорт временно недоступен из-за проверки целостности данных.",
            )
        logger.info(
            "Privacy export generated",
            extra={
                "event": "privacy_data_exported",
                "resume_draft_count": artifact.counts.get("resume_drafts", 0),
                "resume_asset_count": artifact.counts.get("resume_assets", 0),
                "oauth_connection_count": artifact.counts.get("oauth_connections", 0),
            },
        )
        response = send_file(
            io.BytesIO(artifact.content),
            mimetype="application/zip",
            as_attachment=True,
            download_name=artifact.filename,
            max_age=0,
            etag=False,
            conditional=False,
        )
        response.headers["Content-Length"] = str(len(artifact.content))
        return response

    @bp.post("/delete-account")
    @login_required
    @limiter.limit("3 per hour")
    def delete_account():
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "").strip()
        error = None
        expected_hash = None
        if confirmation != _DELETE_CONFIRMATION:
            error = f"Введите фразу «{_DELETE_CONFIRMATION}» без изменений."
        else:
            expected_hash = auth_service.verified_current_password_hash(
                g.current_user.id, password
            )
            if expected_hash is None:
                error = "Пароль не подтверждён. Аккаунт не удалён."
        if error:
            return render_center(status=400, delete_error=error)

        try:
            counts = privacy_service.delete_account(
                g.current_user.id,
                expected_password_hash=expected_hash,
            )
        except PrivacyAccountNotFoundError:
            return render_template("privacy/not_found.html"), 404
        except PrivacyReauthenticationRequiredError:
            return render_center(
                status=409,
                delete_error="Пароль изменился во время операции. Повторите подтверждение.",
            )

        session.clear()
        logger.info(
            "Privacy account deletion completed",
            extra={
                "event": "privacy_account_deleted",
                "resume_draft_count": counts.get("resume_drafts", 0),
                "resume_asset_count": counts.get("resume_assets", 0),
                "oauth_connection_count": counts.get("oauth_connections", 0),
                "legacy_oauth_mirror_count": counts.get("legacy_oauth_mirrors", 0),
            },
        )
        return render_template("privacy/deleted.html")

    return bp
