"""Private native-form review. No browser route calls the provider path."""
import secrets
from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError
from domain.vacancy_match import MatchError, MatchRequest
from services.ai.registry import ContractError
from services.ai.match_labels import UI
from services.admin_access import is_search_admin
from security import limiter

_REVIEW_SESSION_KEY = 'ai004_match_review_owner'
_GATE_ENDPOINTS = {'vacancy_match.review_gate', 'vacancy_match.enable_review', 'vacancy_match.disable_review'}


def create_vacancy_match_blueprint(service, settings):
    bp = Blueprint('vacancy_match', __name__)

    @bp.before_request
    def private_boundary():
        if not is_search_admin(getattr(g, 'current_user', None), settings):
            abort(404)
        if request.endpoint not in _GATE_ENDPOINTS and session.get(_REVIEW_SESSION_KEY) != g.current_user.id:
            abort(404)

    @bp.after_request
    def protect_response(response):
        response.headers['Cache-Control'] = 'no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        response.headers['Referrer-Policy'] = 'strict-origin'
        response.headers.pop('ETag', None)
        return response

    @bp.errorhandler(MatchError)
    def feature_error(error):
        reason = str(error)
        conflicts = {'stale_source', 'idempotency_conflict', 'stale_report'}
        unavailable = {'storage_unavailable', 'invalid_saved_report', 'invalid_contract'}
        status = 404 if reason in {'not_found', 'verified_account_required'} else 409 if reason in conflicts else 503 if reason in unavailable else 400
        key = 'error_conflict' if reason in conflicts else 'error_storage' if reason in unavailable else 'limit' if reason == 'history_limit' else 'error_invalid'
        if request.path.startswith('/api/'):
            return jsonify(ok=False, error=UI['ru'][key]), status
        return render_template('matching/error.html', ui=UI['ru'], error=UI['ru'][key]), status

    @bp.errorhandler(SQLAlchemyError)
    @bp.errorhandler(OSError)
    def storage_error(_error):
        return feature_error(MatchError('storage_unavailable'))

    @bp.errorhandler(ContractError)
    def contract_error(_error):
        return feature_error(MatchError('invalid_contract'))

    def fields(allowed, required=()):
        if request.content_length and request.content_length > 8192:
            abort(413)
        if request.files or request.is_json or set(request.form) - set(allowed) - {'csrf_token'}:
            raise MatchError('invalid_request')
        if any(len(request.form.getlist(k)) != 1 for k in request.form) or not set(required) <= request.form.keys():
            raise MatchError('invalid_request')
        return request.form

    @bp.get('/ai-match/review')
    @limiter.limit('30 per 5 minutes')
    def review_gate():
        return render_template('matching/review_gate.html', ui=UI['ru'],
                               enabled=session.get(_REVIEW_SESSION_KEY) == g.current_user.id)

    @bp.post('/ai-match/review/enable')
    @limiter.limit('20 per hour')
    def enable_review():
        fields(set())
        session[_REVIEW_SESSION_KEY] = g.current_user.id
        return redirect(url_for('vacancy_match.index'), code=303)

    @bp.post('/ai-match/review/disable')
    @limiter.limit('20 per hour')
    def disable_review():
        fields(set())
        session.pop(_REVIEW_SESSION_KEY, None)
        return redirect(url_for('vacancy_match.review_gate'), code=303)

    @bp.get('/ai-match')
    @limiter.limit('60 per 5 minutes')
    def index():
        return render_template('matching/index.html', ui=UI['ru'], locales=UI, choices=service.choices(),
                               reports=service.history(g.current_user.id), operation_key=lambda: secrets.token_urlsafe(24))

    @bp.post('/ai-match/reference')
    @limiter.limit('20 per hour')
    def reference():
        data = fields({'fixture_id', 'source_hash', 'operation_key'}, {'fixture_id', 'source_hash', 'operation_key'})
        report = service.create_reference(MatchRequest(g.current_user.id, data['fixture_id'], data['source_hash'], data['operation_key']))
        return redirect(url_for('vacancy_match.detail', report_id=report['id']), code=303)

    @bp.get('/ai-match/<uuid:report_id>')
    @limiter.limit('60 per 5 minutes')
    def detail(report_id):
        report = service.get(g.current_user.id, str(report_id))
        return render_template('matching/detail.html', ui=UI[report['language']], report=report)

    @bp.get('/api/vacancy-matches/<uuid:report_id>')
    @limiter.limit('60 per 5 minutes')
    def read_api(report_id):
        return jsonify(ok=True, report=service.get(g.current_user.id, str(report_id)))

    @bp.post('/ai-match/<uuid:report_id>/delete')
    @limiter.limit('20 per hour')
    def delete_report(report_id):
        data = fields({'result_hash', 'confirm'}, {'result_hash', 'confirm'})
        if data['confirm'] != '1':
            raise MatchError('invalid_request')
        service.delete(g.current_user.id, str(report_id), data['result_hash'])
        return redirect(url_for('vacancy_match.index'), code=303)

    return bp
