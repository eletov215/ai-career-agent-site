"""Native and progressively enhanced JOB-001 forms; all objects are owner-scoped."""
from __future__ import annotations
import json
from datetime import datetime, timezone

from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError
from domain.saved_vacancy import MAX_NOTE, SavedVacancyError
from services.saved_vacancy_labels import UI, ERROR_MESSAGES
from security import limiter


def create_saved_vacancies_blueprint(service):
    bp = Blueprint('saved_vacancies', __name__)

    def wants_json():
        return request.path.startswith('/api/') or request.accept_mimetypes.best == 'application/json'

    @bp.before_request
    def require_verified_owner():
        user = getattr(g, 'current_user', None)
        if user is None:
            if wants_json():
                return jsonify(ok=False, error=UI['login_required']), 401
            return redirect(url_for('auth.login', next='/saved-vacancies'))
        if user.status != 'active' or user.email_verified_at is None:
            abort(404)

    @bp.after_request
    def private_headers(response):
        response.headers['Cache-Control'] = 'no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        response.headers['Referrer-Policy'] = 'strict-origin'
        response.headers.pop('ETag', None)
        return response

    @bp.app_template_filter('saved_time')
    def saved_time(value):
        try:
            return datetime.fromtimestamp(int(value), timezone.utc).strftime('%d.%m.%Y %H:%M UTC')
        except (ValueError, TypeError, OverflowError, OSError):
            return '-'

    @bp.errorhandler(SavedVacancyError)
    def feature_error(error):
        code = str(error)
        status = (404 if code in ('not_found','verified_account_required') else
                  409 if code in ('stale_source','stale_write','ambiguous_group','invalid_reference','has_letters') else
                  503 if code in ('storage_unavailable','invalid_saved_snapshot') else 400)
        message = ERROR_MESSAGES.get(code, UI['invalid'])
        if wants_json():
            return jsonify(ok=False, error=message, code=code if code in ERROR_MESSAGES else 'invalid_request'), status
        return render_template('saved_vacancies/error.html', ui=UI, error=message), status

    @bp.errorhandler(SQLAlchemyError)
    @bp.errorhandler(OSError)
    def storage_error(_error):
        return feature_error(SavedVacancyError('storage_unavailable'))

    def fields(required, *, limit=16384):
        if request.content_length is not None and request.content_length > limit:
            abort(413)
        if request.is_json or request.files:
            raise SavedVacancyError('invalid_request')
        allowed = set(required) | {'csrf_token'}
        if (set(request.form) - allowed or not set(required) <= set(request.form)
                or any(len(request.form.getlist(key)) != 1 for key in request.form)):
            raise SavedVacancyError('invalid_request')
        return request.form

    @bp.get('/saved-vacancies')
    @limiter.limit('60 per 5 minutes')
    def index():
        if any(len(request.args.getlist(key)) != 1 for key in request.args):
            raise SavedVacancyError('invalid_request')
        try:
            page = int(request.args.get('page','1'))
        except (TypeError, ValueError):
            raise SavedVacancyError('invalid_request') from None
        results = service.list(g.current_user.id, query=request.args.get('q',''), page=page)
        return render_template('saved_vacancies/index.html', ui=UI, results=results)

    @bp.post('/saved-vacancies/save')
    @limiter.limit('60 per hour')
    def save():
        data = fields({'reference'})
        record = service.save(g.current_user.id, data['reference'])
        target = url_for('saved_vacancies.detail', saved_id=record['id'])
        if wants_json():
            return jsonify(ok=True, id=record['id'], created=record['created'], url=target), 201 if record['created'] else 200
        return redirect(target, code=303)

    @bp.get('/saved-vacancies/<uuid:saved_id>')
    @limiter.limit('60 per 5 minutes')
    def detail(saved_id):
        record = service.get(g.current_user.id, str(saved_id))
        return render_template('saved_vacancies/detail.html', ui=UI, record=record, error=None,
                               draft_note=record['note'], note_limit=MAX_NOTE)

    @bp.get('/api/saved-vacancies/<uuid:saved_id>')
    @limiter.limit('60 per 5 minutes')
    def read_api(saved_id):
        return jsonify(ok=True, vacancy=service.get(g.current_user.id, str(saved_id)))

    @bp.post('/saved-vacancies/<uuid:saved_id>/note')
    @limiter.limit('60 per hour')
    def save_note(saved_id):
        data = fields({'note','expected_revision'}, limit=65536)
        try:
            service.update_note(g.current_user.id, str(saved_id), data['note'], data['expected_revision'])
        except SavedVacancyError as error:
            if str(error) == 'stale_write' and not wants_json():
                # Preserve the unsaved user text. Never silently overwrite the
                # newer note or auto-resubmit it against a fresh revision.
                record = service.get(g.current_user.id, str(saved_id))
                return render_template('saved_vacancies/conflict.html', ui=UI,
                    record=record, draft_note=data['note'][:MAX_NOTE], error=ERROR_MESSAGES['stale_write']), 409
            raise
        return redirect(url_for('saved_vacancies.detail', saved_id=saved_id), code=303)

    @bp.post('/saved-vacancies/<uuid:saved_id>/delete')
    @limiter.limit('30 per hour')
    def delete_saved(saved_id):
        data = fields({'expected_revision','confirm'})
        if data['confirm'] != '1':
            raise SavedVacancyError('confirmation_required')
        service.delete(g.current_user.id, str(saved_id), data['expected_revision'])
        return redirect(url_for('saved_vacancies.index'), code=303)

    @bp.post('/saved-vacancies/import-legacy')
    @limiter.limit('10 per hour')
    def import_legacy():
        data = fields({'keys','confirm'}, limit=131072)
        if data['confirm'] != '1':
            raise SavedVacancyError('confirmation_required')
        try:
            keys = json.loads(data['keys'])
        except (ValueError, TypeError):
            raise SavedVacancyError('invalid_legacy') from None
        return jsonify(ok=True, **service.import_legacy(g.current_user.id, keys))

    return bp
