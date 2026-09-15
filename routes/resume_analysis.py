"""Private reference-only review UI. No browser endpoint dispatches Alice."""
import secrets
from flask import Blueprint, abort, g, redirect, render_template, request, url_for
from security import limiter
from services.admin_access import is_search_admin
from domain.resume_analysis import AnalysisRequest, AnalysisError

LABELS = {
    'title': '\u0410\u043d\u0430\u043b\u0438\u0437 \u0440\u0435\u0437\u044e\u043c\u0435: \u043f\u0440\u043e\u0432\u0435\u0440\u043e\u0447\u043d\u044b\u0439 \u0440\u0435\u0436\u0438\u043c',
    'notice': '\u0422\u043e\u043b\u044c\u043a\u043e \u0441\u0438\u043d\u0442\u0435\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u043f\u0440\u0438\u043c\u0435\u0440\u044b. \u042d\u0442\u0430\u043b\u043e\u043d\u043d\u044b\u0439 \u043e\u0442\u0447\u0451\u0442 \u043d\u0435 \u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u043d\u043e\u0432\u044b\u043c \u043e\u0442\u0432\u0435\u0442\u043e\u043c Alice. \u0412\u044b\u0437\u043e\u0432\u044b API \u0438 \u043f\u0435\u0440\u0435\u0434\u0430\u0447\u0430 \u0440\u0435\u0430\u043b\u044c\u043d\u044b\u0445 \u0440\u0435\u0437\u044e\u043c\u0435 \u043d\u0435 \u0432\u044b\u043f\u043e\u043b\u043d\u044f\u044e\u0442\u0441\u044f.',
    'create': '\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u044d\u0442\u0430\u043b\u043e\u043d\u043d\u044b\u0439 \u043f\u0440\u0438\u043c\u0435\u0440',
    'history': '\u0418\u0441\u0442\u043e\u0440\u0438\u044f \u043e\u0442\u0447\u0451\u0442\u043e\u0432',
    'empty': '\u0421\u043e\u0445\u0440\u0430\u043d\u0451\u043d\u043d\u044b\u0445 \u043e\u0442\u0447\u0451\u0442\u043e\u0432 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442.',
    'source': '\u0418\u0441\u0445\u043e\u0434\u043d\u044b\u0435 \u0444\u0430\u043a\u0442\u044b',
    'strengths': '\u0421\u0438\u043b\u044c\u043d\u044b\u0435 \u0441\u0442\u043e\u0440\u043e\u043d\u044b',
    'gaps': '\u0427\u0442\u043e \u0441\u0442\u043e\u0438\u0442 \u0443\u0442\u043e\u0447\u043d\u0438\u0442\u044c',
    'recommendations': '\u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438',
    'unverified': '\u041d\u0435\u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0451\u043d\u043d\u044b\u0435 \u0441\u0432\u0435\u0434\u0435\u043d\u0438\u044f',
    'gap_note': '\u041e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0438\u0435 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u044f \u0432 \u043f\u0440\u0438\u043c\u0435\u0440\u0435 \u043d\u0435 \u043e\u0437\u043d\u0430\u0447\u0430\u0435\u0442, \u0447\u0442\u043e \u0447\u0435\u043b\u043e\u0432\u0435\u043a \u043d\u0435 \u043e\u0431\u043b\u0430\u0434\u0430\u0435\u0442 \u043d\u0430\u0432\u044b\u043a\u043e\u043c.',
    'review_note': '\u041f\u0440\u0438\u043d\u044f\u0442\u0438\u0435 \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438 \u043d\u0435 \u0438\u0437\u043c\u0435\u043d\u044f\u0435\u0442 \u043f\u0440\u043e\u0444\u0438\u043b\u044c \u0438 \u043d\u0435 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0430\u0435\u0442 \u043d\u043e\u0432\u044b\u0439 \u043e\u043f\u044b\u0442. \u0421\u0441\u044b\u043b\u043a\u0438 \u043d\u0430 \u0444\u0430\u043a\u0442\u044b \u043f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u044e\u0442 \u043e\u0441\u043d\u043e\u0432\u0430\u043d\u0438\u0435 \u0432\u044b\u0432\u043e\u0434\u0430, \u0430 \u043d\u0435 \u0432\u0435\u0440\u043e\u044f\u0442\u043d\u043e\u0441\u0442\u044c \u0435\u0433\u043e \u0438\u0441\u0442\u0438\u043d\u043d\u043e\u0441\u0442\u0438.',
    'accept': '\u041f\u0440\u0438\u043d\u044f\u0442\u044c', 'reject': '\u041e\u0442\u043a\u043b\u043e\u043d\u0438\u0442\u044c', 'reset': '\u0412\u0435\u0440\u043d\u0443\u0442\u044c \u043a \u043e\u0431\u0441\u0443\u0436\u0434\u0435\u043d\u0438\u044e',
    'pending': '\u041d\u0435 \u0440\u0430\u0441\u0441\u043c\u043e\u0442\u0440\u0435\u043d\u043e', 'accepted': '\u041f\u0440\u0438\u043d\u044f\u0442\u043e', 'rejected': '\u041e\u0442\u043a\u043b\u043e\u043d\u0435\u043d\u043e',
    'version': '\u0412\u0435\u0440\u0441\u0438\u044f', 'reference': '\u042d\u0442\u0430\u043b\u043e\u043d', 'provider': '\u041e\u0442\u0432\u0435\u0442 AI',
    'fact': '\u0424\u0430\u043a\u0442', 'back': '\u041a \u0438\u0441\u0442\u043e\u0440\u0438\u0438', 'review_history': '\u0418\u0441\u0442\u043e\u0440\u0438\u044f \u0440\u0435\u0448\u0435\u043d\u0438\u0439',
    'delete': '\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u044d\u0442\u043e\u0442 \u043e\u0442\u0447\u0451\u0442',
}

