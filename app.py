import json
import secrets
import socket
import platform
import time
import logging
from pathlib import Path
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename


from services.base_provider import SearchResult
from services.hh_provider import HeadHunterProvider
from services.superjob_provider import SuperJobProvider
from services.reed_provider import ReedProvider
from services.search_filters import VacancySearchFilters
from services.search_aggregation import SearchAggregationService
from services.source_status import build_source_states, selectable_source_keys
from services.vacancy_presenter import present_vacancy
from services.resume_parser import ResumeParseError, build_resume_preview, parse_resume_pdf
from services.university_logo import find_university_logo
from config import AppSettings, load_settings
from database import CURRENT_REVISION, create_database, database_health
from services.storage import StorageServices
from services.auth import AuthService
from services.email_delivery import build_auth_email_sender
from routes.auth import AUTH_SESSION_KEY, create_auth_blueprint, login_required
from services.oauth_identity import OAuthIdentityError, OAuthIdentityService
from services.trudvsem_sync import TrudvsemSyncService
from security import csrf, diagnostics_access_allowed, init_security, limiter
from observability import (
    ALERT_DISPATCHER,
    OPS_STATE,
    build_test_alert_payload,
    configure_logging,
    current_request_id,
    init_observability,
    provider_operation,
)

SETTINGS: AppSettings = load_settings()
configure_logging(SETTINGS)

app = Flask(__name__)
app.config.from_mapping(SETTINGS.flask_mapping())
# Register request correlation before security handlers so CSRF/host/error logs
# receive the same request ID as the final HTTP access record.
init_observability(app, SETTINGS)
init_security(app, SETTINGS)

CLIENT_ID = SETTINGS.superjob_client_id
CLIENT_SECRET = SETTINGS.superjob_client_secret
REDIRECT_URI = SETTINGS.superjob_redirect_uri
HH_CLIENT_ID = SETTINGS.hh_client_id
HH_CLIENT_SECRET = SETTINGS.hh_client_secret
HH_REDIRECT_URI = SETTINGS.hh_redirect_uri
HH_USER_AGENT = SETTINGS.hh_user_agent
HH_APP_TOKEN = SETTINGS.hh_app_token
REED_API_KEY = SETTINGS.reed_api_key

HH_AUTHORIZE_URL = "https://hh.ru/oauth/authorize"
HH_TOKEN_URL = "https://api.hh.ru/token"
HH_ME_URL = "https://api.hh.ru/me"
HH_VACANCIES_URL = "https://api.hh.ru/vacancies"
FERNET = Fernet(SETTINGS.token_encryption_key.encode("ascii"))

AUTHORIZE_URL = "https://www.superjob.ru/authorize/"
TOKEN_URL = "https://api.superjob.ru/2.0/oauth2/access_token/"
REFRESH_URL = "https://api.superjob.ru/2.0/oauth2/refresh_token/"
CURRENT_USER_URL = "https://api.superjob.ru/2.0/user/current/"
USER_CVS_URL = "https://api.superjob.ru/2.0/user_cvs/"
VACANCIES_URL = "https://api.superjob.ru/2.0/vacancies/"

DATA_DIR = SETTINGS.data_dir
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE = create_database(SETTINGS.database_url)
VACANCY_CACHE_TTL = SETTINGS.vacancy_cache_ttl
VACANCY_PAGE_SIZE = SETTINGS.vacancy_page_size
TRUDVSEM_SYNC_ENABLED = SETTINGS.trudvsem_sync_enabled
logger = logging.getLogger(__name__)
DEBUG_HH = SETTINGS.debug_hh
HH_CURRENCY_SCAN_PAGES = SETTINGS.hh_currency_scan_pages
MAX_RESUME_UPLOAD_MB = SETTINGS.max_resume_upload_mb
MAX_RESUME_PAGES = SETTINGS.max_resume_pages
RENDER_REGION = SETTINGS.render_region
SYNC_SECRET = SETTINGS.sync_secret

OAUTH_STATE_TTL_SECONDS = 10 * 60


STORAGE = StorageServices.from_database(DATABASE)
AUTH_EMAIL_SENDER = build_auth_email_sender(SETTINGS)
AUTH_SERVICE = AuthService(STORAGE.auth, AUTH_EMAIL_SENDER, SETTINGS)
app.register_blueprint(create_auth_blueprint(AUTH_SERVICE, SETTINGS))
OAUTH_CONNECTIONS = STORAGE.oauth_connections
OAUTH_IDENTITIES = OAuthIdentityService(OAUTH_CONNECTIONS)
SYNC_RUNS = STORAGE.sync_runs
USERS = STORAGE.users
VACANCY_STORE = STORAGE.vacancies
SEARCH_AGGREGATION = SearchAggregationService(
    STORAGE.search_snapshots,
    page_size=SETTINGS.search_page_size,
    ttl_seconds=SETTINGS.search_snapshot_ttl_seconds,
    max_pages_per_source=SETTINGS.search_snapshot_max_pages_per_source,
    max_candidates=SETTINGS.search_snapshot_max_candidates,
    max_rounds_per_request=SETTINGS.search_snapshot_max_rounds_per_request,
    buffer_items=SETTINGS.search_snapshot_buffer_items,
    extension_lease_seconds=SETTINGS.search_snapshot_extension_lease_seconds,
)

logger.info(
    "Application runtime initialized",
    extra={
        "event": "application_runtime_initialized",
        "database_revision": CURRENT_REVISION,
    },
)


TRUDVSEM_SYNC = TrudvsemSyncService(
    settings=SETTINGS,
    database=DATABASE,
    vacancy_store=VACANCY_STORE,
    sync_runs=SYNC_RUNS,
    sync_checkpoints=STORAGE.sync_checkpoints,
    provider_operation_factory=provider_operation,
)


def trudvsem_sync_status():
    """Return durable queue state written by the external worker."""

    return TRUDVSEM_SYNC.status()


def request_trudvsem_sync(*, trigger: str = "web"):
    """Queue an idempotent job without running provider I/O in Gunicorn."""

    if not TRUDVSEM_SYNC_ENABLED:
        return None
    run = TRUDVSEM_SYNC.enqueue(trigger=trigger)
    logger.info(
        "Trudvsem sync queued",
        extra={
            "event": "trudvsem_sync_queued",
            "provider": "trudvsem",
            "operation": "enqueue",
            "sync_run_id": run.id,
            "sync_status": run.status,
            "trigger": trigger,
        },
    )
    return run


def _remember_oauth_state(
    prefix: str,
    *,
    user_id: str,
    auth_session_id: str,
) -> str:
    """Bind OAuth state to one authenticated first-party user/session."""

    state = secrets.token_urlsafe(32)
    session[f"{prefix}_oauth_state"] = state
    session[f"{prefix}_oauth_state_issued_at"] = int(time.time())
    session[f"{prefix}_oauth_user_id"] = str(user_id)
    session[f"{prefix}_oauth_auth_session_id"] = str(auth_session_id)
    return state


def _discard_oauth_state(prefix: str) -> None:
    session.pop(f"{prefix}_oauth_state", None)
    session.pop(f"{prefix}_oauth_state_issued_at", None)
    session.pop(f"{prefix}_oauth_user_id", None)
    session.pop(f"{prefix}_oauth_auth_session_id", None)


