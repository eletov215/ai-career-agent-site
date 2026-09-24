"""Admin-only browser routes for AI-005 synthetic Alice SITE QA."""
from __future__ import annotations

from flask import Blueprint, Response, abort, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from domain.cover_letter import LetterError
from security import limiter
from services.admin_access import is_search_admin

_REVIEW_SESSION_KEY = "ai005_site_qa_admin"
_GATE_ENDPOINTS = {
    "ai005_site_qa.review_gate",
    "ai005_site_qa.enable_review",
    "ai005_site_qa.disable_review",
}


def create_ai005_site_qa_blueprint(service, settings):
    bp = Blueprint("ai005_site_qa", __name__)

    @bp.before_request
    def private_boundary():
        user = getattr(g, "current_user", None)
        if not is_search_admin(user, settings):
            abort(404)
        if request.endpoint not in _GATE_ENDPOINTS and session.get(_REVIEW_SESSION_KEY) != user.id:
            abort(404)

    @bp.after_request
    def private_response(response):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["Referrer-Policy"] = "strict-origin"
        response.headers.pop("ETag", None)
        return response

    @bp.errorhandler(LetterError)
    def feature_error(error):
        code = str(error)
        status = 404 if code == "not_found" else 409 if code in {"stale_write", "stale_source"} else 400
        if code in {"generation_unavailable", "storage_unavailable", "storage_integrity"}:
            status = 503
        messages = {
            "not_found": "Тестовый черновик не найден.",
            "stale_write": "Состояние тестового черновика изменилось. Откройте его заново.",
            "stale_source": "Синтетический источник изменился. Начните новый тест.",
            "confirmation_required": "Подтвердите сохранение или отклонение результата.",
            "invalid_preview": "Предпросмотр устарел. Начните новый тест.",
            "generation_unavailable": "Тест Alice сейчас недоступен. Реальные данные не отправлялись.",
            "storage_unavailable": "Тестовое хранилище временно недоступно.",
            "storage_integrity": "Синтетический тест остановлен из-за проверки целостности.",
        }
        return render_template(
            "letters/site_qa_error.html",
            error=messages.get(code, "Тест не выполнен. Реальные данные не отправлялись."),
        ), status

    @bp.errorhandler(SQLAlchemyError)
    @bp.errorhandler(OSError)
    def storage_error(_error):
        return feature_error(LetterError("storage_unavailable"))

    def fields(required=(), optional=()):
        if request.content_length and request.content_length > 65536:
            abort(413)
        if request.is_json or request.files:
            raise LetterError("invalid_request")
        allowed = set(required) | set(optional) | {"csrf_token"}
        if not set(required) <= set(request.form) or set(request.form) - allowed:
            raise LetterError("invalid_request")
        if any(len(request.form.getlist(key)) != 1 for key in request.form):
            raise LetterError("invalid_request")
        return request.form

    @bp.get("/ai-cover-letter-qa/review")
    @limiter.limit("30 per 5 minutes")
    def review_gate():
        return render_template(
            "letters/site_qa_review.html",
            enabled=session.get(_REVIEW_SESSION_KEY) == g.current_user.id,
        )

    @bp.post("/ai-cover-letter-qa/review/enable")
    @limiter.limit("20 per hour")
    def enable_review():
        fields()
        session[_REVIEW_SESSION_KEY] = g.current_user.id
        session.modified = True
        return redirect(url_for("ai005_site_qa.index"), code=303)

    @bp.post("/ai-cover-letter-qa/review/disable")
    @limiter.limit("20 per hour")
    def disable_review():
        fields()
        session.pop(_REVIEW_SESSION_KEY, None)
        session.modified = True
        return redirect(url_for("ai005_site_qa.review_gate"), code=303)

    @bp.get("/ai-cover-letter-qa")
    @limiter.limit("60 per 5 minutes")
    def index():
        return render_template("letters/site_qa_index.html")

    @bp.post("/ai-cover-letter-qa/start")
    @limiter.limit("30 per hour")
    def start():
        data = fields({"language", "length", "tone"})
        result = service.start(
            g.current_user.id,
            data["language"],
            data["length"],
            data["tone"],
        )
        return render_template("letters/site_qa_preview.html", **result)

    @bp.post("/ai-cover-letter-qa/<language>/<uuid:letter_id>/generate")
    @limiter.limit("10 per hour")
    def generate(language, letter_id):
        data = fields({"review_token"})
        result = service.generate(g.current_user.id, language, str(letter_id), data["review_token"])
        if result["status"] == "proposal":
            return redirect(url_for(
                "ai005_site_qa.detail",
                language=language,
                letter_id=letter_id,
                proposal=result["proposal"]["id"],
            ), code=303)
        if result["status"] == "already_processed":
            return render_template("letters/site_qa_error.html",
                error="Этот тестовый запрос уже был обработан. Повторный вызов Alice не выполнен."), 409
        return render_template("letters/site_qa_error.html",
            error="Alice не подготовила валидный черновик. Повторный вызов автоматически не выполнялся."), 503

    @bp.get("/ai-cover-letter-qa/<language>/<uuid:letter_id>")
    @limiter.limit("60 per 5 minutes")
    def detail(language, letter_id):
        data = service.detail(g.current_user.id, language, str(letter_id), request.args.get("proposal"))
        return render_template("letters/site_qa_detail.html", language=language, **data)

    @bp.post("/ai-cover-letter-qa/<language>/<uuid:letter_id>/accept")
    @limiter.limit("30 per hour")
    def accept(language, letter_id):
        data = fields({"expected_revision", "proposal_id", "subject", "body", "confirm"})
        service.accept(
            g.current_user.id,
            language,
            str(letter_id),
            expected=data["expected_revision"],
            proposal_id=data["proposal_id"],
            subject=data["subject"],
            body=data["body"],
            confirmed=data["confirm"] == "1",
        )
        return redirect(url_for("ai005_site_qa.detail", language=language, letter_id=letter_id), code=303)

    @bp.post("/ai-cover-letter-qa/<language>/<uuid:letter_id>/proposals/<uuid:proposal_id>/reject")
    @limiter.limit("30 per hour")
    def reject(language, letter_id, proposal_id):
        data = fields({"expected_revision", "confirm"})
        service.reject(
            g.current_user.id,
            language,
            str(letter_id),
            str(proposal_id),
            expected=data["expected_revision"],
            confirmed=data["confirm"] == "1",
        )
        return redirect(url_for("ai005_site_qa.detail", language=language, letter_id=letter_id), code=303)

    @bp.get("/ai-cover-letter-qa/<language>/<uuid:letter_id>/versions/<int:number>")
    @limiter.limit("60 per 5 minutes")
    def version(language, letter_id, number):
        item = service.version(g.current_user.id, language, str(letter_id), number)
        return render_template("letters/site_qa_version.html", language=language, letter_id=str(letter_id), version=item)

    @bp.get("/ai-cover-letter-qa/<language>/<uuid:letter_id>/versions/<int:number>/export.txt")
    @limiter.limit("30 per hour")
    def export(language, letter_id, number):
        raw = service.export(g.current_user.id, language, str(letter_id), number)
        response = Response(raw, content_type="text/plain; charset=utf-8")
        response.headers["Content-Disposition"] = f'attachment; filename="alice-site-qa-{letter_id}-v{number}.txt"'
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    return bp
