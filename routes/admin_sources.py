"""Read-only SEARCH-005 administrator source-health center."""

from __future__ import annotations

import time
from typing import Any

from flask import Blueprint, abort, g, jsonify, render_template

from routes.auth import login_required
from security import limiter
from services.admin_access import is_search_admin
from services.source_health import list_health_views


def _safe_cache(vacancy_store: Any, provider: str) -> tuple[int, int | None]:
    try:
        count = max(0, int(vacancy_store.count(keyword="", sources=[provider]) or 0))
    except Exception:
        count = 0
    try:
        age = vacancy_store.source_age_seconds(provider)
        age = None if age is None else max(0, int(age))
    except Exception:
        age = None
    return count, age


def _trudvsem_details(storage: Any, settings: Any) -> dict[str, object]:
    details: dict[str, object] = {
        "sync_status": None,
        "sync_started_at": None,
        "sync_finished_at": None,
        "sync_processed": 0,
        "sync_saved": 0,
        "worker_alive": False,
        "worker_status": None,
        "worker_heartbeat_age_seconds": None,
    }
    try:
        run = storage.sync_runs.active("trudvsem") or storage.sync_runs.latest("trudvsem")
        if run is not None:
            details.update(
                {
                    "sync_status": run.status,
                    "sync_started_at": run.started_at,
                    "sync_finished_at": run.finished_at,
                    "sync_processed": max(0, int(run.processed or 0)),
                    "sync_saved": max(0, int(run.saved or 0)),
                }
            )
    except Exception:
        pass
    try:
        worker = storage.sync_workers.latest("trudvsem")
        if worker is not None:
            age = max(0, int(time.time()) - int(worker.heartbeat_at))
            details.update(
                {
                    "worker_alive": age <= int(settings.trudvsem_sync_stale_seconds),
                    "worker_status": str(worker.status)[:32],
                    "worker_heartbeat_age_seconds": age,
                }
            )
    except Exception:
        pass
    return details


def _payload(settings: Any, storage: Any, vacancy_store: Any) -> dict[str, object]:
    sources: list[dict[str, object]] = []
    for view in list_health_views():
        item = view.as_dict()
        cache_count, cache_age = _safe_cache(vacancy_store, view.provider)
        item["cache_item_count"] = cache_count
        item["cache_age_seconds"] = cache_age
        if view.provider == "trudvsem":
            item.update(_trudvsem_details(storage, settings))
        sources.append(item)
    return {
        "status": "ok",
        "generated_at": int(time.time()),
        "sources": sources,
    }


def create_admin_sources_blueprint(settings: Any, storage: Any, vacancy_store: Any) -> Blueprint:
    bp = Blueprint("admin_sources", __name__)

    def _require_admin() -> None:
        if not is_search_admin(getattr(g, "current_user", None), settings):
            abort(404)

    @bp.app_context_processor
    def admin_template_context():
        return {
            "search_admin_access": is_search_admin(getattr(g, "current_user", None), settings)
        }

    @bp.after_request
    def protect_admin_response(response):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers.pop("ETag", None)
        return response

    @bp.get("/admin/sources")
    @login_required
    @limiter.limit("30 per 5 minutes")
    def source_center():
        _require_admin()
        payload = _payload(settings, storage, vacancy_store)
        return render_template("admin/source_center.html", source_payload=payload)

    @bp.get("/api/admin/sources")
    @login_required
    @limiter.limit("60 per 5 minutes")
    def source_center_api():
        _require_admin()
        return jsonify(_payload(settings, storage, vacancy_store))

    return bp