def _consume_oauth_state(
    prefix: str,
    received_state: str | None,
    *,
    user_id: str,
    auth_session_id: str,
) -> bool:
    expected_state = session.pop(f"{prefix}_oauth_state", None)
    issued_at = session.pop(f"{prefix}_oauth_state_issued_at", None)
    expected_user_id = session.pop(f"{prefix}_oauth_user_id", None)
    expected_auth_session_id = session.pop(
        f"{prefix}_oauth_auth_session_id",
        None,
    )
    if (
        not expected_state
        or not received_state
        or issued_at is None
        or not expected_user_id
        or not expected_auth_session_id
        or not secrets.compare_digest(str(expected_user_id), str(user_id))
        or not secrets.compare_digest(
            str(expected_auth_session_id),
            str(auth_session_id),
        )
    ):
        return False
    try:
        age = int(time.time()) - int(issued_at)
    except (TypeError, ValueError):
        return False
    if age < 0 or age > OAUTH_STATE_TTL_SECONDS:
        return False
    return secrets.compare_digest(str(expected_state), str(received_state))


def _rotate_after_oauth_callback() -> None:
    """Clear transient OAuth state while keeping the first-party session."""

    auth_session_token = session.get(AUTH_SESSION_KEY)
    session.clear()
    if auth_session_token:
        session[AUTH_SESSION_KEY] = auth_session_token
    session.permanent = True


def _oauth_callback_login_failure(prefix: str, provider_name: str):
    """Return a query-safe response when first-party auth was lost mid-flow.

    OAuth authorization codes and state values must not be copied into the
    generic login ``next`` parameter. A lost/changed first-party session means
    the user must start the provider connection again from the dashboard.
    """

    if getattr(g, "current_user", None) is not None and getattr(
        g, "current_auth", None
    ) is not None:
        return None
    _discard_oauth_state(prefix)
    return (
        render_template(
            "message.html",
            success=False,
            title="Сессия подключения завершена",
            message=(
                f"Войдите в AI Career Agent и начните подключение {provider_name} "
                "заново из личного кабинета."
            ),
            action_url=url_for("auth.login"),
            action_label="Перейти ко входу",
        ),
        401,
    )


def _public_trudvsem_status_payload() -> dict:
    state = trudvsem_sync_status()
    return {
        "source": "trudvsem",
        "available": True,
        "running": bool(state.get("running")),
        "queued": bool(state.get("queued")),
        "progress_percent": max(0, min(int(state.get("progress_percent") or 0), 100)),
        "cached_total": VACANCY_STORE.count(keyword="", sources=["trudvsem"]),
        "cache_age_seconds": VACANCY_STORE.source_age_seconds("trudvsem"),
    }

def _safe_upload_filename(filename: str) -> str:
    """Return a filesystem-safe display name without trusting client paths."""

    candidate = secure_filename(Path(filename or "").name)
    return candidate or "resume.pdf"


def _search_provider_with_metrics(source_key, provider, *, filters, page):
    """Run one direct provider search and record only bounded metadata."""

    with provider_operation(source_key, "vacancy_search") as observation:
        result = provider.search(filters=filters, page=page)
        observation.result_count = len(result.items)
        if result.error:
            observation.fail("ProviderSearchError")
        return result


def enc(value):
    return FERNET.encrypt(value.encode()).decode() if value else None


def dec(value):
    if not value:
        return None
    try:
        return FERNET.decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("Не удалось расшифровать OAuth-токен.") from exc


def headers(token=None):
    result = {"X-Api-App-Id": CLIENT_SECRET, "Accept": "application/json"}
    if token:
        result["Authorization"] = f"Bearer {token}"
    return result


def _current_user_id() -> str | None:
    current_user = getattr(g, "current_user", None)
    return current_user.id if current_user is not None else None


def account(user_id: str | None = None):
    owner_id = user_id or _current_user_id()
    if not owner_id:
        return None
    return OAUTH_IDENTITIES.get(user_id=owner_id, provider="superjob")


def save_account(profile, token_data, *, user_id: str):
    now = int(time.time())
    expires_in = token_data.get("expires_in")
    expires_at = now + int(expires_in) if expires_in else None
    return OAUTH_IDENTITIES.connect(
        user_id=user_id,
        provider="superjob",
        external_user_id=str(profile["id"]),
        display_name=profile.get("name") or "Пользователь SuperJob",
        email=profile.get("email"),
        access_token=enc(token_data["access_token"]),
        refresh_token=enc(token_data.get("refresh_token")),
        expires_at=expires_at,
        profile_json=json.dumps(profile, ensure_ascii=False),
        updated_at=now,
    )


def valid_token(row):
    if row.expires_at and int(row.expires_at) <= int(time.time()) + 120:
        refresh_token = dec(row.refresh_token)
        if not refresh_token:
            raise RuntimeError("Refresh token отсутствует. Подключите SuperJob заново.")
        try:
            response = requests.get(
                REFRESH_URL,
                params={
                    "refresh_token": refresh_token,
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                },
                headers={"X-Api-App-Id": CLIENT_SECRET},
                timeout=30,
            )
        except requests.RequestException as exc:
            logger.warning(
                "SuperJob token refresh request failed type=%s",
                type(exc).__name__,
            )
            raise RuntimeError(
                "Не удалось обновить подключение SuperJob. Подключите площадку заново."
            ) from None
        if not response.ok:
            logger.warning(
                "SuperJob token refresh failed status=%s",
                response.status_code,
            )
            raise RuntimeError(
                "Не удалось обновить подключение SuperJob. Подключите площадку заново."
            )
        try:
            token_data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                "SuperJob вернул некорректный ответ при обновлении подключения."
            ) from exc
        access_token = token_data.get("access_token")
        if not access_token:
            raise RuntimeError(
                "SuperJob не вернул новый токен. Подключите площадку заново."
            )
        token_data.setdefault("refresh_token", refresh_token)
        if not row.user_id:
            raise RuntimeError("Подключение SuperJob не привязано к пользователю.")
        save_account(
            json.loads(row.profile_json),
            token_data,
            user_id=row.user_id,
        )
        return access_token
    return dec(row.access_token)


def hh_account(user_id: str | None = None):
    owner_id = user_id or _current_user_id()
    if not owner_id:
        return None
    return OAUTH_IDENTITIES.get(user_id=owner_id, provider="headhunter")


