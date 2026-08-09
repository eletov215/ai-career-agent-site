import json
import secrets
import socket
import platform
import time
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename


from services.hh_provider import HeadHunterProvider
from services.superjob_provider import SuperJobProvider
from services.reed_provider import ReedProvider
from services.search_filters import VacancySearchFilters, filter_vacancies
from services.vacancy_deduplication import deduplicate_vacancies
from services.vacancy_presenter import present_vacancy
from services.resume_parser import ResumeParseError, build_resume_preview, parse_resume_pdf
from services.university_logo import find_university_logo
from config import AppSettings, load_settings
from database import CURRENT_REVISION, create_database, database_health
from services.storage import StorageServices
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
OAUTH_CONNECTIONS = STORAGE.oauth_connections
SYNC_RUNS = STORAGE.sync_runs
USERS = STORAGE.users
VACANCY_STORE = STORAGE.vacancies

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


def _remember_oauth_state(prefix: str) -> str:
    state = secrets.token_urlsafe(32)
    session[f"{prefix}_oauth_state"] = state
    session[f"{prefix}_oauth_state_issued_at"] = int(time.time())
    return state


def _consume_oauth_state(prefix: str, received_state: str | None) -> bool:
    expected_state = session.pop(f"{prefix}_oauth_state", None)
    issued_at = session.pop(f"{prefix}_oauth_state_issued_at", None)
    if not expected_state or not received_state or issued_at is None:
        return False
    try:
        age = int(time.time()) - int(issued_at)
    except (TypeError, ValueError):
        return False
    if age < 0 or age > OAUTH_STATE_TTL_SECONDS:
        return False
    return secrets.compare_digest(str(expected_state), str(received_state))


def _establish_authenticated_session(**identities):
    """Clear transient session data while preserving connected providers."""

    connected = {
        "superjob_user_id": session.get("superjob_user_id"),
        "hh_user_id": session.get("hh_user_id"),
    }
    connected.update({key: value for key, value in identities.items() if value is not None})
    session.clear()
    for key, value in connected.items():
        if value is not None:
            session[key] = value
    session.permanent = True


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


def account():
    user_id = session.get("superjob_user_id")
    if not user_id:
        return None
    connection = OAUTH_CONNECTIONS.get("superjob", str(user_id))
    return connection.as_legacy_mapping() if connection else None


