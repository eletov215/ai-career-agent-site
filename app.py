import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, redirect, render_template, request, session, url_for

from services.hh_provider import HeadHunterProvider
from services.superjob_provider import SuperJobProvider
from services.trudvsem_provider import TrudvsemProvider
from services.vacancy_store import VacancyStore

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

CLIENT_ID = os.environ["SUPERJOB_CLIENT_ID"].strip()
CLIENT_SECRET = os.environ["SUPERJOB_CLIENT_SECRET"].strip()
REDIRECT_URI = os.environ["SUPERJOB_REDIRECT_URI"].strip()
HH_CLIENT_ID = os.environ["HH_CLIENT_ID"].strip()
HH_CLIENT_SECRET = os.environ["HH_CLIENT_SECRET"].strip()
HH_REDIRECT_URI = os.environ["HH_REDIRECT_URI"].strip()
HH_USER_AGENT = os.environ["HH_USER_AGENT"].strip()

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


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
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


def hh_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": HH_USER_AGENT,
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
        headers={
            "Accept": "application/json",
            "User-Agent": HH_USER_AGENT,
        },
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


@app.get("/vacancies")
def vacancies():
    keyword = request.args.get("keyword", "инженер-конструктор").strip()
    remote_only = request.args.get("remote") == "1"
    search_requested = request.args.get("search") == "1"
    force_refresh = request.args.get("refresh") == "1"
    try:
        page = max(int(request.args.get("page", "0") or 0), 0)
    except ValueError:
        page = 0

    superjob_row = account()
    selected_sources = request.args.getlist("source")
    if not selected_sources:
        selected_sources = ["trudvsem"]

    providers = {"hh": HeadHunterProvider()}
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
        # Работа России: first read our local database. External API is called only
        # when the matching cache is empty/stale or the user requests refresh.
        if "trudvsem" in selected_sources:
            offset = page * VACANCY_PAGE_SIZE
            cached_items = VACANCY_STORE.search(
                keyword=keyword,
                sources=["trudvsem"],
                remote_only=remote_only,
                limit=VACANCY_PAGE_SIZE,
                offset=offset,
            )
            cached_total = VACANCY_STORE.count(
                keyword=keyword,
                sources=["trudvsem"],
                remote_only=remote_only,
            )
            cache_age = VACANCY_STORE.source_age_seconds("trudvsem")
            cache_fresh = cache_age is not None and cache_age < VACANCY_CACHE_TTL

            if force_refresh or not cached_items or not cache_fresh:
                result = TrudvsemProvider(HH_USER_AGENT, per_page=100).search(
                    keyword=keyword,
                    page=page,
                    remote_only=False,
                )
                source_results["trudvsem"] = result
                if result.items:
                    VACANCY_STORE.upsert_many(result.items)
                    cached_items = VACANCY_STORE.search(
                        keyword=keyword,
                        sources=["trudvsem"],
                        remote_only=remote_only,
                        limit=VACANCY_PAGE_SIZE,
                        offset=offset,
                    )
                    cached_total = VACANCY_STORE.count(
                        keyword=keyword,
                        sources=["trudvsem"],
                        remote_only=remote_only,
                    )
                    cache_age = 0
                elif result.error:
                    errors.append(result.error)
            else:
                cache_note = f"Работа России загружена из кэша ({cache_age // 60} мин. назад)."

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
                        keyword=keyword,
                        page=page,
                        remote_only=remote_only,
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

        # Remove duplicates across providers and sort newest first.
        unique_items = {}
        for item in all_items:
            key = (item.get("source"), item.get("external_id") or item.get("url"))
            unique_items[key] = item
        all_items = list(unique_items.values())
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
        {"key": "hh", "title": "HeadHunter", "available": bool(hh_account()), "note": "поиск временно недоступен"},
    ]

    return render_template(
        "vacancies_unified.html",
        vacancies=all_items,
        keyword=keyword,
        remote_only=remote_only,
        selected_sources=selected_sources,
        source_options=source_options,
        source_results=source_results,
        page=page,
        has_next=has_next,
        total=total,
        errors=errors,
        search_requested=search_requested,
        cache_note=cache_note,
    )


@app.post("/sync/trudvsem")
def sync_trudvsem():
    configured_secret = os.environ.get("SYNC_SECRET", "").strip()
    supplied_secret = request.headers.get("X-Sync-Secret", "").strip()
    if not configured_secret or not secrets.compare_digest(configured_secret, supplied_secret):
        return {"ok": False, "error": "unauthorized"}, 401

    keyword = (request.args.get("keyword") or "инженер-конструктор").strip()
    try:
        pages = min(max(int(request.args.get("pages", "2")), 1), 10)
    except ValueError:
        pages = 2

    provider = TrudvsemProvider(HH_USER_AGENT, per_page=100)
    saved = 0
    errors = []
    for page_number in range(pages):
        result = provider.search(keyword=keyword, page=page_number, remote_only=False)
        if result.error:
            errors.append(result.error)
            break
        saved += VACANCY_STORE.upsert_many(result.items)
        if not result.has_next:
            break

    return {
        "ok": not errors,
        "source": "trudvsem",
        "keyword": keyword,
        "saved": saved,
        "errors": errors,
    }, 200 if not errors else 502


@app.get("/superjob/vacancies")
def superjob_vacancies_redirect():
    return redirect(url_for("vacancies", source="superjob"))


@app.get("/hh/vacancies")
def hh_vacancies():
    row = hh_account()
    if not row:
        return redirect(url_for("hh_login"))

    keyword = request.args.get("keyword", "инженер-конструктор").strip()
    period = request.args.get("period", "7").strip()
    remote_only = request.args.get("remote") == "1"

    try:
        page = max(int(request.args.get("page", "0") or 0), 0)
    except ValueError:
        page = 0

    if period not in {"1", "3", "7", "14", "30"}:
        period = "7"

    params = {
        "text": keyword,
        "period": period,
        "page": page,
        "per_page": 20,
        "order_by": "publication_time",
    }
    if remote_only:
        params["schedule"] = "remote"

    payload = {"items": [], "found": 0, "pages": 0, "page": page}
    error = None

    try:
        response = requests.get(
    HH_VACANCIES_URL,
    params=params,
    headers={
        "Accept": "application/json",
        "User-Agent": HH_USER_AGENT,
    },
    timeout=30,
)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        response_text = ""
        if exc.response is not None:
            response_text = exc.response.text[:1000]
        error = str(exc)
        if response_text:
            error += f" Ответ HH: {response_text}"
    except (ValueError, KeyError, RuntimeError) as exc:
        error = str(exc)

    return render_template(
        "hh_vacancies.html",
        vacancies=payload.get("items", []),
        keyword=keyword,
        period=period,
        remote_only=remote_only,
        page=page,
        pages=int(payload.get("pages", 0) or 0),
        total=int(payload.get("found", 0) or 0),
        error=error,
    )


@app.get("/health")
def health():
    return {"status": "ok", "oauth_configured": True, "database": str(DB_PATH)}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