def hh_headers(token=None):
    """Build headers required by HH API.

    HH requires the custom HH-User-Agent header. We also send the regular
    User-Agent for compatibility with proxies and HTTP tooling.
    """
    headers = {
        "Accept": "application/json",
        "HH-User-Agent": HH_USER_AGENT,
        "User-Agent": HH_USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers



def _masked_hh_headers(headers):
    """Return HH request headers safe for logs and debug responses."""
    safe = {}
    for key, value in dict(headers or {}).items():
        if key.lower() == "authorization":
            safe[key] = "Bearer ***" if value else "***"
        else:
            safe[key] = value
    return safe


def _hh_response_report(response):
    """Build a bounded diagnostic report without tokens or arbitrary bodies."""

    safe_response_headers = {}
    for name in ("Content-Type", "Server", "X-Request-Id", "Request-Id"):
        value = response.headers.get(name)
        if value:
            safe_response_headers[name] = value

    error_types = []
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        for item in payload.get("errors", []):
            if isinstance(item, dict) and item.get("type"):
                error_types.append(str(item["type"])[:80])

    return {
        "status_code": response.status_code,
        "ok": response.ok,
        "request_headers": _masked_hh_headers(response.request.headers),
        "response_headers": safe_response_headers,
        "error_types": error_types[:10],
    }


def save_hh_account(profile, token_data, *, user_id: str):
    now = int(time.time())
    expires_in = token_data.get("expires_in")
    expires_at = now + int(expires_in) if expires_in else None
    display_name = " ".join(
        part for part in (profile.get("first_name"), profile.get("last_name")) if part
    ) or None
    return OAUTH_IDENTITIES.connect(
        user_id=user_id,
        provider="headhunter",
        external_user_id=str(profile["id"]),
        display_name=display_name,
        first_name=profile.get("first_name"),
        last_name=profile.get("last_name"),
        email=profile.get("email"),
        access_token=enc(token_data["access_token"]),
        refresh_token=enc(token_data.get("refresh_token")),
        expires_at=expires_at,
        profile_json=json.dumps(profile, ensure_ascii=False),
        updated_at=now,
    )


def valid_hh_token(row):
    """Return a valid HH access token, refreshing it shortly before expiry."""
    expires_at = row.expires_at
    if not expires_at or int(expires_at) > int(time.time()) + 120:
        return dec(row.access_token)

    refresh_token = dec(row.refresh_token)
    if not refresh_token:
        raise RuntimeError("Refresh token HH отсутствует. Подключите HeadHunter заново.")

    try:
        response = requests.post(
            HH_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": HH_CLIENT_ID,
                "client_secret": HH_CLIENT_SECRET,
            },
            headers=hh_headers(),
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.warning(
            "HeadHunter token refresh request failed type=%s",
            type(exc).__name__,
        )
        raise RuntimeError(
            "Не удалось обновить подключение HeadHunter. Подключите площадку заново."
        ) from None
    if not response.ok:
        logger.warning("HeadHunter token refresh failed status=%s", response.status_code)
        raise RuntimeError(
            "Не удалось обновить подключение HeadHunter. Подключите площадку заново."
        )
    try:
        token_data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            "HeadHunter вернул некорректный ответ при обновлении подключения."
        ) from exc
    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError(
            "HeadHunter не вернул новый токен. Подключите площадку заново."
        )
    token_data.setdefault("refresh_token", refresh_token)

    if not row.user_id:
        raise RuntimeError("Подключение HeadHunter не привязано к пользователю.")
    profile = json.loads(row.profile_json)
    save_hh_account(profile, token_data, user_id=row.user_id)
    return access_token


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/privacy")
def privacy():
    return render_template("privacy.html")


@app.get("/oauth/superjob/login")
@limiter.limit("20 per 10 minutes")
@login_required
def superjob_login():
    state = _remember_oauth_state(
        "superjob",
        user_id=g.current_user.id,
        auth_session_id=g.current_auth.session.id,
    )
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }
    return redirect(f"{AUTHORIZE_URL}?{urlencode(params)}")


@app.get("/oauth/superjob/callback")
@limiter.limit("60 per 10 minutes")
def superjob_callback():
    login_failure = _oauth_callback_login_failure("superjob", "SuperJob")
    if login_failure is not None:
        return login_failure
    # State is one-time, TTL-bounded, and tied to the first-party user that
    # initiated the connection. Provider-controlled error fields are processed
    # only after this ownership check succeeds.
    received_state = request.args.get("state")
    if not _consume_oauth_state(
        "superjob",
        received_state,
        user_id=g.current_user.id,
        auth_session_id=g.current_auth.session.id,
    ):
        return render_template(
            "message.html",
            success=False,
            title="Ошибка безопасности",
            message="Начните подключение SuperJob заново из личного кабинета.",
        ), 400

    if request.args.get("error"):
        return render_template(
            "message.html",
            success=False,
            title="Авторизация отклонена",
            message="Подключение SuperJob было отменено. Попробуйте начать его заново.",
        ), 400

    code = request.args.get("code")
    if not code:
        return render_template(
            "message.html",
            success=False,
            title="Код не получен",
            message="SuperJob не передал код.",
        ), 400

    try:
        token_response = requests.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
            },
            headers={"X-Api-App-Id": CLIENT_SECRET},
            timeout=30,
        )
        token_response.raise_for_status()
        token_data = token_response.json()

        profile_response = requests.get(
            CURRENT_USER_URL,
            headers=headers(token_data["access_token"]),
            timeout=30,
        )
        profile_response.raise_for_status()
        profile = profile_response.json()

        result = save_account(
            profile,
            token_data,
            user_id=g.current_user.id,
        )
    except OAuthIdentityError as exc:
        logger.warning(
            "SuperJob OAuth ownership conflict",
            extra={
                "event": "oauth_connection_conflict",
                "provider": "superjob",
                "conflict_code": exc.code,
            },
        )
        return render_template(
            "message.html",
            success=False,
            title="Подключение не изменено",
            message=exc.public_message,
            action_url=url_for("dashboard", _anchor="connections"),
            action_label="Вернуться в кабинет",
        ), 409
    except (requests.RequestException, ValueError, KeyError):
        logger.exception("SuperJob OAuth callback failed")
        return render_template(
            "message.html",
            success=False,
            title="Ошибка подключения",
            message="Не удалось завершить подключение SuperJob. Повторите попытку позже.",
        ), 502

    _rotate_after_oauth_callback()
    flash(
        "SuperJob подключён к вашему аккаунту."
        if result.outcome in {"created", "claimed"}
        else "Доступ SuperJob обновлён.",
        "success",
    )
    logger.info(
        "SuperJob OAuth connection stored",
        extra={
            "event": "oauth_connection_bound",
            "provider": "superjob",
            "binding_outcome": result.outcome,
        },
    )
    return redirect(url_for("dashboard", _anchor="connections"))


@app.post("/oauth/superjob/disconnect")
@limiter.limit("20 per hour")
@login_required
def superjob_disconnect():
    removed = OAUTH_IDENTITIES.disconnect(
        user_id=g.current_user.id,
        provider="superjob",
    )
    _discard_oauth_state("superjob")
    flash(
        "SuperJob отключён, сохранённые OAuth-токены и профиль площадки удалены."
        if removed
        else "Подключение SuperJob уже отсутствует.",
        "success",
    )
    logger.info(
        "SuperJob OAuth connection disconnected",
        extra={
            "event": "oauth_connection_disconnected",
            "provider": "superjob",
            "connection_existed": bool(removed),
        },
    )
    return redirect(url_for("dashboard", _anchor="connections"))


@app.get("/oauth/hh/login")
@limiter.limit("20 per 10 minutes")
@login_required
def hh_login():
    state = _remember_oauth_state(
        "hh",
        user_id=g.current_user.id,
        auth_session_id=g.current_auth.session.id,
    )
    params = {
        "response_type": "code",
        "client_id": HH_CLIENT_ID,
        "redirect_uri": HH_REDIRECT_URI,
        "state": state,
    }
    return redirect(f"{HH_AUTHORIZE_URL}?{urlencode(params)}")