def create_resume_analysis_blueprint(service, settings):
    bp=Blueprint('resume_analysis',__name__,url_prefix='/ai-analysis')

    @bp.before_request
    def private_boundary():
        if not settings.ai_analysis_review_enabled or not is_search_admin(getattr(g,'current_user',None),settings):
            abort(404)

    @bp.after_request
    def no_store(response):
        response.headers['Cache-Control']='no-store, max-age=0';response.headers['Pragma']='no-cache'
        response.headers['Referrer-Policy']='strict-origin';response.headers.pop('ETag',None)
        return response

    def fields(allowed):
        if request.files or request.is_json or set(request.form)-set(allowed)-{'csrf_token'}:
            abort(400)
        if any(len(request.form.getlist(k))!=1 for k in request.form):abort(400)

    @bp.get('')
    @limiter.limit('60 per 5 minutes')
    def index():
        return render_template('analysis/index.html',ui=LABELS,choices=service.choices(),
                               reports=service.history(g.current_user.id),operation_key=secrets.token_urlsafe(24))

    @bp.post('/reference')
    @limiter.limit('20 per hour')
    def reference():
        fields({'fixture_id','source_hash','operation_key'})
        outcome=service.create_reference(AnalysisRequest(g.current_user.id,request.form.get('operation_key',''),
                                                       request.form.get('fixture_id',''),request.form.get('source_hash','')))
        if outcome.report is None:
            abort(409 if outcome.reason in {'stale_source','idempotency_conflict'} else 400)
        return redirect(url_for('resume_analysis.detail',report_id=outcome.report['id']),code=303)

    @bp.get('/<uuid:report_id>')
    @limiter.limit('60 per 5 minutes')
    def detail(report_id):
        report=service.get(g.current_user.id,str(report_id))
        if report is None:abort(404)
        return render_template('analysis/detail.html',ui=LABELS,report=report)

    @bp.post('/<uuid:report_id>/review')
    @limiter.limit('60 per hour')
    def review(report_id):
        fields({'recommendation_id','decision','expected_revision','source_hash'})
        try:
            revision=int(request.form.get('expected_revision','-1'))
            service.decide(user_id=g.current_user.id,report_id=str(report_id),recommendation_id=request.form.get('recommendation_id',''),
                           decision=request.form.get('decision',''),expected_revision=revision,expected_source_hash=request.form.get('source_hash',''))
        except AnalysisError as exc:
            abort(404 if str(exc)=='not_found' else 409 if str(exc) in {'stale_review','stale_source'} else 400)
        except ValueError:abort(400)
        return redirect(url_for('resume_analysis.detail',report_id=report_id),code=303)

    @bp.post('/<uuid:report_id>/delete')
    @limiter.limit('20 per hour')
    def delete_report(report_id):
        fields({'source_hash'})
        try:service.delete(g.current_user.id,str(report_id),request.form.get('source_hash',''))
        except AnalysisError as exc:abort(404 if str(exc)=='not_found' else 409)
        return redirect(url_for('resume_analysis.index'),code=303)

    return bp
