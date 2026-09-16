"""Private AI-003 UI and bounded ID-only API. No provider dispatch routes."""
from __future__ import annotations

import json
import secrets
from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy.exc import SQLAlchemyError

from domain.resume_interview import InterviewCommand, InterviewError, StartInterviewRequest
from security import limiter
from services.admin_access import is_search_admin
from services.ai.interview_labels import UI, ERRORS

_COMMAND_FIELDS = {'action', 'expected_revision', 'source_hash', 'operation_key', 'node_id',
                   'choice_id', 'answer_index', 'selected_fact_ids', 'confirm'}
_CONFLICTS = {'stale_source', 'stale_interview', 'stale_draft', 'idempotency_conflict',
              'already_confirmed', 'unexpected_question', 'history_limit'}
_REVIEW_SESSION_KEY = 'ai_interview_review_session'
_REVIEW_GATE_ENDPOINTS = {
    'resume_interview.review_gate',
    'resume_interview.enable_review',
    'resume_interview.disable_review',
}


def create_resume_interview_blueprint(service, settings):
    bp = Blueprint('resume_interview', __name__)

    @bp.before_request
    def private_boundary():
        # Every AI-003 review route remains hidden from ordinary users. The
        # allowlisted administrator can explicitly unlock the synthetic review
        # UI for the current signed browser session. This avoids depending on
        # a deployment-time environment toggle for a one-off staging review.
        if not is_search_admin(getattr(g, 'current_user', None), settings):
            abort(404)
        if request.endpoint in _REVIEW_GATE_ENDPOINTS:
            return None
        if not settings.ai_interview_review_enabled and session.get(_REVIEW_SESSION_KEY) is not True:
            abort(404)

    @bp.after_request
    def protect_response(response):
        response.headers['Cache-Control'] = 'no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Referrer-Policy'] = 'strict-origin'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        response.headers.pop('ETag', None)
        return response

    @bp.errorhandler(InterviewError)
    def feature_error(error):
        reason = str(error)
        status = 404 if reason in {'not_found', 'verified_account_required'} else 409 if reason in _CONFLICTS else 503 if reason == 'storage_unavailable' else 400
        message = ERRORS.get(reason, ERRORS['invalid_request'])
        if request.path.startswith('/api/'):
            return jsonify(ok=False, reason=reason if reason in ERRORS else 'invalid_request', error=message), status
        return render_template('interview/error.html', ui=UI, error=message), status

    @bp.errorhandler(SQLAlchemyError)
    def unavailable(_error):
        # Never render/log SQL parameters, owner data or exception messages.
        return feature_error(InterviewError('storage_unavailable'))

    def form_fields(allowed):
        if request.files or request.is_json or set(request.form) - allowed - {'csrf_token'}:
            raise InterviewError('invalid_request')
        for key in request.form:
            maximum = 12 if key == 'selected_fact_ids' else 1
            if not 1 <= len(request.form.getlist(key)) <= maximum:
                raise InterviewError('invalid_request')
        return request.form.to_dict()

    def parse_command(session_id, *, api=False):
        if api:
            if request.mimetype != 'application/json' or len(request.get_data()) > 16384:
                raise InterviewError('invalid_request')
            def pairs(items):
                obj = {}
                for key, value in items:
                    if key in obj:
                        raise InterviewError('invalid_request')
                    obj[key] = value
                return obj
            try:
                data = json.loads(request.get_data(), object_pairs_hook=pairs,
                    parse_constant=lambda _: (_ for _ in ()).throw(InterviewError('invalid_request')))
            except (ValueError, UnicodeError, RecursionError):
                raise InterviewError('invalid_request') from None
            if not isinstance(data, dict) or set(data) - _COMMAND_FIELDS:
                raise InterviewError('invalid_request')
        else:
            data = form_fields(_COMMAND_FIELDS)
            data.pop('csrf_token', None)
            try:
                data['expected_revision'] = int(data.get('expected_revision', ''))
                if 'answer_index' in data:
                    data['answer_index'] = int(data['answer_index'])
            except (ValueError, TypeError):
                raise InterviewError('invalid_request') from None
            if data.get('confirm') not in (None, '1'):
                raise InterviewError('invalid_request')
            data['confirm'] = data.get('confirm') == '1'
            data['selected_fact_ids'] = request.form.getlist('selected_fact_ids')
        selected = data.get('selected_fact_ids', [])
        if not isinstance(selected, list) or len(selected) > 12:
            raise InterviewError('invalid_request')
        return InterviewCommand(user_id=g.current_user.id, session_id=str(session_id),
            expected_revision=data.get('expected_revision'), source_hash=data.get('source_hash'),
            operation_key=data.get('operation_key'), action=data.get('action'), node_id=data.get('node_id'),
            choice_id=data.get('choice_id'), answer_index=data.get('answer_index'),
            selected_fact_ids=tuple(selected), confirm=data.get('confirm', False))

    @bp.get('/ai-interview/review')
    @limiter.limit('30 per 5 minutes')
    def review_gate():
        return render_template(
            'interview/review_gate.html',
            ui=UI,
            environment_enabled=bool(settings.ai_interview_review_enabled),
            session_enabled=session.get(_REVIEW_SESSION_KEY) is True,
        )

    @bp.post('/ai-interview/review/enable')
    @limiter.limit('20 per hour')
    def enable_review():
        session[_REVIEW_SESSION_KEY] = True
        session.modified = True
        return redirect(url_for('resume_interview.index'), code=303)

    @bp.post('/ai-interview/review/disable')
    @limiter.limit('20 per hour')
    def disable_review():
        session.pop(_REVIEW_SESSION_KEY, None)
        session.modified = True
        return redirect(url_for('resume_interview.review_gate'), code=303)

    @bp.get('/ai-interview')
    @limiter.limit('60 per 5 minutes')
    def index():
        return render_template('interview/index.html', ui=UI, choices=service.choices(),
            interviews=service.history(g.current_user.id), operation_key=lambda: secrets.token_urlsafe(24))

    @bp.post('/ai-interview/start')
    @limiter.limit('20 per hour')
    def start():
        data = form_fields({'fixture_id', 'source_hash', 'operation_key'})
        result = service.start(StartInterviewRequest(g.current_user.id, data.get('fixture_id', ''),
            data.get('source_hash', ''), data.get('operation_key', '')))
        return redirect(url_for('resume_interview.detail', draft_id=result['draft_id']), code=303)

    @bp.get('/resume-builder/<uuid:draft_id>/interview')
    @limiter.limit('60 per 5 minutes')
    def detail(draft_id):
        sid = service.for_draft(g.current_user.id, str(draft_id))
        if sid is None:
            abort(404)
        return render_template('interview/detail.html', ui=UI, interview=service.get(g.current_user.id, sid),
            operation_key=lambda: secrets.token_urlsafe(24))

    @bp.post('/ai-interview/<uuid:session_id>/actions')
    @limiter.limit('120 per hour')
    def action(session_id):
        result = service.execute(parse_command(session_id))
        return redirect(url_for('resume_interview.detail', draft_id=result['draft_id'], _anchor='interview-current'), code=303)

    @bp.get('/api/resume-interviews/<uuid:session_id>')
    @limiter.limit('60 per 5 minutes')
    def read_api(session_id):
        return jsonify(ok=True, interview=service.get(g.current_user.id, str(session_id)))

    @bp.post('/api/resume-interviews/<uuid:session_id>/actions')
    @limiter.limit('120 per hour')
    def action_api(session_id):
        return jsonify(ok=True, interview=service.execute(parse_command(session_id, api=True)))

    return bp