@app.get("/oauth/hh/callback")
@limiter.limit("60 per 10 minutes")
def hh_callback():
    login_failure = _oauth_callback_login_failure("hh", "HeadHunter")
    if login_failure is not None:
        return login_failure
    received_state = request.args.get("state")
    if not _consume_oauth_state(
        "hh",
        received_state,
        user_id=g.current_user.id,
        auth_session_id=g.current_auth.session.id,
    ):
        return render_template(
            "message.html",
            success=False,
            title="Ошибка безопасности",
            message="Начните подключение HeadHunter заново из личного кабинета.",
        ), 400

    if request.args.get("error"):
        return render_template(
            "message.html",
            success=False,
            title="Авторизация HH отклонена",
            message="Подключение HeadHunter было отменено. Попробуйте начать его заново.",
        ), 400

    code = request.args.get("code")
    if not code:
        return render_template(
            "message.html",
            success=False,
            title="Код не получен",
            message="HeadHunter не передал код авторизации.",
        ), 400

    try:
        token_response = requests.post(
            HH_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": HH_CLIENT_ID,
                "client_secret": HH_CLIENT_SECRET,
                "code": code,
                "redirect_uri": HH_REDIRECT_URI,
            },
            headers={
                "Accept": "application/json",
                "User-Agent": HH_USER_AGENT,
            },
            timeout=30,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data["access_token"]

        profile_response = requests.get(
            HH_ME_URL,
            headers=hh_headers(access_token),
            timeout=30,
        )
        profile_response.raise_for_status()
        profile = profile_response.json()

        result = save_hh_account(
            profile,
            token_data,
            user_id=g.current_user.id,
        )
    except OAuthIdentityError as exc:
        logger.warning(
            "HeadHunter OAuth ownership conflict",
            extra={
                "event": "oauth_connection_conflict",
                "provider": "headhunter",
                "conflict_code": exc.code,
            },
        )
        return render_template(
            "message.html",
            success=False,
            title="Подключение не изменено",
            message=exc.public_message,
            action_url=url_for("dashboard", _anchor="connections"),
            action_label="Вернуться в кабинет",
        ), 409
    except requests.RequestException:
        logger.exception("HeadHunter OAuth callback request failed")
        return render_template(
            "message.html",
            success=False,
            title="Ошибка подключения HH",
            message="Не удалось завершить подключение HeadHunter. Повторите попытку позже.",
        ), 502
    except (ValueError, KeyError):
        logger.exception("HeadHunter OAuth callback returned an invalid payload")
        return render_template(
            "message.html",
            success=False,
            title="Некорректный ответ HH",
            message="HeadHunter вернул неожиданный ответ. Повторите подключение позже.",
        ), 502

    _rotate_after_oauth_callback()
    flash(
        "HeadHunter подключён к вашему аккаунту."
        if result.outcome in {"created", "claimed"}
        else "Доступ HeadHunter обновлён.",
        "success",
    )
    logger.info(
        "HeadHunter OAuth connection stored",
        extra={
            "event": "oauth_connection_bound",
            "provider": "headhunter",
            "binding_outcome": result.outcome,
        },
    )
    return redirect(url_for("dashboard", _anchor="connections"))


@app.post("/oauth/hh/disconnect")
@limiter.limit("20 per hour")
@login_required
def hh_disconnect():
    removed = OAUTH_IDENTITIES.disconnect(
        user_id=g.current_user.id,
        provider="headhunter",
    )
    _discard_oauth_state("hh")
    flash(
        "HeadHunter отключён, сохранённые OAuth-токены и профиль площадки удалены."
        if removed
        else "Подключение HeadHunter уже отсутствует.",
        "success",
    )
    logger.info(
        "HeadHunter OAuth connection disconnected",
        extra={
            "event": "oauth_connection_disconnected",
            "provider": "headhunter",
            "connection_existed": bool(removed),
        },
    )
    return redirect(url_for("dashboard", _anchor="connections"))


@app.post("/logout")
@limiter.limit("20 per 10 minutes")
def logout():
    # Backward-compatible endpoint for pre-AUTH-001 forms. The canonical
    # first-party logout lives at /auth/logout and both revoke server state.
    AUTH_SERVICE.logout(session.get(AUTH_SESSION_KEY))
    session.clear()
    return redirect(url_for("home"))


@app.get("/dashboard")
@limiter.limit("120 per 5 minutes")
@login_required
def dashboard():
    first_party_user = g.current_user
    current_auth = g.current_auth
    superjob_row = account(first_party_user.id)
    hh_row = hh_account(first_party_user.id)

    auth_sessions = []
    for auth_session in AUTH_SERVICE.list_sessions(first_party_user.id):
        auth_sessions.append(
            {
                "id": auth_session.id,
                "is_current": auth_session.id == current_auth.session.id,
                "created_at": time.strftime("%d.%m.%Y %H:%M UTC", time.gmtime(auth_session.created_at)),
                "last_seen_at": time.strftime("%d.%m.%Y %H:%M UTC", time.gmtime(auth_session.last_seen_at)),
                "expires_at": time.strftime("%d.%m.%Y %H:%M UTC", time.gmtime(auth_session.expires_at)),
            }
        )

    resumes = []
    error = None

    if superjob_row:
        try:
            response = requests.get(
                USER_CVS_URL,
                headers=headers(valid_token(superjob_row)),
                timeout=8,
            )
            response.raise_for_status()
            resumes = response.json().get("objects", [])
        except (requests.RequestException, ValueError, RuntimeError) as exc:
            logger.warning("SuperJob resume list unavailable: %s", type(exc).__name__)
            error = "Не удалось загрузить данные SuperJob. Попробуйте обновить страницу позже."

    return render_template(
        "dashboard.html",
        account=superjob_row,
        hh_account=hh_row,
        first_party_user=first_party_user,
        auth_sessions=auth_sessions,
        resumes=resumes,
        error=error,
    )


@app.post("/api/resume/preview")
@limiter.limit("10 per 10 minutes")
def resume_preview_api():
    uploaded = request.files.get("resume")
    if not uploaded or not uploaded.filename:
        return jsonify({"ok": False, "error": "Выберите PDF-файл с резюме."}), 400

    safe_name = _safe_upload_filename(uploaded.filename)
    if not safe_name.lower().endswith(".pdf"):
        return jsonify({"ok": False, "error": "Поддерживаются только файлы PDF."}), 400

    max_bytes = MAX_RESUME_UPLOAD_MB * 1024 * 1024
    file_bytes = uploaded.stream.read(max_bytes + 1)
    if len(file_bytes) > max_bytes:
        return jsonify({"ok": False, "error": f"Размер PDF не должен превышать {MAX_RESUME_UPLOAD_MB} МБ."}), 413

    try:
        parsed = parse_resume_pdf(
            file_bytes,
            safe_name,
            max_pages=MAX_RESUME_PAGES,
            max_text_characters=SETTINGS.max_resume_text_characters,
        )
    except ResumeParseError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify({"ok": True, "profile": build_resume_preview(parsed)})


