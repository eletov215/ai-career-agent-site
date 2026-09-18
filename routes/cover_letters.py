"""Private native AI-005 forms. No provider network or outbound sending."""
from __future__ import annotations
import secrets
from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, Response, url_for
from sqlalchemy.exc import SQLAlchemyError
from domain.cover_letter import LetterError, MAX_BODY, MAX_SUBJECT
from services.cover_letter_labels import UI, ERROR_MESSAGES
from security import limiter


def create_cover_letters_blueprint(service):
    bp=Blueprint('cover_letters',__name__)
    def wants_json():
        return request.path.startswith('/api/') or request.accept_mimetypes.best=='application/json'

    @bp.before_request
    def require_owner():
        user=getattr(g,'current_user',None)
        if user is None:
            if wants_json():return jsonify(ok=False,error=ERROR_MESSAGES['verified_account_required']),401
            return redirect(url_for('auth.login',next='/cover-letters'))
        if user.status!='active' or user.email_verified_at is None:abort(404)
        if any(len(request.args.getlist(k))!=1 for k in request.args):raise LetterError('invalid_request')

    @bp.after_request
    def private_response(response):
        response.headers['Cache-Control']='no-store, max-age=0'
        response.headers['Pragma']='no-cache'
        response.headers['X-Robots-Tag']='noindex, nofollow'
        response.headers['Referrer-Policy']='strict-origin'
        response.headers.pop('ETag',None)
        return response

    @bp.errorhandler(LetterError)
    def error_response(error):
        code=str(error)
        status=(404 if code in ('not_found','verified_account_required') else
                409 if code in ('stale_write','stale_source','idempotency_conflict','current_version') else
                503 if code in ('generation_unavailable','storage_integrity','storage_unavailable') else 400)
        message=ERROR_MESSAGES.get(code,ERROR_MESSAGES['invalid_request'])
        if wants_json():return jsonify(ok=False,error=message,code=code if code in ERROR_MESSAGES else 'invalid_request'),status
        return render_template('letters/error.html',ui=UI,error=message),status

    @bp.errorhandler(SQLAlchemyError)
    @bp.errorhandler(OSError)
    def storage_error(_error):
        return error_response(LetterError('storage_unavailable'))

    def fields(required,optional=(),repeated=()):
        if request.content_length and request.content_length>65536:abort(413)
        if request.is_json or request.files:raise LetterError('invalid_request')
        allowed=set(required)|set(optional)|set(repeated)|{'csrf_token'}
        if not set(required)<=set(request.form) or set(request.form)-allowed:raise LetterError('invalid_request')
        if any(len(request.form.getlist(k))!=1 for k in request.form if k not in repeated):raise LetterError('invalid_request')
        return request.form

    def render_editor(record,proposal=None):
        if proposal is not None and (proposal['base_revision']!=record['revision'] or record['source_stale']):
            return render_template('letters/conflict.html',ui=UI,record=record,draft=proposal['content']),409
        return render_template('letters/detail.html',ui=UI,record=record,proposal=proposal,
            editor=proposal['content'] if proposal else record['content'],operation_key=secrets.token_urlsafe(24),
            max_body=MAX_BODY,max_subject=MAX_SUBJECT)

    @bp.get('/cover-letters')
    @limiter.limit('60 per 5 minutes')
    def index():
        results=service.list(g.current_user.id,page=request.args.get('page','1'))
        return render_template('letters/index.html',ui=UI,results=results,source=None,saved_id=None)

    @bp.get('/saved-vacancies/<uuid:saved_id>/letters')
    @limiter.limit('60 per 5 minutes')
    def for_vacancy(saved_id):
        saved_id=str(saved_id)
        source=service.source(g.current_user.id,saved_id)
        results=service.list(g.current_user.id,saved_id=saved_id,page=request.args.get('page','1'))
        return render_template('letters/index.html',ui=UI,results=results,source=source,saved_id=saved_id,
                               operation_key=secrets.token_urlsafe(24))

    @bp.post('/cover-letters/new')
    @limiter.limit('30 per hour')
    def create():
        data=fields({'saved_id','source_hash','operation_key','language','length','tone','confirm'})
        row=service.create(g.current_user.id,data['saved_id'],data['source_hash'],data['operation_key'],
                           data['language'],data['length'],data['tone'],confirmed=data['confirm']=='1')
        return redirect(url_for('cover_letters.detail',letter_id=row['id']),code=303)

    @bp.get('/cover-letters/<uuid:letter_id>')
    @limiter.limit('60 per 5 minutes')
    def detail(letter_id):
        record=service.get(g.current_user.id,str(letter_id));proposal=None
        proposal_id=request.args.get('proposal')
        if proposal_id:
            proposal=next((p for p in record['proposals'] if p['id']==proposal_id),None)
            if proposal is None:raise LetterError('not_found')
        return render_editor(record,proposal)

    @bp.get('/api/cover-letters/<uuid:letter_id>')
    @limiter.limit('60 per 5 minutes')
    def read_api(letter_id):
        return jsonify(ok=True,letter=service.get(g.current_user.id,str(letter_id)))

    @bp.post('/cover-letters/<uuid:letter_id>/save')
    @limiter.limit('60 per hour')
    def save(letter_id):
        data=fields({'expected_revision','subject','body','language','length','tone','confirm'}, {'proposal_id'})
        try:
            service.save(g.current_user.id,str(letter_id),data['expected_revision'],data['subject'],data['body'],
                data['language'],data['length'],data['tone'],confirmed=data['confirm']=='1',proposal_id=data.get('proposal_id') or None)
        except LetterError as exc:
            if str(exc) in ('stale_write','stale_source') and not wants_json():
                record=service.get(g.current_user.id,str(letter_id))
                draft={'subject':data['subject'][:MAX_SUBJECT],'body':data['body'][:MAX_BODY]}
                return render_template('letters/conflict.html',ui=UI,record=record,draft=draft),409
            raise
        return redirect(url_for('cover_letters.detail',letter_id=letter_id),code=303)

    @bp.post('/cover-letters/<uuid:letter_id>/compose')
    @limiter.limit('30 per hour')
    def compose_local(letter_id):
        data=fields({'expected_revision','language','length','tone','operation_key'},repeated={'fact_id'})
        proposal=service.propose_local(g.current_user.id,str(letter_id),data['expected_revision'],
            data['language'],data['length'],data['tone'],data.getlist('fact_id'),data['operation_key'])
        return redirect(url_for('cover_letters.detail',letter_id=letter_id,proposal=proposal['id']),code=303)

    @bp.post('/cover-letters/<uuid:letter_id>/generate')
    @limiter.limit('10 per hour')
    def generate(letter_id):
        fields(set())
        return service.generate(g.current_user.id,str(letter_id))

    @bp.post('/cover-letters/<uuid:letter_id>/proposals/<uuid:proposal_id>/delete')
    @limiter.limit('30 per hour')
    def reject(letter_id,proposal_id):
        data=fields({'expected_revision','confirm'})
        service.reject(g.current_user.id,str(letter_id),str(proposal_id),data['expected_revision'],confirmed=data['confirm']=='1')
        return redirect(url_for('cover_letters.detail',letter_id=letter_id),code=303)

    @bp.get('/cover-letters/<uuid:letter_id>/versions/<int:number>')
    @limiter.limit('60 per 5 minutes')
    def version(letter_id,number):
        record=service.get(g.current_user.id,str(letter_id))
        item=service.version(g.current_user.id,str(letter_id),number)
        return render_template('letters/version.html',ui=UI,record=record,version=item)

    @bp.get('/cover-letters/<uuid:letter_id>/versions/<int:number>/export.txt')
    @limiter.limit('30 per hour')
    def export(letter_id,number):
        raw=service.export_text(g.current_user.id,str(letter_id),number)
        response=Response(raw,content_type='text/plain; charset=utf-8')
        response.headers['Content-Disposition']=f'attachment; filename="cover-letter-{letter_id}-v{number}.txt"'
        response.headers['X-Content-Type-Options']='nosniff'
        return response

    @bp.get('/cover-letters/<uuid:letter_id>/compare')
    @limiter.limit('30 per 5 minutes')
    def compare(letter_id):
        compared=service.compare(g.current_user.id,str(letter_id),request.args.get('left'),request.args.get('right'))
        return render_template('letters/compare.html',ui=UI,letter_id=str(letter_id),compared=compared)

    @bp.post('/cover-letters/<uuid:letter_id>/versions/<int:number>/delete')
    @limiter.limit('30 per hour')
    def delete_version(letter_id,number):
        data=fields({'expected_revision','confirm'})
        service.delete_version(g.current_user.id,str(letter_id),number,data['expected_revision'],confirmed=data['confirm']=='1')
        return redirect(url_for('cover_letters.detail',letter_id=letter_id),code=303)

    @bp.post('/cover-letters/<uuid:letter_id>/delete')
    @limiter.limit('30 per hour')
    def delete_letter(letter_id):
        data=fields({'expected_revision','confirm'})
        service.delete(g.current_user.id,str(letter_id),data['expected_revision'],confirmed=data['confirm']=='1')
        return redirect(url_for('cover_letters.index'),code=303)

    return bp
