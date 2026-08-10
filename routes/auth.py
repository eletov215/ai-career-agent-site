"""AUTH-001 first-party account routes."""

from __future__ import annotations

import functools
import logging

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from config import AppSettings
from security import limiter
from services.auth import AuthService, AuthValidationError, safe_next_path

logger = logging.getLogger(__name__)

AUTH_SESSION_KEY = "auth_session_token"
_PROVIDER_SESSION_KEYS = ("superjob_user_id", "hh_user_id")
_DELIVERY_UNAVAILABLE = (
    "Регистрация и восстановление временно недоступны: сервис отправки писем ещё не настроен."
)


def _preserved_provider_identities() -> dict[str, object]:
    return {
        key: session.get(key)
        for key in _PROVIDER_SESSION_KEYS
        if session.get(key) is not None
    }


def _rotate_browser_session(raw_token: str) -> None:
    """Rotate Flask session state while retaining independent provider identities."""

    provider_identities = _preserved_provider_identities()
    session.clear()
    session[AUTH_SESSION_KEY] = raw_token
    for key, value in provider_identities.items():
        session[key] = value
    session.permanent = True


def _clear_first_party_session() -> None:
    session.pop(AUTH_SESSION_KEY, None)


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if getattr(g, "current_user", None) is None:
            next_path = request.full_path if request.query_string else request.path
            return redirect(url_for("auth.login", next=next_path))
        return view(*args, **kwargs)

    return wrapped