@app.route("/ai-career", methods=["GET", "POST"])
@limiter.limit("6 per 10 minutes", methods=["POST"])
def ai_career():
    parsed_resume = None
    upload_error = None

    if request.method == "POST":
        uploaded = request.files.get("resume")
        if not uploaded or not uploaded.filename:
            upload_error = "Выберите PDF-файл с резюме."
        else:
            safe_name = _safe_upload_filename(uploaded.filename)
            if not safe_name.lower().endswith(".pdf"):
                upload_error = "Поддерживаются только файлы PDF."
            else:
                max_bytes = MAX_RESUME_UPLOAD_MB * 1024 * 1024
                file_bytes = uploaded.stream.read(max_bytes + 1)
                if len(file_bytes) > max_bytes:
                    upload_error = f"Размер PDF не должен превышать {MAX_RESUME_UPLOAD_MB} МБ."
                else:
                    try:
                        parsed_resume = parse_resume_pdf(
                            file_bytes,
                            safe_name,
                            max_pages=MAX_RESUME_PAGES,
                            max_text_characters=SETTINGS.max_resume_text_characters,
                        )
                    except ResumeParseError as exc:
                        upload_error = str(exc)

    return render_template(
        "ai_career.html",
        parsed_resume=parsed_resume,
        upload_error=upload_error,
        max_resume_upload_mb=MAX_RESUME_UPLOAD_MB,
    )


@app.post("/api/university/logo")
@limiter.limit("20 per 10 minutes")
def university_logo_api():
    payload = request.get_json(silent=True) or {}
    university_name = str(payload.get("name") or "").strip()
    if len(university_name) < 3:
        return jsonify({"ok": False, "error": "Укажите название учебного заведения."}), 400
    try:
        with provider_operation("university_logo", "lookup") as observation:
            result = find_university_logo(university_name)
            observation.result_count = 1 if result else 0
    except requests.RequestException:
        logger.exception("University logo lookup request failed")
        return jsonify({"ok": False, "error": "Сервис поиска эмблемы временно недоступен."}), 502
    except ValueError as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    except Exception:
        logger.exception("University logo lookup failed")
        return jsonify({"ok": False, "error": "Не удалось найти эмблему университета."}), 500
    return jsonify({"ok": True, **result})


@app.get("/resume-builder")
def resume_builder():
    return render_template("resume_builder.html")


