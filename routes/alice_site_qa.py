"""Admin-only synthetic AI-005 Alice SITE QA routes."""
from __future__ import annotations

from flask import Blueprint, abort, g, redirect, render_template, request, url_for

from domain.cover_letter import LetterError
from routes.auth import login_required
from security import limiter
from services.admin_access import is_search_admin
from services.ai.letter_admission import synthetic_cases
from services.cover_letter_labels import ERROR_MESSAGES, UI


def create_alice_site_qa_blueprint(settings, service):
    bp=Blueprint("alice_site_qa",__name__)

    def require_admin():
        if not is_search_admin(getattr(g,"current_user",None),settings):
            abort(404)

    def strict_form(required):
        if request.content_length and request.content_length>65536:
            abort(413)
        if request.is_json or request.files:
            raise LetterError("invalid_request")
        allowed=set(required)|{"csrf_token"}
        if set(request.form)-allowed or not set(required)<=set(request.form):
            raise LetterError("invalid_request")
        if any(len(request.form.getlist(key))!=1 for key in request.form):
            raise LetterError("invalid_request")
        return request.form

    @bp.after_request
    def protect(response):
        response.headers["Cache-Control"]="no-store, max-age=0"
        response.headers["Pragma"]="no-cache"
        response.headers["X-Robots-Tag"]="noindex, nofollow"
        response.headers["Referrer-Policy"]="strict-origin"
        response.headers.pop("ETag",None)
        return response

    @bp.errorhandler(LetterError)
    def letter_error(error):
        code=str(error)
        status=409 if code in ("stale_write","stale_source","idempotency_conflict") else (
            503 if code in ("generation_unavailable","storage_integrity","storage_unavailable") else 400)
        message=ERROR_MESSAGES.get(code,ERROR_MESSAGES["invalid_request"])
        return render_template("alice_qa/error.html",ui=UI,error=message),status

    @bp.get("/admin/alice-qa")
    @login_required
    @limiter.limit("60 per 5 minutes")
    def index():
        require_admin()
        cases=synthetic_cases()
        editor={"language":"ru","length":"short","tone":"professional"}
        return render_template("alice_qa/index.html",ui=UI,cases=cases,editor=editor)

    @bp.post("/admin/alice-qa/preview")
    @login_required
    @limiter.limit("20 per hour")
    def preview():
        require_admin()
        data=strict_form({"language","length","tone"})
        prepared=service.prepare(g.current_user.id,data["language"],data["length"],data["tone"])
        return render_template("alice_qa/preview.html",ui=UI,prepared=prepared)

    @bp.post("/admin/alice-qa/<uuid:letter_id>/generate")
    @login_required
    @limiter.limit("10 per hour")
    def generate(letter_id):
        require_admin()
        data=strict_form({"review_token"})
        result=service.generate(g.current_user.id,str(letter_id),data["review_token"])
        if result["status"]=="proposal":
            return redirect(url_for("cover_letters.detail",letter_id=letter_id,
                                    proposal=result["proposal"]["id"]),code=303)
        if result["status"]=="already_processed":
            return render_template("alice_qa/error.html",ui=UI,error=UI["already_processed"]),409
        return render_template("alice_qa/error.html",ui=UI,error=UI["generation_failed"]),503

    return bp