def create_auth_blueprint(auth_service: AuthService, settings: AppSettings) -> Blueprint:
    bp = Blueprint("auth", __name__, url_prefix="/auth")

    @bp.before_app_request
    def load_current_user() -> None:
        g.current_auth = None
        g.current_user = None
        raw_token = session.get(AUTH_SESSION_KEY)
        if not raw_token:
            return
        authenticated = auth_service.load_session(raw_token)
        if authenticated is None:
            _clear_first_party_session()
            return
        g.current_auth = authenticated
        g.current_user = authenticated.user

    @bp.after_request
    def protect_auth_responses(response):
        # Authentication pages may carry one-time tokens in the URL. Keep them
        # out of caches and strip path/query details from Referer while still
        # allowing Flask-WTF's production HTTPS same-origin CSRF check to see
        # the request origin on form POSTs. ``no-referrer`` breaks every
        # production auth POST when WTF_CSRF_SSL_STRICT is enabled.
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Referrer-Policy"] = "strict-origin"
        return response

    @bp.app_context_processor
    def auth_template_context():
        return {
            "current_user": getattr(g, "current_user", None),
            "current_auth_session": (
                getattr(g, "current_auth", None).session
                if getattr(g, "current_auth", None)
                else None
            ),
            "auth_email_delivery_available": auth_service.email_delivery_available,
        }

    @bp.route("/register", methods=["GET", "POST"])
    @limiter.limit("5 per hour", methods=["POST"])
    def register():
        if getattr(g, "current_user", None):
            return redirect(url_for("dashboard"))
        values = {
            "email": request.form.get("email", ""),
            "display_name": request.form.get("display_name", ""),
        }
        error = None
        status_code = 200
        if request.method == "POST":
            if not auth_service.email_delivery_available:
                error = _DELIVERY_UNAVAILABLE
                status_code = 503
            else:
                password = request.form.get("password", "")
                confirmation = request.form.get("password_confirm", "")
                if password != confirmation:
                    error = "Пароли не совпадают."
                    status_code = 400
                else:
                    try:
                        result = auth_service.register(
                            email=values["email"],
                            password=password,
                            display_name=values["display_name"],
                            verification_url_builder=lambda token: url_for(
                                "auth.verify_email",
                                token=token,
                                _external=True,
                            ),
                        )
                    except AuthValidationError as exc:
                        error = str(exc)
                        status_code = 400
                    else:
                        logger.info(
                            "First-party registration accepted",
                            extra={
                                "event": "auth_registration_accepted",
                                "result_code": result.code,
                            },
                        )
                        return render_template(
                            "auth/notice.html",
                            title="Проверьте почту",
                            message=result.message,
                            action_url=url_for("auth.login"),
                            action_label="Перейти ко входу",
                        )
        return (
            render_template(
                "auth/register.html",
                values=values,
                error=error,
                password_min_length=settings.auth_password_min_length,
                delivery_available=auth_service.email_delivery_available,
            ),
            status_code,
        )

    @bp.route("/resend-verification", methods=["GET", "POST"])
    @limiter.limit("5 per hour", methods=["POST"])
    def resend_verification():
        email = request.form.get("email", "")
        error = None
        status_code = 200
        if request.method == "POST":
            if not auth_service.email_delivery_available:
                error = _DELIVERY_UNAVAILABLE
                status_code = 503
            else:
                result = auth_service.resend_verification(
                    email=email,
                    verification_url_builder=lambda token: url_for(
                        "auth.verify_email",
                        token=token,
                        _external=True,
                    ),
                )
                return render_template(
                    "auth/notice.html",
                    title="Запрос принят",
                    message=result.message,
                    action_url=url_for("auth.login"),
                    action_label="Перейти ко входу",
                )
        return (
            render_template(
                "auth/simple_form.html",
                page_kind="resend",
                title="Повторная отправка письма",
                description="Введите email, указанный при регистрации.",
                submit_label="Отправить письмо",
                email=email,
                error=error,
                delivery_available=auth_service.email_delivery_available,
            ),
            status_code,
        )

    @bp.get("/verify")
    @limiter.limit("30 per hour")
    def verify_email():
        token = request.args.get("token", "")
        return render_template(
            "auth/verify.html",
            token=token,
            token_present=bool(token),
        )

    @bp.post("/verify")
    @limiter.limit("20 per hour")
    def verify_email_submit():
        result = auth_service.verify_email(request.form.get("token", ""))
        return render_template(
            "auth/notice.html",
            title="Email подтверждён" if result.ok else "Ссылка недействительна",
            message=result.message,
            action_url=(
                url_for("auth.login")
                if result.ok
                else url_for("auth.resend_verification")
            ),
            action_label=("Войти" if result.ok else "Запросить новое письмо"),
            success=result.ok,
        ), (200 if result.ok else 400)

    @bp.route("/login", methods=["GET", "POST"])
    @limiter.limit("10 per 10 minutes", methods=["POST"])
    def login():
        if getattr(g, "current_user", None):
            return redirect(url_for("dashboard"))
        next_path = safe_next_path(
            request.values.get("next"),
            fallback=url_for("dashboard"),
        )
        email = request.form.get("email", "")
        error = None
        status_code = 200
        if request.method == "POST":
            result = auth_service.login(
                email=email,
                password=request.form.get("password", ""),
                user_agent=request.headers.get("User-Agent"),
            )
            if result.ok and result.session_token:
                _rotate_browser_session(result.session_token)
                logger.info(
                    "First-party login succeeded",
                    extra={"event": "auth_login_succeeded"},
                )
                return redirect(next_path)
            error = result.message
            status_code = 401
            logger.info(
                "First-party login rejected",
                extra={
                    "event": "auth_login_rejected",
                    "result_code": result.code,
                },
            )
        return (
            render_template(
                "auth/login.html",
                email=email,
                error=error,
                next_path=next_path,
            ),
            status_code,
        )

    @bp.post("/logout")
    @limiter.limit("30 per 10 minutes")
    def logout():
        auth_service.logout(session.get(AUTH_SESSION_KEY))
        # AUTH-001 owns only the first-party identity. Existing HeadHunter and
        # SuperJob browser identities remain independent until AUTH-002 binds
        # their encrypted database connections to a User explicitly.
        _clear_first_party_session()
        return redirect(url_for("home"))

    @bp.route("/forgot-password", methods=["GET", "POST"])
    @limiter.limit("5 per hour", methods=["POST"])
    def forgot_password():
        email = request.form.get("email", "")
        error = None
        status_code = 200
        if request.method == "POST":
            if not auth_service.email_delivery_available:
                error = _DELIVERY_UNAVAILABLE
                status_code = 503
            else:
                result = auth_service.request_password_reset(
                    email=email,
                    reset_url_builder=lambda token: url_for(
                        "auth.reset_password",
                        token=token,
                        _external=True,
                    ),
                )
                return render_template(
                    "auth/notice.html",
                    title="Запрос принят",
                    message=result.message,
                    action_url=url_for("auth.login"),
                    action_label="Вернуться ко входу",
                )
        return (
            render_template(
                "auth/simple_form.html",
                page_kind="reset_request",
                title="Восстановление пароля",
                description=(
                    "Введите email аккаунта. Ответ будет одинаковым независимо от того, "
                    "существует ли адрес."
                ),
                submit_label="Отправить ссылку",
                email=email,
                error=error,
                delivery_available=auth_service.email_delivery_available,
            ),
            status_code,
        )

    @bp.route("/reset-password", methods=["GET", "POST"])
    @limiter.limit("10 per hour", methods=["POST"])
    def reset_password():
        token = request.values.get("token", "")
        error = None
        status_code = 200
        token_active = auth_service.reset_token_active(token) if token else False
        if request.method == "GET" and token and not token_active:
            error = "Ссылка недействительна или срок её действия истёк."
            status_code = 400
        if request.method == "POST":
            password = request.form.get("password", "")
            confirmation = request.form.get("password_confirm", "")
            if password != confirmation:
                error = "Пароли не совпадают."
                status_code = 400
            else:
                try:
                    result = auth_service.reset_password(
                        raw_token=token,
                        new_password=password,
                    )
                except AuthValidationError as exc:
                    error = str(exc)
                    status_code = 400
                else:
                    if result.ok:
                        auth_service.logout(session.get(AUTH_SESSION_KEY))
                        _clear_first_party_session()
                        return render_template(
                            "auth/notice.html",
                            title="Пароль обновлён",
                            message=result.message,
                            action_url=url_for("auth.login"),
                            action_label="Войти",
                        )
                    error = result.message
                    status_code = 400
        return (
            render_template(
                "auth/reset.html",
                token=token if token_active or request.method == "POST" else "",
                error=error,
                password_min_length=settings.auth_password_min_length,
            ),
            status_code,
        )

    @bp.post("/sessions/revoke-others")
    @limiter.limit("20 per hour")
    @login_required
    def revoke_other_sessions():
        current = g.current_auth
        count = auth_service.revoke_other_sessions(
            user_id=current.user.id,
            current_session_id=current.session.id,
        )
        flash(
            "Другие активные сессии завершены."
            if count
            else "Других активных сессий нет.",
            "success",
        )
        return redirect(url_for("dashboard"))

    @bp.post("/sessions/<session_id>/revoke")
    @limiter.limit("30 per hour")
    @login_required
    def revoke_session(session_id: str):
        current = g.current_auth
        revoked = auth_service.revoke_session(
            user_id=current.user.id,
            session_id=session_id,
            current_session_id=current.session.id,
        )
        flash(
            "Сессия завершена." if revoked else "Эту сессию нельзя завершить здесь.",
            "success" if revoked else "error",
        )
        return redirect(url_for("dashboard"))

    return bp