@app.get("/vacancies")
@limiter.limit("60 per 5 minutes")
def vacancies():
    filters = VacancySearchFilters.from_query(request.args)
    keyword = filters.keyword
    remote_only = filters.remote_only
    search_requested = request.args.get("search") == "1"
    sync_queued = request.args.get("sync") == "queued"
    try:
        requested_page = max(int(request.args.get("page", "0") or 0), 0)
    except ValueError:
        requested_page = 0

    requested_snapshot_id = str(request.args.get("snapshot") or "").strip() or None
    allowed_source_order = ("trudvsem", "superjob", "reed", "hh")
    allowed_sources = set(allowed_source_order)
    requested_source_values = list(
        dict.fromkeys(
            source
            for source in request.args.getlist("source")
            if source in allowed_sources
        )
    )

    configured_sources = {
        "superjob": bool(CLIENT_SECRET),
        "reed": bool(REED_API_KEY),
        "hh": bool(HH_APP_TOKEN),
    }
    trudvsem_cache_age = VACANCY_STORE.source_age_seconds("trudvsem")
    trudvsem_cache_total = VACANCY_STORE.count(
        keyword="",
        sources=["trudvsem"],
    )
    trudvsem_runtime_state = trudvsem_sync_status()
    trudvsem_latest_run = trudvsem_runtime_state.get("latest_run")
    trudvsem_last_run_failed = bool(
        trudvsem_latest_run
        and getattr(trudvsem_latest_run, "status", None) == "failed"
    )
    initial_source_states = build_source_states(
        configured_sources=configured_sources,
        selected_sources=requested_source_values,
        trudvsem_cache_total=trudvsem_cache_total,
        trudvsem_cache_age_seconds=trudvsem_cache_age,
        trudvsem_cache_ttl_seconds=VACANCY_CACHE_TTL,
        trudvsem_sync_enabled=TRUDVSEM_SYNC_ENABLED,
        trudvsem_sync_running=bool(trudvsem_runtime_state.get("running")),
        trudvsem_sync_queued=bool(
            trudvsem_runtime_state.get("queued") or sync_queued
        ),
        trudvsem_last_run_failed=trudvsem_last_run_failed,
    )
    selectable_sources = selectable_source_keys(initial_source_states)
    if requested_source_values:
        selected_sources = [
            source for source in requested_source_values if source in selectable_sources
        ]
    else:
        preferred_default = next(
            (source for source in allowed_source_order if source in selectable_sources),
            None,
        )
        selected_sources = [preferred_default] if preferred_default else []

    excluded_sources = [
        source
        for source in requested_source_values
        if source not in selectable_sources
    ]
    source_selection_notice = None
    if excluded_sources:
        excluded_titles = [
            next(
                state.title
                for state in initial_source_states
                if state.key == source
            )
            for source in excluded_sources
        ]
        source_selection_notice = (
            "Недоступные сейчас источники не включены в поиск: "
            + ", ".join(excluded_titles)
            + "."
        )

    providers = {
        "hh": HeadHunterProvider(
            HH_VACANCIES_URL,
            hh_headers,
            (lambda: HH_APP_TOKEN) if HH_APP_TOKEN else None,
            debug=DEBUG_HH,
            currency_scan_pages=HH_CURRENCY_SCAN_PAGES,
        )
    }
    if REED_API_KEY:
        providers["reed"] = ReedProvider(REED_API_KEY)
    # Vacancy listings from SuperJob do not require user OAuth. The app-level
    # X-Api-App-Id credential is enough for search; OAuth remains available for
    # user-specific SuperJob features in the dashboard.
    if CLIENT_SECRET:
        providers["superjob"] = SuperJobProvider(
            VACANCIES_URL,
            headers,
        )

    all_items = []
    source_results = {}
    errors = []
    cache_note = None
    page = requested_page
    has_next = False
    provider_reported_total = 0
    known_unique_total = 0
    total_is_exact = False
    snapshot_bounded = False
    snapshot_id = None
    snapshot_restarted = False
    page_size = SETTINGS.search_page_size
    deduplication_stats = {
        "input_count": 0,
        "output_count": 0,
        "duplicate_count": 0,
        "identity_duplicate_count": 0,
        "cross_source_duplicate_count": 0,
        "cross_source_groups": 0,
        "exact_groups": 0,
        "similarity_groups": 0,
    }

    if search_requested and selected_sources:
        if "trudvsem" in selected_sources:
            if trudvsem_runtime_state.get("running"):
                cache_note = "Данные «Работы России» обновляются в фоне. Поиск продолжает работать по сохранённому кэшу."
            elif trudvsem_runtime_state.get("queued") or sync_queued:
                cache_note = "Фоновое обновление «Работы России» поставлено в очередь."
            elif trudvsem_cache_age is None:
                queued_run = request_trudvsem_sync(trigger="cache-miss")
                if queued_run is not None:
                    trudvsem_runtime_state["queued"] = True
                    cache_note = "Кэш пока пуст. Загрузка поставлена в очередь; обновите страницу немного позже."
                else:
                    cache_note = "Кэш пока пуст, а внешняя синхронизация сейчас отключена."
            else:
                cache_note = (
                    "Работа России используется из сохранённого кэша "
                    f"({trudvsem_cache_age // 60} мин. назад)."
                )
                if trudvsem_last_run_failed:
                    cache_note += " Последнее обновление не завершилось, сохранённые вакансии доступны."

        def fetch_source_page(source_key: str, source_page: int) -> SearchResult:
            if source_key == "trudvsem":
                offset = source_page * VACANCY_PAGE_SIZE
                cached_items = VACANCY_STORE.search(
                    keyword=keyword,
                    sources=["trudvsem"],
                    remote_only=filters.remote_only,
                    salary_from=filters.salary_from,
                    salary_only=filters.salary_only,
                    period_days=filters.period_days,
                    sort=filters.sort,
                    region=filters.region,
                    experience=filters.experience,
                    employment=filters.employment,
                    work_format=filters.work_format,
                    currency=filters.currency,
                    limit=VACANCY_PAGE_SIZE,
                    offset=offset,
                )
                cached_total = VACANCY_STORE.count(
                    keyword=keyword,
                    sources=["trudvsem"],
                    remote_only=filters.remote_only,
                    salary_from=filters.salary_from,
                    salary_only=filters.salary_only,
                    period_days=filters.period_days,
                    region=filters.region,
                    experience=filters.experience,
                    employment=filters.employment,
                    work_format=filters.work_format,
                    currency=filters.currency,
                )
                return SearchResult(
                    items=cached_items,
                    total=cached_total,
                    page=source_page,
                    pages=(cached_total + VACANCY_PAGE_SIZE - 1) // VACANCY_PAGE_SIZE
                    if cached_total
                    else 0,
                    has_next=offset + len(cached_items) < cached_total,
                )

            provider = providers.get(source_key)
            if provider is None:
                if source_key == "superjob":
                    message = "SuperJob временно недоступен."
                elif source_key == "reed":
                    message = "Reed.co.uk временно недоступен."
                elif source_key == "hh":
                    message = "HeadHunter временно недоступен."
                else:
                    message = f"{source_key}: unavailable"
                return SearchResult(page=source_page, error=message)
            return _search_provider_with_metrics(
                source_key,
                provider,
                filters=filters,
                page=source_page,
            )

        aggregation = SEARCH_AGGREGATION.search(
            filters=filters,
            selected_sources=selected_sources,
            page=requested_page,
            snapshot_id=requested_snapshot_id,
            fetch_source=fetch_source_page,
        )
        page = aggregation.page
        page_size = aggregation.page_size
        has_next = aggregation.has_next
        source_results = aggregation.source_results
        errors = aggregation.errors
        provider_reported_total = aggregation.provider_reported_total
        known_unique_total = aggregation.known_unique_total
        total_is_exact = aggregation.total_is_exact
        snapshot_bounded = aggregation.bounded
        snapshot_id = aggregation.snapshot_id
        snapshot_restarted = aggregation.snapshot_restarted
        deduplication_stats = aggregation.deduplication_stats
        all_items = [present_vacancy(item) for item in aggregation.items]

        candidate_counts_by_source = {
            key: summary.fetched_items
            for key, summary in source_results.items()
        }
        OPS_STATE.record_search_dedup(
            page=page,
            selected_sources=selected_sources,
            candidate_counts_by_source=candidate_counts_by_source,
            stats=deduplication_stats,
        )
        OPS_STATE.record_search_pagination(
            snapshot_id=snapshot_id or "",
            page=page,
            page_size=page_size,
            source_results=source_results,
            known_unique_total=known_unique_total,
            provider_reported_total=provider_reported_total,
            total_is_exact=total_is_exact,
            bounded=snapshot_bounded,
            has_next=has_next,
            committed_count=aggregation.committed_count,
            late_arrival_count=aggregation.late_arrival_count,
            snapshot_age_seconds=aggregation.snapshot_age_seconds,
        )
        logger.info(
            "Stable search snapshot page served snapshot_prefix=%s page=%s page_size=%s "
            "known_unique=%s provider_total=%s exact=%s bounded=%s has_next=%s "
            "committed=%s late_arrivals=%s",
            (snapshot_id or "")[:12],
            page,
            page_size,
            known_unique_total,
            provider_reported_total,
            total_is_exact,
            snapshot_bounded,
            has_next,
            aggregation.committed_count,
            aggregation.late_arrival_count,
        )
    elif search_requested:
        source_selection_notice = (
            source_selection_notice
            or "Сейчас нет доступных источников для выбранного поиска."
        )

    source_options = build_source_states(
        configured_sources=configured_sources,
        selected_sources=selected_sources,
        source_results=source_results,
        trudvsem_cache_total=trudvsem_cache_total,
        trudvsem_cache_age_seconds=trudvsem_cache_age,
        trudvsem_cache_ttl_seconds=VACANCY_CACHE_TTL,
        trudvsem_sync_enabled=TRUDVSEM_SYNC_ENABLED,
        trudvsem_sync_running=bool(trudvsem_runtime_state.get("running")),
        trudvsem_sync_queued=bool(
            trudvsem_runtime_state.get("queued") or sync_queued
        ),
        trudvsem_last_run_failed=trudvsem_last_run_failed,
    )
    selected_source_states = [
        source for source in source_options if source.key in selected_sources
    ]

    filter_pairs = filters.query_pairs()
    for source in selected_sources:
        filter_pairs.append(("source", source))
    filter_query = urlencode(filter_pairs)
    pagination_pairs = list(filter_pairs)
    if snapshot_id:
        pagination_pairs.append(("snapshot", snapshot_id))
    pagination_query = urlencode(pagination_pairs)

    page_start = page * page_size + 1 if all_items else 0
    page_end = page * page_size + len(all_items)

    return render_template(
        "vacancies_unified.html",
        vacancies=all_items,
        keyword=keyword,
        remote_only=remote_only,
        filters=filters,
        selected_sources=selected_sources,
        source_options=source_options,
        selected_source_states=selected_source_states,
        source_results=source_results,
        source_selection_notice=source_selection_notice,
        page=page,
        page_size=page_size,
        page_start=page_start,
        page_end=page_end,
        has_next=has_next,
        total=provider_reported_total,
        provider_reported_total=provider_reported_total,
        known_unique_total=known_unique_total,
        total_is_exact=total_is_exact,
        snapshot_bounded=snapshot_bounded,
        snapshot_id=snapshot_id,
        snapshot_restarted=snapshot_restarted,
        errors=errors,
        search_requested=search_requested,
        cache_note=cache_note,
        filter_query=filter_query,
        pagination_query=pagination_query,
        show_manual_refresh=not SETTINGS.is_production,
        deduplication_stats=deduplication_stats,
    )


@app.get("/vacancies/internal")
@limiter.limit("120 per 5 minutes")
def vacancies_internal_redirect():
    """Keep historical links working while making /vacancies canonical."""

    target = url_for("vacancies")
    if request.query_string:
        target = f"{target}?{request.query_string.decode('latin-1')}"
    response = redirect(target, code=308)
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["X-Robots-Tag"] = "noindex"
    return response


