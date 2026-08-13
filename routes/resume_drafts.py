"""Owner-scoped PROF-003 resume draft, asset, version, and export routes."""

from __future__ import annotations

import logging
from io import BytesIO

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from routes.auth import login_required
from security import limiter
from services.profile import CareerProfileService
from services.resume_drafts import (
    ResumeDraftConflictError,
    ResumeDraftNotFoundError,
    ResumeDraftService,
    ResumeDraftValidationError,
)

logger = logging.getLogger(__name__)

_VERSION_REASON_LABELS = {
    "checkpoint": "Сохранённая версия",
    "export": "Экспорт PDF",
    "restore": "Восстановление версии",
}


def _format_timestamp(value: int | None) -> str:
    if not value:
        return "—"
    import time

    return time.strftime("%d.%m.%Y %H:%M UTC", time.gmtime(int(value)))


def _json_error(message: str, status: int):
    return jsonify({"ok": False, "error": message}), status


def create_resume_drafts_blueprint(
    draft_service: ResumeDraftService,
    profile_service: CareerProfileService,
) -> Blueprint:
    bp = Blueprint("resume_drafts", __name__)

    @bp.after_request
    def protect_resume_responses(response):  # noqa: ANN001
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response

    @bp.get("/resumes")
    @limiter.limit("120 per 5 minutes")
    @login_required
    def library():
        summaries = draft_service.list_drafts(user_id=g.current_user.id)
        return render_template(
            "resumes/library.html",
            summaries=summaries,
            format_timestamp=_format_timestamp,
        )

    @bp.post("/resumes/new")
    @limiter.limit("20 per hour")
    @login_required
    def create_draft():
        source = str(request.form.get("source") or "blank").strip().casefold()
        profile = profile_service.get(g.current_user.id) if source == "profile" else None
        try:
            draft = draft_service.create(
                user_id=g.current_user.id,
                title=request.form.get("title"),
                profile=profile,
                display_name=g.current_user.display_name,
            )
        except ResumeDraftValidationError as exc:
            flash(str(exc), "error")
            return redirect(url_for("resume_drafts.library"))
        flash("Черновик создан.", "success")
        return redirect(url_for("resume_drafts.builder", draft_id=draft.id))

    @bp.post("/resumes/<draft_id>/rename")
    @limiter.limit("30 per hour")
    @login_required
    def rename_draft(draft_id: str):
        try:
            draft_service.rename(
                user_id=g.current_user.id,
                draft_id=draft_id,
                title=request.form.get("title"),
            )
        except ResumeDraftNotFoundError:
            abort(404)
        except ResumeDraftValidationError as exc:
            flash(str(exc), "error")
        else:
            flash("Название резюме обновлено.", "success")
        return redirect(url_for("resume_drafts.library"))

    @bp.post("/resumes/<draft_id>/delete")
    @limiter.limit("12 per hour")
    @login_required
    def delete_draft(draft_id: str):
        if not draft_service.delete(user_id=g.current_user.id, draft_id=draft_id):
            abort(404)
        logger.info(
            "Resume draft deleted",
            extra={"event": "resume_draft_deleted"},
        )
        flash("Черновик и его версии удалены.", "success")
        return redirect(url_for("resume_drafts.library"))

    @bp.get("/resume-builder")
    @limiter.limit("120 per 5 minutes")
    @login_required
    def resume_builder():
        profile = profile_service.get(g.current_user.id)
        draft = draft_service.latest_or_create(
            user_id=g.current_user.id,
            profile=profile,
            display_name=g.current_user.display_name,
        )
        return redirect(url_for("resume_drafts.builder", draft_id=draft.id))

    @bp.get("/resume-builder/<draft_id>")
    @limiter.limit("120 per 5 minutes")
    @login_required
    def builder(draft_id: str):
        draft = draft_service.get(user_id=g.current_user.id, draft_id=draft_id)
        if draft is None:
            abort(404)
        initial_state = draft_service.client_state(
            draft,
            asset_url_builder=lambda asset_id: url_for(
                "resume_drafts.asset",
                asset_id=asset_id,
            ),
        )
        version_count, export_count = draft_service.counts(
            user_id=g.current_user.id,
            draft_id=draft.id,
        )
        return render_template(
            "resume_builder.html",
            draft=draft,
            initial_state=initial_state,
            version_count=version_count,
            export_count=export_count,
        )

    @bp.put("/api/resume-drafts/<draft_id>")
    @limiter.limit("120 per 10 minutes")
    @login_required
    def save_draft(draft_id: str):
        payload = request.get_json(silent=True) or {}
        try:
            result = draft_service.save(
                user_id=g.current_user.id,
                draft_id=draft_id,
                expected_revision=payload.get("expected_revision"),
                state=payload.get("state") or {},
            )
        except ResumeDraftNotFoundError:
            return _json_error("Черновик не найден.", 404)
        except ResumeDraftConflictError as exc:
            return _json_error(str(exc), 409)
        except ResumeDraftValidationError as exc:
            return _json_error(str(exc), 400)
        logger.info(
            "Resume draft autosaved",
            extra={
                "event": "resume_draft_autosaved",
                "changed": result.changed,
                "draft_revision": result.draft.revision,
                "completion_percent": result.draft.completion_percent,
            },
        )
        return jsonify(
            {
                "ok": True,
                "changed": result.changed,
                "revision": result.draft.revision,
                "completion_percent": result.draft.completion_percent,
                "saved_at": result.draft.updated_at,
            }
        )

    @bp.post("/api/resume-drafts/<draft_id>/checkpoint")
    @limiter.limit("30 per hour")
    @login_required
    def checkpoint(draft_id: str):
        payload = request.get_json(silent=True) or {}
        try:
            result = draft_service.checkpoint(
                user_id=g.current_user.id,
                draft_id=draft_id,
                expected_revision=payload.get("expected_revision"),
            )
        except ResumeDraftNotFoundError:
            return _json_error("Черновик не найден.", 404)
        except ResumeDraftConflictError as exc:
            return _json_error(str(exc), 409)
        except (ResumeDraftValidationError, TypeError, ValueError) as exc:
            return _json_error(str(exc) or "Неверная версия черновика.", 400)
        logger.info(
            "Resume version checkpointed",
            extra={
                "event": "resume_version_checkpointed",
                "created": result.created,
                "resume_version": result.version.version,
            },
        )
        return jsonify(
            {
                "ok": True,
                "created": result.created,
                "version": result.version.version,
            }
        )

    @bp.post("/api/resume-drafts/<draft_id>/assets")
    @limiter.limit("20 per 10 minutes")
    @login_required
    def upload_asset(draft_id: str):
        uploaded = request.files.get("asset")
        if not uploaded:
            return _json_error("Выберите изображение.", 400)
        data = uploaded.stream.read(2 * 1024 * 1024 + 1)
        try:
            asset_record = draft_service.store_asset(
                user_id=g.current_user.id,
                draft_id=draft_id,
                kind=request.form.get("kind", ""),
                content_type=uploaded.mimetype or "",
                data=data,
            )
        except ResumeDraftNotFoundError:
            return _json_error("Черновик не найден.", 404)
        except ResumeDraftValidationError as exc:
            return _json_error(str(exc), 400)
        logger.info(
            "Resume asset stored",
            extra={
                "event": "resume_asset_stored",
                "asset_kind": asset_record.kind,
                "asset_bytes": asset_record.byte_size,
            },
        )
        return jsonify(
            {
                "ok": True,
                "asset_id": asset_record.id,
                "url": url_for("resume_drafts.asset", asset_id=asset_record.id),
                "content_type": asset_record.content_type,
                "byte_size": asset_record.byte_size,
            }
        )

    @bp.get("/resumes/assets/<asset_id>")
    @limiter.limit("240 per 5 minutes")
    @login_required
    def asset(asset_id: str):
        record = draft_service.get_asset(
            user_id=g.current_user.id,
            asset_id=asset_id,
        )
        if record is None:
            abort(404)
        response = send_file(
            BytesIO(record.data),
            mimetype=record.content_type,
            download_name=f"{record.kind}.{record.content_type.split('/')[-1]}",
            max_age=0,
            conditional=True,
        )
        response.headers["Cache-Control"] = "private, no-store, max-age=0"
        return response

    @bp.post("/api/resume-drafts/<draft_id>/exports")
    @limiter.limit("30 per hour")
    @login_required
    def record_export(draft_id: str):
        payload = request.get_json(silent=True) or {}
        try:
            result = draft_service.record_export(
                user_id=g.current_user.id,
                draft_id=draft_id,
                expected_revision=payload.get("expected_revision"),
                page_count=payload.get("page_count"),
                byte_size=payload.get("byte_size"),
                pdf_sha256=payload.get("pdf_sha256"),
                file_name=payload.get("file_name"),
            )
        except ResumeDraftNotFoundError:
            return _json_error("Черновик не найден.", 404)
        except ResumeDraftConflictError as exc:
            return _json_error(str(exc), 409)
        except (ResumeDraftValidationError, TypeError, ValueError) as exc:
            return _json_error(str(exc) or "Метаданные PDF имеют неверный формат.", 400)
        logger.info(
            "Resume PDF export recorded",
            extra={
                "event": "resume_pdf_export_recorded",
                "resume_version": result.version.version,
                "version_created": result.version_created,
                "page_count": result.export.page_count,
                "pdf_bytes": result.export.byte_size,
            },
        )
        return jsonify(
            {
                "ok": True,
                "version": result.version.version,
                "version_created": result.version_created,
                "export_id": result.export.id,
            }
        )

    @bp.get("/resumes/<draft_id>/history")
    @limiter.limit("120 per 5 minutes")
    @login_required
    def history(draft_id: str):
        draft = draft_service.get(user_id=g.current_user.id, draft_id=draft_id)
        if draft is None:
            abort(404)
        versions = draft_service.list_versions(
            user_id=g.current_user.id,
            draft_id=draft_id,
        )
        return render_template(
            "resumes/history.html",
            draft=draft,
            versions=versions,
            reason_labels=_VERSION_REASON_LABELS,
            format_timestamp=_format_timestamp,
        )

    @bp.get("/resumes/<draft_id>/history/<int:version>")
    @limiter.limit("120 per 5 minutes")
    @login_required
    def version(draft_id: str, version: int):
        draft = draft_service.get(user_id=g.current_user.id, draft_id=draft_id)
        snapshot = draft_service.get_version(
            user_id=g.current_user.id,
            draft_id=draft_id,
            version=version,
        )
        if draft is None or snapshot is None:
            abort(404)
        state = draft_service.version_state(snapshot)
        return render_template(
            "resumes/version.html",
            draft=draft,
            version=snapshot,
            state=state,
            reason_label=_VERSION_REASON_LABELS.get(snapshot.reason, snapshot.reason),
            created_at=_format_timestamp(snapshot.created_at),
        )

    @bp.post("/resumes/<draft_id>/history/<int:version>/restore")
    @limiter.limit("20 per hour")
    @login_required
    def restore_version(draft_id: str, version: int):
        try:
            draft, restored = draft_service.restore(
                user_id=g.current_user.id,
                draft_id=draft_id,
                version=version,
                expected_revision=request.form.get("expected_revision"),
            )
        except ResumeDraftNotFoundError:
            abort(404)
        except ResumeDraftConflictError as exc:
            flash(str(exc), "error")
            return redirect(url_for("resume_drafts.history", draft_id=draft_id))
        except (ResumeDraftValidationError, TypeError, ValueError) as exc:
            flash(str(exc) or "Не удалось восстановить версию.", "error")
            return redirect(url_for("resume_drafts.history", draft_id=draft_id))
        logger.info(
            "Resume version restored",
            extra={
                "event": "resume_version_restored",
                "restored_from_version": version,
                "resume_version": restored.version,
                "draft_revision": draft.revision,
            },
        )
        flash(f"Версия {version} восстановлена как новая версия {restored.version}.", "success")
        return redirect(url_for("resume_drafts.builder", draft_id=draft_id))

    return bp
