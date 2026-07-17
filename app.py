import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from flask import Flask, redirect, render_template, request, session, url_for

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

@app.get("/")
def home():
    return render_template("index.html", account=account())


@app.get("/privacy")
def privacy():
    return render_template("privacy.html")


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
                "User-Agent": "AI Career Platform support@example.com",
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

    return render_template(
        "message.html",
        success=True,
        title="HeadHunter подключён",
        message=(
            f"Авторизация выполнена. "
            f"Пользователь: {profile.get('first_name', '')} "
            f"{profile.get('last_name', '')}"
        ),
    )
@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.get("/dashboard")
def dashboard():
    row = account()
    if not row:
        return redirect(url_for("login"))
    try:
        response = requests.get(USER_CVS_URL, headers=headers(valid_token(row)), timeout=30)
        response.raise_for_status()
        resumes = response.json().get("objects", [])
        error = None
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        resumes, error = [], str(exc)
    return render_template("dashboard.html", account=row, resumes=resumes, error=error)


@app.get("/vacancies")
def vacancies():
    row = account()
    if not row:
        return redirect(url_for("login"))
    keyword = request.args.get("keyword", "инженер-конструктор").strip()
    period = request.args.get("period", "7")
    page = max(int(request.args.get("page", "0") or 0), 0)
    try:
        response = requests.get(VACANCIES_URL, params={
            "keyword": keyword, "period": period, "order_field": "date", "order_direction": "desc",
            "count": 20, "page": page,
        }, headers=headers(valid_token(row)), timeout=30)
        response.raise_for_status()
        payload = response.json()
        items, error = payload.get("objects", []), None
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        payload, items, error = {"more": False, "total": 0}, [], str(exc)
    return render_template("vacancies.html", vacancies=items, keyword=keyword, period=period, page=page,
                           more=payload.get("more", False), total=payload.get("total", 0), error=error)


@app.get("/health")
def health():
    return {"status": "ok", "oauth_configured": True, "database": str(DB_PATH)}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