@app.get("/debug/trudvsem")
@limiter.limit("20 per 5 minutes")
def debug_trudvsem():
    """Diagnose Render -> Работа России connectivity without exposing secrets."""
    if not diagnostics_access_allowed(SETTINGS):
        return {"ok": False, "error": "not found"}, 404
    host = "opendata.trudvsem.ru"
    api_url = f"https://{host}/api/v1/vacancies"
    report = {
        "service": "Работа России",
        "api_url": api_url,
        "render_region": RENDER_REGION,
        "timestamp_unix": int(time.time()),
    }

    dns_started = time.monotonic()
    try:
        address_rows = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        report["dns"] = {
            "ok": True,
            "seconds": round(time.monotonic() - dns_started, 3),
            "addresses": sorted({row[4][0] for row in address_rows}),
        }
    except OSError as exc:
        report["dns"] = {
            "ok": False,
            "seconds": round(time.monotonic() - dns_started, 3),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    request_started = time.monotonic()
    try:
        response = requests.get(
            api_url,
            params={"limit": 1, "offset": 0},
            headers={
                "User-Agent": HH_USER_AGENT,
                "Accept": "application/json",
                "Connection": "close",
            },
            timeout=(4, 8),
        )
        elapsed = round(time.monotonic() - request_started, 3)
        content_type = response.headers.get("Content-Type", "")
        preview = response.text[:1000]
        report["https_request"] = {
            "ok": response.ok,
            "seconds": elapsed,
            "status_code": response.status_code,
            "content_type": content_type,
            "response_bytes": len(response.content),
            "body_preview": preview,
        }
    except requests.RequestException as exc:
        report["https_request"] = {
            "ok": False,
            "seconds": round(time.monotonic() - request_started, 3),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    ip_started = time.monotonic()
    try:
        ip_response = requests.get("https://api.ipify.org", timeout=(3, 5))
        ip_response.raise_for_status()
        report["outbound_ip"] = {
            "ok": True,
            "seconds": round(time.monotonic() - ip_started, 3),
            "ip": ip_response.text.strip(),
        }
    except requests.RequestException as exc:
        report["outbound_ip"] = {
            "ok": False,
            "seconds": round(time.monotonic() - ip_started, 3),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }

    overall_ok = bool(report.get("dns", {}).get("ok") and report.get("https_request", {}).get("ok"))
    report["overall_ok"] = overall_ok
    return report, 200


@app.post("/trudvsem/refresh")
@csrf.exempt
@limiter.limit("3 per 10 minutes")
def refresh_trudvsem_cache():
    """Queue a development refresh without exposing a production control."""
    if SETTINGS.is_production:
        return {"ok": False, "error": "not found"}, 404
    # The route is globally exempt so production can return a neutral 404
    # before CSRF validation. Development/test still require a valid token.
    csrf.protect()
    request_trudvsem_sync(trigger="development-refresh")
    filters = VacancySearchFilters.from_query(request.form)
    sources = request.form.getlist("source") or ["trudvsem"]
    params = filters.query_pairs()
    params.append(("sync", "queued"))
    params.extend(("source", source) for source in sources)
    return redirect(url_for("vacancies") + "?" + urlencode(params))


@app.get("/api/sources/trudvsem/status")
@limiter.limit("120 per 5 minutes")
def trudvsem_public_status():
    """Return only fields needed by the public vacancy interface."""

    return _public_trudvsem_status_payload(), 200


@app.get("/trudvsem/status")
@limiter.limit("60 per 5 minutes")
def trudvsem_status():
    if not diagnostics_access_allowed(SETTINGS):
        return {"ok": False, "error": "not found"}, 404
    state = trudvsem_sync_status()
    state["cache_age_seconds"] = VACANCY_STORE.source_age_seconds("trudvsem")
    state["cached_total"] = VACANCY_STORE.count(keyword="", sources=["trudvsem"])
    state["sync_enabled"] = TRUDVSEM_SYNC_ENABLED
    state["worker_mode"] = "external_process"
    stale_after = int(time.time()) - max(
        SETTINGS.trudvsem_worker_heartbeat_seconds * 3,
        300,
    )
    active_workers = STORAGE.sync_workers.active(
        "trudvsem",
        stale_after=stale_after,
    )
    state["worker_alive"] = bool(active_workers)
    state["workers"] = [worker.public_summary() for worker in active_workers]
    latest_run = state.pop("latest_run", None)
    active_run = state.pop("active_run", None)
    checkpoint = state.pop("checkpoint", None)
    if latest_run:
        state["persisted_run"] = latest_run.public_summary()
    if active_run:
        state["active_run"] = active_run.public_summary()
    if checkpoint:
        state["checkpoint"] = checkpoint.public_summary()
    return state, 200


@app.post("/sync/trudvsem")
@csrf.exempt
@limiter.limit("10 per 5 minutes")
def sync_trudvsem():
    configured_secret = SYNC_SECRET or ""
    supplied_secret = request.headers.get("X-Sync-Secret", "").strip()
    if not configured_secret or not secrets.compare_digest(configured_secret, supplied_secret):
        return {"ok": False, "error": "unauthorized"}, 401

    run = request_trudvsem_sync(trigger="api")
    if run is None:
        return {
            "ok": False,
            "source": "trudvsem",
            "error": "sync disabled",
        }, 503
    return {
        "ok": True,
        "source": "trudvsem",
        "message": "sync job queued for external worker",
        "run_id": run.id,
        "status": run.status,
    }, 202


@app.get("/superjob/vacancies")
def superjob_vacancies_redirect():
    return redirect(url_for("vacancies", source="superjob"))


@app.get("/hh/vacancies")
def hh_vacancies_redirect():
    """Keep the legacy HH URL working through the unified vacancy search."""
    query = request.args.to_dict(flat=False)
    query["source"] = ["hh"]
    query["search"] = ["1"]
    return redirect(url_for("vacancies") + "?" + urlencode(query, doseq=True))


@app.get("/debug/hh")
@limiter.limit("20 per 5 minutes")
def debug_hh():
    """Run safe HH API diagnostics. Enabled only when DEBUG_HH=1."""
    if not DEBUG_HH or not diagnostics_access_allowed(SETTINGS):
        return {"ok": False, "error": "not found"}, 404

    # Diagnostics use a user OAuth token only when the caller already has a
    # valid first-party browser session. Provider identity is never restored
    # from legacy browser keys.
    row = hh_account() if getattr(g, "current_user", None) else None
    params = {
        "text": request.args.get("keyword", "инженер-конструктор").strip() or "инженер-конструктор",
        "period": 7,
        "page": 0,
        "per_page": 1,
        "order_by": "publication_time",
    }
    report = {
        "ok": False,
        "endpoint": HH_VACANCIES_URL,
        "params": params,
        "environment": {
            "debug_hh": DEBUG_HH,
            "render_region": RENDER_REGION,
            "python": platform.python_version(),
            "requests": requests.__version__,
            "hh_client_id_configured": bool(HH_CLIENT_ID),
            "hh_redirect_uri": HH_REDIRECT_URI,
            "hh_user_agent": HH_USER_AGENT,
            "hh_app_token_configured": bool(HH_APP_TOKEN),
            "hh_account_connected": bool(row),
        },
        "attempts": [],
    }

    attempts = []
    if HH_APP_TOKEN:
        attempts.append(("application", HH_APP_TOKEN))
    if row:
        try:
            attempts.append(("oauth", valid_hh_token(row)))
        except Exception as exc:
            report["oauth_token_error"] = f"{type(exc).__name__}: {exc}"
    attempts.append(("public", None))

    for name, token in attempts:
        started = time.monotonic()
        try:
            response = requests.get(
                HH_VACANCIES_URL,
                params=params,
                headers=hh_headers(token),
                timeout=30,
            )
            attempt = {
                "name": name,
                "seconds": round(time.monotonic() - started, 3),
                **_hh_response_report(response),
            }
            report["attempts"].append(attempt)
            logger.info(
                "HH DEBUG attempt=%s status=%s request_id=%s content_type=%s",
                name,
                response.status_code,
                response.headers.get("X-Request-Id")
                or response.headers.get("Request-Id")
                or response.headers.get("X-Request-ID"),
                response.headers.get("Content-Type"),
            )
        except requests.RequestException as exc:
            report["attempts"].append({
                "name": name,
                "seconds": round(time.monotonic() - started, 3),
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
            logger.exception("HH DEBUG request failed attempt=%s", name)

    report["ok"] = any(item.get("ok") for item in report["attempts"])
    return report, 200


def _readiness_response():
    started = time.monotonic()
    database_status = database_health(DATABASE)
    database_status["latency_ms"] = round(
        max(0.0, (time.monotonic() - started) * 1000.0),
        3,
    )
    migration_ok = database_status.get("revision") == CURRENT_REVISION
    ready = bool(database_status.get("ok") and migration_ok)
    status_code = 200 if ready else 503
    return {
        "status": "ok" if ready else "degraded",
        "service": SETTINGS.service_name,
        "version": SETTINGS.app_version,
        "request_id": current_request_id(),
        "uptime_seconds": OPS_STATE.uptime_seconds,
        "oauth_configured": True,
        "auth": {
            "email_backend": AUTH_SERVICE.email_backend_name,
            "email_delivery_configured": AUTH_SERVICE.email_delivery_available,
        },
        "database": {
            **database_status,
            "configured": SETTINGS.database_url_explicit,
        },
        "migrations": {
            "ok": migration_ok,
            "expected_revision": CURRENT_REVISION,
            "current_revision": database_status.get("revision"),
        },
    }, status_code


@app.get("/health/live")
@limiter.limit("300 per minute")
def health_live():
    return {
        "status": "ok",
        "service": SETTINGS.service_name,
        "version": SETTINGS.app_version,
        "request_id": current_request_id(),
        "uptime_seconds": OPS_STATE.uptime_seconds,
    }, 200


@app.get("/health/ready")
@limiter.limit("300 per minute")
def health_ready():
    return _readiness_response()


@app.get("/health")
@limiter.limit("300 per minute")
def health():
    # Backwards-compatible readiness alias used by existing monitoring.
    return _readiness_response()


@app.get("/health/search-dedup")
@limiter.limit("120 per 5 minutes")
def health_search_dedup():
    """Expose aggregate SEARCH-002 results from the most recent completed search.

    This endpoint never calls vacancy providers. It is intentionally limited to
    counts and source names so it can be opened directly in a browser during
    staging verification without exposing keywords, regions or credentials.
    """

    snapshot = OPS_STATE.search_dedup_snapshot()
    return {
        "ok": True,
        "status": "ok",
        "service": SETTINGS.service_name,
        "package": "SEARCH-002",
        "request_id": current_request_id(),
        "scope": "last_completed_search_in_current_web_process",
        "dedup": snapshot,
        "note": (
            "Counts describe only the vacancy candidates fetched for the latest "
            "search page after canonical filtering; provider-reported global totals "
            "are not scanned here."
        ),
    }, 200


@app.get("/health/search-pagination")
@limiter.limit("120 per 5 minutes")
def health_search_pagination():
    """Return secret-free SEARCH-003 state for one opaque snapshot ID."""

    snapshot_id = str(request.args.get("snapshot") or "").strip()
    if not snapshot_id or len(snapshot_id) > 64:
        return {
            "ok": False,
            "status": "invalid_request",
            "package": "SEARCH-003",
            "request_id": current_request_id(),
            "error": "snapshot is required",
        }, 400
    summary = STORAGE.search_snapshots.aggregate_summary(snapshot_id)
    if summary is None:
        return {
            "ok": False,
            "status": "not_found",
            "package": "SEARCH-003",
            "request_id": current_request_id(),
        }, 404
    return {
        "ok": True,
        "status": "ok",
        "service": SETTINGS.service_name,
        "package": "SEARCH-003",
        "request_id": current_request_id(),
        "scope": "bounded_persistent_search_snapshot",
        "snapshot": summary,
        "note": (
            "provider_reported_total is approximate until all source cursors are exhausted; "
            "known_unique_total counts stable materialized cards after canonical filters and dedup."
        ),
    }, 200


@app.get("/api/security/rate-limit-probe")
@limiter.limit("5 per minute")
def security_rate_limit_probe():
    """Secret-free production probe used to verify a controlled HTTP 429."""

    return {
        "ok": True,
        "status": "ok",
        "request_id": current_request_id(),
    }, 200


@app.get("/ops/status")
@limiter.limit("30 per 5 minutes")
def ops_status():
    if not diagnostics_access_allowed(SETTINGS):
        return {"ok": False, "error": "not found"}, 404
    database_status = database_health(DATABASE)
    return {
        "ok": bool(database_status.get("ok")),
        "service": SETTINGS.service_name,
        "version": SETTINGS.app_version,
        "request_id": current_request_id(),
        "database": {
            **database_status,
            "configured": SETTINGS.database_url_explicit,
        },
        "background": {
            "trudvsem_sync_enabled": TRUDVSEM_SYNC_ENABLED,
            "trudvsem_worker_mode": "external_process",
            "trudvsem_running": bool(trudvsem_sync_status().get("running")),
            "trudvsem_queued": bool(trudvsem_sync_status().get("queued")),
        },
        "telemetry": OPS_STATE.snapshot(include_recent_errors=True),
    }, 200


@app.post("/ops/alerts/test")
@csrf.exempt
@limiter.limit("3 per hour")
def ops_alert_test():
    if not diagnostics_access_allowed(SETTINGS):
        return {"ok": False, "error": "not found"}, 404
    if not ALERT_DISPATCHER.configured:
        return {
            "ok": False,
            "error": "alert webhook is not configured",
        }, 503
    accepted = ALERT_DISPATCHER.enqueue(build_test_alert_payload())
    return {
        "ok": accepted,
        "status": "queued" if accepted else "queue_full",
        "request_id": current_request_id(),
    }, 202 if accepted else 503


def _generic_error_response(status_code: int, title: str, message: str):
    if request.path.startswith("/api/") or request.is_json:
        return jsonify({"ok": False, "error": message}), status_code
    return render_template(
        "message.html",
        success=False,
        title=title,
        message=message,
    ), status_code


@app.errorhandler(400)
def bad_request_error(_error):
    return _generic_error_response(
        400,
        "Некорректный запрос",
        "Проверьте введённые данные и повторите действие.",
    )


@app.errorhandler(404)
def not_found_error(_error):
    return _generic_error_response(
        404,
        "Страница не найдена",
        "Проверьте адрес или вернитесь на главную страницу.",
    )


@app.errorhandler(405)
def method_not_allowed_error(_error):
    return _generic_error_response(
        405,
        "Действие недоступно",
        "Обновите страницу и повторите действие правильным способом.",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=SETTINGS.port, debug=SETTINGS.flask_debug)
