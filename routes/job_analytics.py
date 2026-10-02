"""Private GET-only JOB-004 analytics page."""
from flask import Blueprint, abort, g, redirect, render_template, request, url_for
from security import limiter


def create_job_analytics_blueprint(service):
    bp = Blueprint("job_analytics", __name__)

    @bp.before_request
    def require_verified_owner():
        user = getattr(g, "current_user", None)
        if user is None:
            return redirect(url_for("auth.login", next=request.full_path if request.query_string else request.path))
        if user.status != "active" or user.email_verified_at is None:
            abort(404)

    @bp.after_request
    def private_headers(response):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers.pop("ETag", None)
        return response

    @bp.get("/analytics")
    @limiter.limit("60 per 5 minutes")
    def index():
        period = request.args.get("period", "30")
        source = request.args.get("source") or None
        if len(period) > 3 or (source is not None and len(source) > 32):
            abort(400)
        report = service.report(g.current_user.id, period=period, source=source)
        return render_template("analytics/index.html", report=report)

    return bp
