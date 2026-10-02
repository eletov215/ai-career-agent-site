"""Private native-form routes for JOB-002 application tracking."""
from flask import Blueprint, abort, g, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError
from domain.application_tracker import STATES, TRANSITIONS, TrackerError
from domain.saved_vacancy import SavedVacancyError
from security import limiter

LABELS = {
    'saved': 'Сохранено', 'preparing': 'Готовлю отклик',
    'submitted_user_reported': 'Отклик отправлен (со слов пользователя)',
    'in_process_user_reported': 'Процесс продолжается (со слов пользователя)',
    'closed': 'Закрыто',
}


def create_application_trackers_blueprint(service, saved_service, reminder_service=None):
    bp = Blueprint('application_trackers', __name__)

    @bp.before_request
    def require_owner():
        user = getattr(g, 'current_user', None)
        if user is None:
            return redirect(url_for('auth.login', next=request.path))
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

    @bp.errorhandler(TrackerError)
    def tracker_error(error):
        code = str(error)
        status = 404 if code == 'not_found' else 409 if code == 'stale_write' else 400
        messages = {'stale_write': 'Статус уже изменён в другой вкладке. Обновите страницу.',
                    'invalid_transition': 'Этот переход статуса недоступен.',
                    'invalid_state': 'Неизвестный статус.', 'invalid_revision': 'Некорректная версия.'}
        return render_template('application_trackers/error.html', message=messages.get(code, 'Запрос отклонён.')), status

    @bp.errorhandler(SQLAlchemyError)
    @bp.errorhandler(OSError)
    def storage_error(_error):
        return render_template('application_trackers/error.html', message='Хранилище временно недоступно.'), 503

    @bp.get('/saved-vacancies/<uuid:saved_id>/tracker')
    @limiter.limit('60 per 5 minutes')
    def detail(saved_id):
        saved_id = str(saved_id)
        try:
            record = saved_service.get(g.current_user.id, saved_id)
        except SavedVacancyError:
            raise TrackerError('not_found') from None
        tracker = service.get(g.current_user.id, saved_id)
        reminder = reminder_service.for_saved(g.current_user.id, saved_id) if reminder_service else None
        targets = TRANSITIONS[tracker['state']]
        return render_template('application_trackers/detail.html', record=record, tracker=tracker,
                               states=STATES, labels=LABELS, targets=targets, reminder=reminder, reminder_feature=reminder_service is not None)

    @bp.post('/saved-vacancies/<uuid:saved_id>/tracker')
    @limiter.limit('60 per hour')
    def transition(saved_id):
        if request.is_json or request.files or set(request.form) != {'csrf_token','state','expected_revision'} or any(
                len(request.form.getlist(key)) != 1 for key in request.form):
            raise TrackerError('invalid_state')
        service.transition(g.current_user.id, str(saved_id), request.form['state'], request.form['expected_revision'])
        return redirect(url_for('application_trackers.detail', saved_id=saved_id), code=303)

    return bp
