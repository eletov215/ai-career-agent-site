"""Owner-facing privacy controls for PRIV-001."""

from __future__ import annotations

import io
import logging

from flask import Blueprint, g, render_template, request, send_file, session

from routes.auth import login_required
from security import limiter
from services.auth import AuthService
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
