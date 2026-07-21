import json
import os
import secrets
import socket
import platform
import sqlite3
import time
import threading
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from datetime import datetime, timezone

from services.hh_provider import HeadHunterProvider
from services.superjob_provider import SuperJobProvider
from services.trudvsem_provider import TrudvsemProvider
from services.vacancy_store import VacancyStore
from services.search_filters import VacancySearchFilters, canonical_currency
from services.resume_parser import ResumeParseError, build_resume_preview, parse_resume_pdf

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

CLIENT_ID = os.environ["SUPERJOB_CLIENT_ID"].strip()
CLIENT_SECRET = os.environ["SUPERJOB_CLIENT_SECRET"].strip()
REDIRECT_URI = os.environ["SUPERJOB_REDIRECT_URI"].strip()
HH_CLIENT_ID = os.environ["HH_CLIENT_ID"].strip()
HH_CLIENT_SECRET = os.environ["HH_CLIENT_SECRET"].strip()
HH_REDIRECT_URI = os.environ["HH_REDIRECT_URI"].strip()
HH_USER_AGENT = os.environ["HH_USER_AGENT"].strip()
HH_APP_TOKEN = os.environ.get("HH_APP_TOKEN", "").strip() or None

HH_AUTHORIZE_URL = "https://hh.ru/oauth/authorize"
HH_TOKEN_URL = "https://api.hh.ru/token"
HH_ME_URL = "https://api.hh.ru/me"
HH_VACANCIES_URL = "https://api.hh.ru/vacancies"
FERNET = Fernet(os.environ["TOKEN_ENCRYPTION_KEY"].strip().encode())

AUTHORIZE_URL = "https://www.superjob.ru/authorize/"
TOKEN_URL = "https://api.superjob.ru/2.0/oauth2/access_token/"
REFRESH_URL = "https://api.superjob.ru/2.0/oauth2/refresh_token/"
CURRENT_USER_URL = "https://api.superjob.ru/2.0/user/current/"
USER_CVS_URL = "https://api.superjob.ru/2.0/user_cvs/"
VACANCIES_URL = "https://api.superjob.ru/2.0/vacancies/"

