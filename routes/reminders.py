"""Private native-form JOB-003 reminder routes."""
from flask import Blueprint, abort, g, redirect, render_template, request, url_for
from sqlalchemy.exc import SQLAlchemyError
from domain.reminders import ReminderError
from security import limiter


def create_reminders_blueprint(service):
    bp = Blueprint('reminders', __name__)

    @bp.before_request
    def require_owner():
        user = getattr(g, 'current_user', None)
        if user is None: return redirect(url_for('auth.login', next=request.path))
        if user.status != 'active' or user.email_verified_at is None: abort(404)

    @bp.after_request
    def private_headers(response):
        response.headers['Cache-Control'] = 'no-store, max-age=0'; response.headers['Pragma'] = 'no-cache'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow'; response.headers['Referrer-Policy'] = 'strict-origin'
        response.headers.pop('ETag', None); return response

    @bp.errorhandler(ReminderError)
    def reminder_error(error):
        code = str(error); status = 404 if code == 'not_found' else 409 if code == 'stale_write' else 400
        messages = {'stale_write': 'Напоминание уже изменено в другой вкладке. Обновите страницу.', 'preference_disabled': 'Сначала включите напоминания в настройках.', 'invalid_date': 'Укажите корректную календарную дату.', 'invalid_revision': 'Некорректная версия.', 'invalid_preference': 'Некорректная настройка.'}
        return render_template('reminders/error.html', message=messages.get(code, 'Запрос отклонён.')), status

    @bp.errorhandler(SQLAlchemyError)
    def storage_error(_error): return render_template('reminders/error.html', message='Хранилище временно недоступно.'), 503

    @bp.get('/reminders')
    @limiter.limit('60 per 5 minutes')
    def index():
        preference = service.preference(g.current_user.id)
        rows = service.list(g.current_user.id) if preference['in_app_reminders_enabled'] else []
        return render_template('reminders/index.html', preference=preference, reminders=rows)

    @bp.post('/reminders/preference')
    @limiter.limit('30 per hour')
    def preference():
        if request.is_json or request.files or set(request.form) != {'csrf_token', 'enabled', 'expected_revision'}: raise ReminderError('invalid_preference')
        service.set_preference(g.current_user.id, request.form['enabled'], request.form['expected_revision'])
        return redirect(url_for('reminders.index'), code=303)

    @bp.post('/saved-vacancies/<uuid:saved_id>/reminder')
    @limiter.limit('60 per hour')
    def save(saved_id):
        if request.is_json or request.files or set(request.form) != {'csrf_token', 'due_date', 'expected_revision'}: raise ReminderError('invalid_date')
        service.save(g.current_user.id, str(saved_id), request.form['due_date'], request.form['expected_revision'])
        return redirect(url_for('application_trackers.detail', saved_id=saved_id), code=303)

    @bp.post('/saved-vacancies/<uuid:saved_id>/reminder/delete')
    @limiter.limit('60 per hour')
    def delete(saved_id):
        if request.is_json or request.files or set(request.form) != {'csrf_token', 'expected_revision'}: raise ReminderError('invalid_revision')
        service.delete(g.current_user.id, str(saved_id), request.form['expected_revision'])
        return redirect(url_for('application_trackers.detail', saved_id=saved_id), code=303)
    return bp