def save_account(profile, token_data):
    now = int(time.time())
    expires_in = token_data.get("expires_in")
    expires_at = now + int(expires_in) if expires_in else None
    OAUTH_CONNECTIONS.upsert(
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
    if row["expires_at"] and int(row["expires_at"]) <= int(time.time()) + 120:
        refresh_token = dec(row["refresh_token"])
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
        save_account(json.loads(row["profile_json"]), token_data)
        return access_token
    return dec(row["access_token"])


def hh_account():
    user_id = session.get("hh_user_id")
    if not user_id:
        return None
    connection = OAUTH_CONNECTIONS.get("headhunter", str(user_id))
    return connection.as_legacy_mapping() if connection else None


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


def save_hh_account(profile, token_data):
    now = int(time.time())
    expires_in = token_data.get("expires_in")
    expires_at = now + int(expires_in) if expires_in else None
    display_name = " ".join(
        part for part in (profile.get("first_name"), profile.get("last_name")) if part
    ) or None
    OAUTH_CONNECTIONS.upsert(
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
    expires_at = row["expires_at"]
    if not expires_at or int(expires_at) > int(time.time()) + 120:
        return dec(row["access_token"])

    refresh_token = dec(row["refresh_token"])
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

    profile = json.loads(row["profile_json"])
    save_hh_account(profile, token_data)
    return access_token


@app.get("/")
def home():
    return render_template(
        "index.html",
        account=account(),
        hh_account=hh_account(),
    )


@app.get("/privacy")
def privacy():
    return render_template("privacy.html")


@app.get("/oauth/superjob/login")
@limiter.limit("20 per 10 minutes")
def login():
    state = _remember_oauth_state("superjob")
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }
    return redirect(f"{AUTHORIZE_URL}?{urlencode(params)}")


@app.get("/oauth/superjob/callback")
@limiter.limit("60 per 10 minutes")
def callback():
    # Validate and consume state before processing any provider-controlled
    # response fields, including cancellation/error callbacks.
    received_state = request.args.get("state")
    if not _consume_oauth_state("superjob", received_state):
        return render_template(
            "message.html",
            success=False,
            title="Ошибка безопасности",
            message="Начните подключение заново.",
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

    except (requests.RequestException, ValueError, KeyError):
        logger.exception("SuperJob OAuth callback failed")
        return render_template(
            "message.html",
            success=False,
            title="Ошибка подключения",
            message="Не удалось завершить подключение SuperJob. Повторите попытку позже.",
        ), 502

    save_account(profile, token_data)
    _establish_authenticated_session(superjob_user_id=int(profile["id"]))

    return redirect(url_for("dashboard"))

@app.get("/oauth/hh/login")
@limiter.limit("20 per 10 minutes")
def hh_login():
    state = _remember_oauth_state("hh")

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
    # Validate and consume state for success and error responses alike.
    received_state = request.args.get("state")
    if not _consume_oauth_state("hh", received_state):
        return render_template(
            "message.html",
            success=False,
            title="Ошибка безопасности",
            message="Некорректный OAuth state. Начните подключение HH заново.",
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

    save_hh_account(profile, token_data)

    _establish_authenticated_session(hh_user_id=str(profile["id"]))

    return redirect(url_for("dashboard"))


@app.post("/logout")
@limiter.limit("20 per 10 minutes")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.get("/dashboard")
@limiter.limit("120 per 5 minutes")
def dashboard():
    superjob_row = account()
    hh_row = hh_account()

    if not superjob_row and not hh_row:
        return redirect(url_for("home"))

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
def vacancies_redirect():
    return redirect(url_for("ai_career"))


@app.get("/vacancies/internal")
@limiter.limit("60 per 5 minutes")
def vacancies():
    filters = VacancySearchFilters.from_query(request.args)
    keyword = filters.keyword
    remote_only = filters.remote_only
    search_requested = request.args.get("search") == "1"
    sync_queued = request.args.get("sync") == "queued"
    try:
        page = max(int(request.args.get("page", "0") or 0), 0)
    except ValueError:
        page = 0

    superjob_row = account()
    selected_sources = request.args.getlist("source")
    if not selected_sources:
        selected_sources = ["trudvsem"]

    hh_row = hh_account()
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
    total = 0
    has_next = False
    cache_note = None
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

    if search_requested:
        # Работа России is always searched locally. Network synchronization
        # is performed only by the external SYNC-001 worker process.
        if "trudvsem" in selected_sources:
            offset = page * VACANCY_PAGE_SIZE
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
            cache_age = VACANCY_STORE.source_age_seconds("trudvsem")
            sync_state = trudvsem_sync_status()

            if sync_state["running"]:
                cache_note = "Данные «Работы России» обновляются в фоне. Сайт продолжает работать из кэша."
            elif sync_state["queued"] or sync_queued:
                cache_note = "Фоновое обновление «Работы России» поставлено в очередь."
            elif cache_age is None:
                queued_run = request_trudvsem_sync(trigger="cache-miss")
                if queued_run is not None:
                    cache_note = "Кэш пока пуст. Загрузка поставлена в очередь; обнови страницу немного позже."
                else:
                    cache_note = "Кэш пока пуст, а внешняя синхронизация сейчас отключена."
            else:
                cache_note = f"Работа России загружена из локального кэша ({cache_age // 60} мин. назад)."
                latest_run = sync_state.get("latest_run")
                if latest_run and latest_run.status == "failed":
                    cache_note += " Последнее обновление завершилось ошибкой, сохранённые вакансии доступны."

            source_results["trudvsem"] = type("CachedResult", (), {
                "total": cached_total,
                "items": cached_items,
                "has_next": offset + len(cached_items) < cached_total,
                "error": None,
            })()
            all_items.extend(cached_items)
            total += cached_total
            has_next = has_next or offset + len(cached_items) < cached_total

        # Other providers remain direct, but run concurrently and cannot block
        # the cached Работа России results.
        direct_sources = [source for source in selected_sources if source != "trudvsem"]
        tasks = {}
        if direct_sources:
            with ThreadPoolExecutor(max_workers=min(len(direct_sources), 2) or 1) as executor:
                for source_key in direct_sources:
                    provider = providers.get(source_key)
                    if not provider:
                        if source_key == "superjob":
                            errors.append("SuperJob временно недоступен. Проверьте конфигурацию API приложения.")
                        elif source_key == "reed":
                            errors.append("Reed.co.uk не подключён. Добавьте REED_API_KEY в Render.")
                        continue
                    future = executor.submit(
                        _search_provider_with_metrics,
                        source_key,
                        provider,
                        filters=filters,
                        page=page,
                    )
                    tasks[future] = source_key

                for future in as_completed(tasks):
                    source_key = tasks[future]
                    try:
                        result = future.result()
                    except Exception:
                        logger.exception("Vacancy provider failed source=%s", source_key)
                        errors.append(f"{source_key}: unavailable")
                        continue
                    source_results[source_key] = result
                    all_items.extend(result.items)
                    total += result.total
                    has_next = has_next or result.has_next
                    if result.error:
                        errors.append(result.error)

        # Apply the same canonical contract at the aggregation boundary.
        # Provider-side filters are only an optimization; this final pass keeps
        # HH, Reed, SuperJob and cached Trudvsem behavior consistent.
        all_items = filter_vacancies(all_items, filters)

        # SEARCH-002: group only high-confidence cross-source duplicates.
        # Source publications remain attached to the representative card so the
        # decision is reversible and users can open any original listing.
        deduplication_result = deduplicate_vacancies(all_items)
        all_items = deduplication_result.items
        deduplication_stats = deduplication_result.stats.as_dict()
        logger.info(
            "Vacancy deduplication completed input=%s output=%s "
            "identity_duplicates=%s cross_source_duplicates=%s groups=%s",
            deduplication_stats["input_count"],
            deduplication_stats["output_count"],
            deduplication_stats["identity_duplicate_count"],
            deduplication_stats["cross_source_duplicate_count"],
            deduplication_stats["cross_source_groups"],
        )
        if filters.sort == "salary_desc":
            all_items.sort(
                key=lambda item: (
                    float(item.get("salary_to") or item.get("salary_from") or 0),
                    str(item.get("published_at") or ""),
                ),
                reverse=True,
            )
        elif filters.sort == "salary_asc":
            all_items.sort(
                key=lambda item: (
                    item.get("salary_from") is None and item.get("salary_to") is None,
                    float(item.get("salary_from") or item.get("salary_to") or 0),
                    str(item.get("published_at") or ""),
                )
            )
        else:
            all_items.sort(
                key=lambda item: (
                    bool(item.get("published_at")),
                    str(item.get("published_at") or ""),
                    str(item.get("title") or ""),
                ),
                reverse=True,
            )

        all_items = [present_vacancy(item) for item in all_items]

    source_options = [
        {"key": "trudvsem", "title": "Работа России", "available": True},
        {
            "key": "superjob",
            "title": "SuperJob",
            "available": bool(CLIENT_SECRET),
            "note": None if CLIENT_SECRET else "Источник временно недоступен",
            "status_text": "Поиск доступен без входа" if CLIENT_SECRET else None,
        },
        {
            "key": "reed",
            "title": "Reed.co.uk",
            "available": bool(REED_API_KEY),
            "note": None if REED_API_KEY else "Источник временно недоступен",
        },
        {
            "key": "hh",
            "title": "HeadHunter",
            "available": bool(HH_APP_TOKEN),
            "note": None if HH_APP_TOKEN else "Источник временно недоступен",
        },
    ]

    filter_pairs = filters.query_pairs()
    for source in selected_sources:
        filter_pairs.append(("source", source))
    filter_query = urlencode(filter_pairs)

    return render_template(
        "vacancies_unified.html",
        vacancies=all_items,
        keyword=keyword,
        remote_only=remote_only,
        filters=filters,
        selected_sources=selected_sources,
        source_options=source_options,
        source_results=source_results,
        page=page,
        has_next=has_next,
        total=total,
        errors=errors,
        search_requested=search_requested,
        cache_note=cache_note,
        filter_query=filter_query,
        show_manual_refresh=not SETTINGS.is_production,
        deduplication_stats=deduplication_stats,
    )


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

    row = hh_account()
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