DATA_DIR = Path(os.environ.get("DATA_DIR", "/tmp/ai-career-agent"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "app.db"
VACANCY_CACHE_TTL = int(os.environ.get("VACANCY_CACHE_TTL", "1800"))
VACANCY_PAGE_SIZE = 60
TRUDVSEM_SYNC_INTERVAL = int(os.environ.get("TRUDVSEM_SYNC_INTERVAL", "1800"))
TRUDVSEM_SYNC_ITEMS = int(os.environ.get("TRUDVSEM_SYNC_ITEMS", "300"))
TRUDVSEM_SYNC_BATCH = int(os.environ.get("TRUDVSEM_SYNC_BATCH", "10"))
TRUDVSEM_REQUEST_ATTEMPTS = int(os.environ.get("TRUDVSEM_REQUEST_ATTEMPTS", "5"))
TRUDVSEM_RETRY_BACKOFF = float(os.environ.get("TRUDVSEM_RETRY_BACKOFF", "1"))
TRUDVSEM_SYNC_ENABLED = os.environ.get("TRUDVSEM_SYNC_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
DEBUG_HH = os.environ.get("DEBUG_HH", "0").strip().lower() in {"1", "true", "yes", "on"}
MAX_RESUME_UPLOAD_MB = max(1, min(int(os.environ.get("MAX_RESUME_UPLOAD_MB", "8")), 25))


def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at INTEGER,
                profile_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS hh_accounts (
            user_id TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            expires_at INTEGER,
            profile_json TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """)
        conn.commit()


init_db()
VACANCY_STORE = VacancyStore(DB_PATH)
VACANCY_STORE.init()

TRUDVSEM_SYNC_EVENT = threading.Event()
TRUDVSEM_SYNC_LOCK = threading.Lock()
TRUDVSEM_SYNC_THREAD = None
TRUDVSEM_SYNC_STATE = {
    "running": False,
    "queued": False,
    "last_started": None,
    "last_finished": None,
    "last_success": None,
    "last_saved": 0,
    "last_processed": 0,
    "current_offset": 0,
    "target": max(1, min(TRUDVSEM_SYNC_ITEMS, 500)),
    "progress_percent": 0,
    "last_error": None,
}


def trudvsem_sync_status():
    with TRUDVSEM_SYNC_LOCK:
        return dict(TRUDVSEM_SYNC_STATE)


def request_trudvsem_sync():
    already_queued = TRUDVSEM_SYNC_EVENT.is_set()
    TRUDVSEM_SYNC_EVENT.set()
    with TRUDVSEM_SYNC_LOCK:
        TRUDVSEM_SYNC_STATE["queued"] = True
    logger.info(
        "Trudvsem event set",
    )
    logger.info(
        "Trudvsem sync requested already_queued=%s running=%s",
        already_queued,
        trudvsem_sync_status().get("running"),
    )


def _run_trudvsem_sync():
    with TRUDVSEM_SYNC_LOCK:
        if TRUDVSEM_SYNC_STATE["running"]:
            return

        previous_success = TRUDVSEM_SYNC_STATE.get("last_success")

        target = max(1, min(TRUDVSEM_SYNC_ITEMS, 500))
        TRUDVSEM_SYNC_STATE.update(
            running=True,
            queued=False,
            last_started=int(time.time()),
            last_finished=None,
            last_error=None,
            last_saved=0,
            last_processed=0,
            current_offset=0,
            target=target,
            progress_percent=0,
        )

    saved = 0
    processed = 0
    error = None

    try:
        logger.info(
            "Trudvsem provider init previous_success=%s",
            previous_success,
        )

        provider = TrudvsemProvider(
            HH_USER_AGENT,
            per_page=10,
            timeout=(5, 45),
            scan_pages=5,
            request_attempts=TRUDVSEM_REQUEST_ATTEMPTS,
            retry_backoff=TRUDVSEM_RETRY_BACKOFF,
        )

        batch_size = max(1, min(TRUDVSEM_SYNC_BATCH, 10))
        target = max(batch_size, min(TRUDVSEM_SYNC_ITEMS, 500))

        # После первой синхронизации запрашиваем только изменённые вакансии.
        modified_from = None

        if previous_success:
            modified_from = datetime.fromtimestamp(
                previous_success,
                tz=timezone.utc,
            ).strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(
            "Trudvsem background sync started target=%s batch_size=%s modified_from=%s",
            target,
            batch_size,
            modified_from,
        )

        total_pages = (target + batch_size - 1) // batch_size
        for page_number in range(1, total_pages + 1):
            remaining = target - processed
            requested = min(batch_size, remaining)
            items = provider.fetch_batch(
                offset=page_number,
                limit=requested,
                modified_from=modified_from,
            )

            logger.info(
                "Trudvsem batch fetched offset=%s requested=%s received=%s first=%s",
                page_number,
                requested,
                len(items),
                items[0].get("external_id") if items else None,
            )

            if not items:
                # Пустая первая страница является нормальным ответом при
                # инкрементальной синхронизации: после previous_success новых
                # или изменённых вакансий могло не появиться. Считаем это
                # ошибкой только при самой первой полной загрузке пустого кэша.
                cached_before_sync = VACANCY_STORE.count(
                    keyword="",
                    sources=["trudvsem"],
                    period_days=3650,
                )
                if (
                    page_number == 1
                    and processed == 0
                    and modified_from is None
                    and cached_before_sync == 0
                ):
                    raise RuntimeError("API 'Работы России' вернул пустую первую страницу")

                logger.info(
                    "Trudvsem sync has no new items page=%s modified_from=%s cached=%s",
                    page_number,
                    modified_from,
                    cached_before_sync,
                )
                break

            processed += len(items)
            saved += VACANCY_STORE.upsert_many(items)
            progress = min(100, int(processed * 100 / target))
            with TRUDVSEM_SYNC_LOCK:
                TRUDVSEM_SYNC_STATE.update(
                    last_processed=processed,
                    last_saved=saved,
                    current_offset=processed,
                    progress_percent=progress,
                )
            logger.info(
                "Trudvsem batch saved page=%s processed=%s saved=%s",
                page_number,
                processed,
                saved,
            )
            time.sleep(0.15)

        logger.info(
            "Trudvsem background sync completed processed=%s saved=%s modified_from=%s",
            processed,
            saved,
            modified_from,
        )

    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        logger.warning(
            "Trudvsem background sync failed error=%s",
            error,
        )

    finally:
        with TRUDVSEM_SYNC_LOCK:
            finished_at = int(time.time())
            TRUDVSEM_SYNC_STATE.update(
                running=False,
                last_finished=finished_at,
                last_saved=saved,
                last_processed=processed,
                current_offset=processed,
                progress_percent=min(100, int(processed * 100 / max(1, target))),
                last_error=error,
            )
            if error is None:
                TRUDVSEM_SYNC_STATE["last_success"] = finished_at
        
def _trudvsem_sync_worker():
    logger.info("Trudvsem sync worker started")
    time.sleep(2)

    while True:
        age = VACANCY_STORE.source_age_seconds("trudvsem")

        if (
            age is None
            or age >= TRUDVSEM_SYNC_INTERVAL
            or TRUDVSEM_SYNC_EVENT.is_set()
        ):
            TRUDVSEM_SYNC_EVENT.clear()
            _run_trudvsem_sync()

        TRUDVSEM_SYNC_EVENT.wait(timeout=30)


def start_trudvsem_sync_worker():
    global TRUDVSEM_SYNC_THREAD
    
    logger.info("ENTER start_trudvsem_sync_worker")

    if not TRUDVSEM_SYNC_ENABLED:
        logger.info("Trudvsem sync worker disabled")
        return

    if (
        TRUDVSEM_SYNC_THREAD is not None
        and TRUDVSEM_SYNC_THREAD.is_alive()
    ):
        logger.info("Trudvsem sync worker already running")
        return

    TRUDVSEM_SYNC_THREAD = threading.Thread(
        target=_trudvsem_sync_worker,
        name="trudvsem-sync-worker",
        daemon=True,
    )

    TRUDVSEM_SYNC_THREAD.start()

    logger.info(
        "Trudvsem sync thread launched alive=%s",
        TRUDVSEM_SYNC_THREAD.is_alive(),
    )
@app.before_request
def start_background_workers():
    global TRUDVSEM_SYNC_THREAD

    if TRUDVSEM_SYNC_ENABLED and TRUDVSEM_SYNC_THREAD is None:
        logger.info("Starting background worker from request")
        start_trudvsem_sync_worker()

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
    with db() as conn:
        return conn.execute("SELECT * FROM accounts WHERE user_id = ?", (user_id,)).fetchone()


def save_account(profile, token_data):
    now = int(time.time())
    expires_in = token_data.get("expires_in")
    expires_at = now + int(expires_in) if expires_in else None
    with db() as conn:
        conn.execute("""
            INSERT INTO accounts (user_id, name, email, access_token, refresh_token, expires_at, profile_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                name=excluded.name,
                email=excluded.email,
                access_token=excluded.access_token,
                refresh_token=COALESCE(excluded.refresh_token, accounts.refresh_token),
                expires_at=excluded.expires_at,
                profile_json=excluded.profile_json,
                updated_at=excluded.updated_at
        """, (
            int(profile["id"]), profile.get("name") or "Пользователь SuperJob", profile.get("email"),
            enc(token_data["access_token"]), enc(token_data.get("refresh_token")), expires_at,
            json.dumps(profile, ensure_ascii=False), now,
        ))
        conn.commit()


def valid_token(row):
    if row["expires_at"] and int(row["expires_at"]) <= int(time.time()) + 120:
        refresh_token = dec(row["refresh_token"])
        if not refresh_token:
            raise RuntimeError("Refresh token отсутствует. Подключите SuperJob заново.")
        response = requests.get(REFRESH_URL, params={
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }, headers={"X-Api-App-Id": CLIENT_SECRET}, timeout=30)
        response.raise_for_status()
        token_data = response.json()
        save_account(json.loads(row["profile_json"]), token_data)
        return token_data["access_token"]
    return dec(row["access_token"])


def hh_account():
    user_id = session.get("hh_user_id")

    if not user_id:
        return None

    with db() as conn:
        return conn.execute(
            "SELECT * FROM hh_accounts WHERE user_id = ?",
            (str(user_id),),
        ).fetchone()


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
    """Build a JSON-safe diagnostic report without exposing OAuth secrets."""
    return {
        "status_code": response.status_code,
        "ok": response.ok,
        "url": response.url,
        "request_headers": _masked_hh_headers(response.request.headers),
        "response_headers": dict(response.headers),
        "body_preview": response.text[:2000],
    }


def save_hh_account(profile, token_data):
    now = int(time.time())

    expires_in = token_data.get("expires_in")
    expires_at = now + int(expires_in) if expires_in else None

    user_id = str(profile["id"])

    with db() as conn:
        conn.execute(
            """
            INSERT INTO hh_accounts (
                user_id,
                first_name,
                last_name,
                email,
                access_token,
                refresh_token,
                expires_at,
                profile_json,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                email = excluded.email,
                access_token = excluded.access_token,
                refresh_token = COALESCE(
                    excluded.refresh_token,
                    hh_accounts.refresh_token
                ),
                expires_at = excluded.expires_at,
                profile_json = excluded.profile_json,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                profile.get("first_name"),
                profile.get("last_name"),
                profile.get("email"),
                enc(token_data["access_token"]),
                enc(token_data.get("refresh_token")),
                expires_at,
                json.dumps(profile, ensure_ascii=False),
                now,
            ),
        )

        conn.commit()


def valid_hh_token(row):
    """Return a valid HH access token, refreshing it shortly before expiry."""
    expires_at = row["expires_at"]
    if not expires_at or int(expires_at) > int(time.time()) + 120:
        return dec(row["access_token"])

    refresh_token = dec(row["refresh_token"])
    if not refresh_token:
        raise RuntimeError("Refresh token HH отсутствует. Подключите HeadHunter заново.")

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
    response.raise_for_status()
    token_data = response.json()

    profile = json.loads(row["profile_json"])
    save_hh_account(profile, token_data)
    return token_data["access_token"]


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
def login():
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }
    return redirect(f"{AUTHORIZE_URL}?{urlencode(params)}")


@app.get("/oauth/superjob/callback")
def callback():
    if request.args.get("error"):
        return render_template(
            "message.html",
            success=False,
            title="Авторизация отклонена",
            message=request.args["error"],
        ), 400

    expected_state = session.pop("oauth_state", None)
    received_state = request.args.get("state")

    if (
        not expected_state
        or not received_state
        or not secrets.compare_digest(expected_state, received_state)
    ):
        return render_template(
            "message.html",
            success=False,
            title="Ошибка безопасности",
            message="Начните подключение заново.",
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

    except (requests.RequestException, ValueError, KeyError) as exc:
        return render_template(
            "message.html",
            success=False,
            title="Ошибка подключения",
            message=str(exc),
        ), 502

    save_account(profile, token_data)
    session["superjob_user_id"] = int(profile["id"])

    return redirect(url_for("dashboard"))

@app.get("/oauth/hh/login")
def hh_login():
    state = secrets.token_urlsafe(32)
    session["hh_oauth_state"] = state

    params = {
        "response_type": "code",
        "client_id": HH_CLIENT_ID,
        "redirect_uri": HH_REDIRECT_URI,
        "state": state,
    }

    return redirect(f"{HH_AUTHORIZE_URL}?{urlencode(params)}")


@app.get("/oauth/hh/callback")
def hh_callback():
    error = request.args.get("error")

    if error:
        return render_template(
            "message.html",
            success=False,
            title="Авторизация HH отклонена",
            message=error,
        ), 400

    expected_state = session.pop("hh_oauth_state", None)
    received_state = request.args.get("state")

    if (
        not expected_state
        or not received_state
        or not secrets.compare_digest(expected_state, received_state)
    ):
        return render_template(
            "message.html",
            success=False,
            title="Ошибка безопасности",
            message="Некорректный OAuth state. Начните подключение HH заново.",
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

    except requests.RequestException as exc:
        response_text = ""

        if exc.response is not None:
            response_text = exc.response.text[:1000]

        message = f"{exc}"

        if response_text:
            message += f"\n\nОтвет HH: {response_text}"

        return render_template(
            "message.html",
            success=False,
            title="Ошибка подключения HH",
            message=message,
        ), 502

    except (ValueError, KeyError) as exc:
        return render_template(
            "message.html",
            success=False,
            title="Некорректный ответ HH",
            message=str(exc),
        ), 502

    save_hh_account(profile, token_data)

    session["hh_user_id"] = str(profile["id"])

    return redirect(url_for("dashboard"))
@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.get("/dashboard")
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
            error = str(exc)

    return render_template(
        "dashboard.html",
        account=superjob_row,
        hh_account=hh_row,
        resumes=resumes,
        error=error,
    )


@app.post("/api/resume/preview")
def resume_preview_api():
    uploaded = request.files.get("resume")
    if not uploaded or not uploaded.filename:
        return jsonify({"ok": False, "error": "Выберите PDF-файл с резюме."}), 400

    safe_name = Path(uploaded.filename).name
    if not safe_name.lower().endswith(".pdf"):
        return jsonify({"ok": False, "error": "Поддерживаются только файлы PDF."}), 400

    max_bytes = MAX_RESUME_UPLOAD_MB * 1024 * 1024
    file_bytes = uploaded.stream.read(max_bytes + 1)
    if len(file_bytes) > max_bytes:
        return jsonify({"ok": False, "error": f"Размер PDF не должен превышать {MAX_RESUME_UPLOAD_MB} МБ."}), 413

    try:
        parsed = parse_resume_pdf(file_bytes, safe_name)
    except ResumeParseError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify({"ok": True, "profile": build_resume_preview(parsed)})


@app.route("/ai-career", methods=["GET", "POST"])
def ai_career():
    parsed_resume = None
    upload_error = None

    source_options = [
        {"key": "trudvsem", "title": "Работа России", "available": True, "connected": True},
        {
            "key": "hh",
            "title": "HeadHunter",
            "available": bool(HH_APP_TOKEN),
            "connected": bool(HH_APP_TOKEN),
            "connect_url": url_for("hh_login"),
        },
        {
            "key": "superjob",
            "title": "SuperJob",
            "available": bool(account()),
            "connected": bool(account()),
            "connect_url": url_for("login"),
        },
    ]

    if request.method == "POST":
        uploaded = request.files.get("resume")
        if not uploaded or not uploaded.filename:
            upload_error = "Выберите PDF-файл с резюме."
        else:
            safe_name = Path(uploaded.filename).name
            if not safe_name.lower().endswith(".pdf"):
                upload_error = "Поддерживаются только файлы PDF."
            else:
                max_bytes = MAX_RESUME_UPLOAD_MB * 1024 * 1024
                file_bytes = uploaded.stream.read(max_bytes + 1)
                if len(file_bytes) > max_bytes:
                    upload_error = f"Размер PDF не должен превышать {MAX_RESUME_UPLOAD_MB} МБ."
                else:
                    try:
                        parsed_resume = parse_resume_pdf(file_bytes, safe_name)
                    except ResumeParseError as exc:
                        upload_error = str(exc)

    return render_template(
        "ai_career.html",
        parsed_resume=parsed_resume,
        upload_error=upload_error,
        max_resume_upload_mb=MAX_RESUME_UPLOAD_MB,
        source_options=source_options,
    )


@app.get("/vacancies")
def vacancies_redirect():
    return redirect(url_for("ai_career"))


@app.get("/vacancies/internal")
def vacancies():
    filters = VacancySearchFilters.from_query(request.args)
    keyword = filters.keyword
    remote_only = filters.remote_only
    search_requested = request.args.get("search") == "1"
    force_refresh = request.args.get("refresh") == "1"
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
        )
    }
    if superjob_row:
        providers["superjob"] = SuperJobProvider(
            VACANCIES_URL,
            headers,
            lambda: valid_token(superjob_row),
        )

    all_items = []
    source_results = {}
    errors = []
    total = 0
    has_next = False
    cache_note = None

    if search_requested:
        # Работа России is always searched locally. Network synchronization
        # runs in a daemon thread and never blocks page navigation.
        if "trudvsem" in selected_sources:
            if force_refresh:
                request_trudvsem_sync()

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
                cache_note = "Данные «Работы России» обновляются в фоне. Сайт продолжает работать без ожидания API."
            elif force_refresh or sync_queued:
                cache_note = "Фоновое обновление «Работы России» запущено. Новые вакансии появятся после обновления страницы."
            elif cache_age is None:
                request_trudvsem_sync()
                cache_note = "Кэш пока пуст. Фоновая загрузка вакансий запущена; обнови страницу через минуту."
            else:
                cache_note = f"Работа России загружена из локального кэша ({cache_age // 60} мин. назад)."
                if sync_state.get("last_error"):
                    cache_note += " Последнее фоновое обновление завершилось ошибкой, сохранённые вакансии доступны."

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
                            errors.append("SuperJob не подключён. Подключите аккаунт в личном кабинете.")
                        continue
                    future = executor.submit(
                        provider.search,
                        filters=filters,
                        page=page,
                    )
                    tasks[future] = source_key

                for future in as_completed(tasks):
                    source_key = tasks[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        errors.append(f"{source_key}: {exc}")
                        continue
                    source_results[source_key] = result
                    all_items.extend(result.items)
                    total += result.total
                    has_next = has_next or result.has_next
                    if result.error:
                        errors.append(result.error)

        # Enforce currency consistently after all providers are combined.
        # Some APIs treat currency as a salary-conversion hint rather than a strict filter.
        if filters.currency:
            all_items = [
                item for item in all_items
                if canonical_currency(item.get("currency")) == filters.currency
            ]

        # Remove duplicates across providers and sort newest first.
        unique_items = {}
        for item in all_items:
            key = (item.get("source"), item.get("external_id") or item.get("url"))
            unique_items[key] = item
        all_items = list(unique_items.values())
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

    source_options = [
        {"key": "trudvsem", "title": "Работа России", "available": True},
        {"key": "superjob", "title": "SuperJob", "available": bool(superjob_row)},
        {
            "key": "hh",
            "title": "HeadHunter",
            "available": bool(HH_APP_TOKEN),
            "note": None if HH_APP_TOKEN else "Не настроен токен приложения",
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
    )


@app.get("/debug/trudvsem")
def debug_trudvsem():
    """Diagnose Render -> Работа России connectivity without exposing secrets."""
    host = "opendata.trudvsem.ru"
    api_url = f"https://{host}/api/v1/vacancies"
    report = {
        "service": "Работа России",
        "api_url": api_url,
        "render_region": os.environ.get("RENDER_REGION") or "unknown",
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
def refresh_trudvsem_cache():
    """Queue a refresh and return immediately; never wait for the API."""
    request_trudvsem_sync()
    filters = VacancySearchFilters.from_query(request.form)
    sources = request.form.getlist("source") or ["trudvsem"]
    params = filters.query_pairs()
    params.append(("sync", "queued"))
    params.extend(("source", source) for source in sources)
    return redirect(url_for("vacancies") + "?" + urlencode(params))


@app.get("/trudvsem/status")
def trudvsem_status():
    state = trudvsem_sync_status()
    state["cache_age_seconds"] = VACANCY_STORE.source_age_seconds("trudvsem")
    state["cached_total"] = VACANCY_STORE.count(keyword="", sources=["trudvsem"])
    state["sync_enabled"] = TRUDVSEM_SYNC_ENABLED
    state["worker_alive"] = bool(TRUDVSEM_SYNC_THREAD and TRUDVSEM_SYNC_THREAD.is_alive())
    state["queued"] = bool(state.get("queued") or TRUDVSEM_SYNC_EVENT.is_set())
    return state, 200


@app.post("/sync/trudvsem")
def sync_trudvsem():
    configured_secret = os.environ.get("SYNC_SECRET", "").strip()
    supplied_secret = request.headers.get("X-Sync-Secret", "").strip()
    if not configured_secret or not secrets.compare_digest(configured_secret, supplied_secret):
        return {"ok": False, "error": "unauthorized"}, 401

    request_trudvsem_sync()
    return {
        "ok": True,
        "source": "trudvsem",
        "message": "background sync scheduled",
        "status": trudvsem_sync_status(),
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
def debug_hh():
    """Run safe HH API diagnostics. Enabled only when DEBUG_HH=1."""
    if not DEBUG_HH:
        return {
            "ok": False,
            "error": "HH diagnostics are disabled. Set DEBUG_HH=1 in Render and redeploy.",
        }, 404

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
            "render_region": os.environ.get("RENDER_REGION") or "unknown",
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
                "HH DEBUG attempt=%s status=%s url=%s request_headers=%s response_headers=%s body=%s",
                name,
                response.status_code,
                response.url,
                _masked_hh_headers(response.request.headers),
                dict(response.headers),
                response.text[:2000],
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


@app.get("/health")
def health():
    return {"status": "ok", "oauth_configured": True, "database": str(DB_PATH)}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
