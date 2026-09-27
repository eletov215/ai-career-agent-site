"""Separate admin namespace; never substitutes the authenticated user or legal gate."""
from __future__ import annotations

import os

from flask import Blueprint, Response, abort, g, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError

from domain.cover_letter import LetterError, MAX_BODY, MAX_SUBJECT
from security import limiter
from services.admin_access import is_search_admin
from services.cover_letter_labels import ERROR_MESSAGES
from services.letter_site_qa import LetterSiteQA

BASE = '/admin/ai/letters/site-qa'


def _flag(name):
    raw = os.environ.get(name, '0').strip()
    if raw not in ('0', '1'):
        raise ValueError('Invalid SITE QA boolean configuration')
    return raw == '1'


def _rate_key():
    return 'site-qa:' + str(getattr(getattr(g, 'current_user', None), 'id', 'anonymous'))


def create_letter_site_qa_blueprint(settings, storage, *, service=None):
    bp = Blueprint('letter_site_qa', __name__)
    # Disabled startup neither reads the DB nor requires extra credentials.
    qa = service
    if qa is None and _flag('AI_SITE_QA_ENABLED'):
        qa = LetterSiteQA(storage, settings, enabled=True, live_enabled=_flag('AI_SITE_QA_LIVE_ENABLED'))

    @bp.before_request
    def require_admin():
        if qa is None or not qa.enabled or not is_search_admin(getattr(g, 'current_user', None), settings):
            abort(404)
        qa.authorize(g.current_user.id)
        if request.args and any(len(request.args.getlist(k)) != 1 for k in request.args):
            raise LetterError('invalid_request')

    @bp.after_request
    def private_response(response):
        response.headers['Cache-Control'] = 'no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers.pop('ETag', None)
        return response

    def page(view, **kwargs):
        return render_template('letters/site_qa.html', view=view, live_enabled=qa.live_enabled,
                               max_body=MAX_BODY, max_subject=MAX_SUBJECT, **kwargs)

    @bp.errorhandler(LetterError)
    def letter_error(error):
        code = str(error)
        status = (404 if code in ('not_found', 'verified_account_required') else
                  409 if code in ('stale_write', 'stale_source', 'idempotency_conflict', 'invalid_preview') else
                  503 if code in ('generation_unavailable', 'storage_integrity', 'storage_unavailable') else 400)
        return page('error', error=ERROR_MESSAGES.get(code, ERROR_MESSAGES['invalid_request'])), status

    @bp.errorhandler(SQLAlchemyError)
    @bp.errorhandler(OSError)
    def storage_error(_error):
        return letter_error(LetterError('storage_unavailable'))

    def fields(required, optional=()):
        if request.content_length and request.content_length > 65536:
            abort(413)
        if request.is_json or request.files or request.args:
            raise LetterError('invalid_request')
        allowed = set(required) | set(optional) | {'csrf_token'}
        if not set(required) <= set(request.form) or set(request.form) - allowed:
            raise LetterError('invalid_request')
        if any(len(request.form.getlist(k)) != 1 for k in request.form):
            raise LetterError('invalid_request')
        return request.form

    @bp.get(BASE)
    @limiter.limit('60 per 5 minutes', key_func=_rate_key)
    def home():
        if request.args:
            raise LetterError('invalid_request')
        return page('home', intention=qa.new_intention(g.current_user.id), recent=qa.recent(g.current_user.id))

    @bp.post(BASE + '/prepare')
    @limiter.limit('20 per hour', key_func=_rate_key)
    def prepare():
        data = fields({'intention', 'language', 'length', 'tone'})
        letter_id = qa.prepare(g.current_user.id, data['intention'], data['language'], data['length'], data['tone'])
        return redirect(url_for('.detail', letter_id=letter_id), code=303)

    @bp.get(BASE + '/<uuid:letter_id>')
    @limiter.limit('60 per 5 minutes', key_func=_rate_key)
    def detail(letter_id):
        if request.args:
            raise LetterError('invalid_request')
        _, _, record = qa.record(g.current_user.id, str(letter_id))
        return page('detail', record=record)

    @bp.post(BASE + '/<uuid:letter_id>/preview')
    @limiter.limit('30 per hour', key_func=_rate_key)
    def preview(letter_id):
        fields(set())
        value = qa.preview(g.current_user.id, str(letter_id))
        return page('preview', preview=value, letter_id=str(letter_id))

    @bp.post(BASE + '/<uuid:letter_id>/generate')
    @limiter.limit('10 per hour', key_func=_rate_key)
    def generate(letter_id):
        data = fields({'review_token'})
        result = qa.generate(g.current_user.id, str(letter_id), data['review_token'])
        if result['status'] == 'proposal':
            return redirect(url_for('.detail', letter_id=letter_id), code=303)
        if result['status'] == 'already_processed':
            return page('processed', letter_id=str(letter_id)), 409
        # No raw provider errors, review tokens, credentials or automatic retry.
        return page('failed', letter_id=str(letter_id)), 503

    @bp.post(BASE + '/<uuid:letter_id>/save')
    @limiter.limit('60 per hour', key_func=_rate_key)
    def save(letter_id):
        data = fields({'expected_revision', 'subject', 'body', 'confirm'}, {'proposal_id'})
        try:
            qa.save(g.current_user.id, str(letter_id), data['expected_revision'], data['subject'], data['body'],
                    data.get('proposal_id') or None, confirmed=data['confirm'] == '1')
        except LetterError as error:
            if str(error) in ('stale_write', 'stale_source'):
                return page('conflict', draft={'subject': data['subject'][:MAX_SUBJECT],
                    'body': data['body'][:MAX_BODY]}, letter_id=str(letter_id)), 409
            raise
        return redirect(url_for('.detail', letter_id=letter_id), code=303)

    @bp.post(BASE + '/<uuid:letter_id>/proposals/<uuid:proposal_id>/reject')
    @limiter.limit('30 per hour', key_func=_rate_key)
    def reject(letter_id, proposal_id):
        data = fields({'expected_revision'})
        qa.reject(g.current_user.id, str(letter_id), str(proposal_id), data['expected_revision'])
        return redirect(url_for('.detail', letter_id=letter_id), code=303)

    @bp.get(BASE + '/<uuid:letter_id>/versions/<int:number>')
    @limiter.limit('60 per 5 minutes', key_func=_rate_key)
    def version(letter_id, number):
        return page('version', version=qa.version(g.current_user.id, str(letter_id), number), letter_id=str(letter_id))

    @bp.get(BASE + '/<uuid:letter_id>/versions/<int:number>/export.txt')
    @limiter.limit('30 per hour', key_func=_rate_key)
    def export(letter_id, number):
        raw = qa.export(g.current_user.id, str(letter_id), number)
        response = Response(raw, content_type='text/plain; charset=utf-8')
        response.headers['Content-Disposition'] = f'attachment; filename="site-qa-letter-{letter_id}-v{number}.txt"'
        return response

    @bp.get(BASE + '/<uuid:letter_id>/compare')
    @limiter.limit('30 per 5 minutes', key_func=_rate_key)
    def compare(letter_id):
        if set(request.args) != {'left', 'right'}:
            raise LetterError('invalid_request')
        return page('compare', compared=qa.compare(g.current_user.id, str(letter_id),
                    request.args['left'], request.args['right']), letter_id=str(letter_id))

    return bp
