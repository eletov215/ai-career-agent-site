import os
import secrets
from urllib.parse import urlencode

import requests
from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

SUPERJOB_CLIENT_ID = os.environ.get("SUPERJOB_CLIENT_ID", "").strip()
SUPERJOB_CLIENT_SECRET = os.environ.get("SUPERJOB_CLIENT_SECRET", "").strip()
SUPERJOB_REDIRECT_URI = os.environ.get("SUPERJOB_REDIRECT_URI", "").strip()

SUPERJOB_AUTHORIZE_URL = "https://www.superjob.ru/authorize/"
SUPERJOB_TOKEN_URL = "https://api.superjob.ru/2.0/oauth2/access_token/"
SUPERJOB_CURRENT_USER_URL = "https://api.superjob.ru/2.0/user/current/"


def oauth_configured() -> bool:
    return all(
        (
            SUPERJOB_CLIENT_ID,
            SUPERJOB_CLIENT_SECRET,
            SUPERJOB_REDIRECT_URI,
        )
    )


@app.get("/")
def home():
    return render_template(
        "index.html",
        oauth_configured=oauth_configured(),
    )


@app.get("/privacy")
def privacy():
    return render_template("privacy.html")


@app.get("/oauth/superjob/login")
def superjob_login():
    if not oauth_configured():
        return render_template(
            "callback.html",
            success=False,
            title="OAuth не настроен",
            message=(
                "На сервере отсутствуют переменные SUPERJOB_CLIENT_ID, "
                "SUPERJOB_CLIENT_SECRET или SUPERJOB_REDIRECT_URI."
            ),
        ), 503

    state = secrets.token_urlsafe(32)
    session["superjob_oauth_state"] = state

    params = {
        "client_id": SUPERJOB_CLIENT_ID,
        "redirect_uri": SUPERJOB_REDIRECT_URI,
        "state": state,
    }
    return redirect(f"{SUPERJOB_AUTHORIZE_URL}?{urlencode(params)}")


@app.get("/oauth/superjob/callback")
def superjob_callback():
    oauth_error = request.args.get("error")
    if oauth_error:
        return render_template(
            "callback.html",
            success=False,
            title="Авторизация отклонена",
            message=f"SuperJob вернул ошибку: {oauth_error}",
        ), 400

    expected_state = session.pop("superjob_oauth_state", None)
    returned_state = request.args.get("state")
    if not expected_state or returned_state != expected_state:
        return render_template(
            "callback.html",
            success=False,
            title="Ошибка безопасности",
            message="Параметр state отсутствует или не совпадает. Начните вход заново.",
        ), 400

    code = request.args.get("code")
    if not code:
        return render_template(
            "callback.html",
            success=False,
            title="Код не получен",
            message="SuperJob не передал временный код авторизации.",
        ), 400

    try:
        token_response = requests.post(
            SUPERJOB_TOKEN_URL,
            data={
                "code": code,
                "client_id": SUPERJOB_CLIENT_ID,
                "client_secret": SUPERJOB_CLIENT_SECRET,
                "redirect_uri": SUPERJOB_REDIRECT_URI,
            },
            timeout=30,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
    except (requests.RequestException, ValueError) as exc:
        return render_template(
            "callback.html",
            success=False,
            title="Не удалось получить токен",
            message=f"Ошибка при обмене кода на токен: {exc}",
        ), 502

    access_token = token_data.get("access_token")
    if not access_token:
        return render_template(
            "callback.html",
            success=False,
            title="Токен не получен",
            message="Ответ SuperJob не содержит access_token.",
        ), 502

    try:
        user_response = requests.get(
            SUPERJOB_CURRENT_USER_URL,
            headers={
                "X-Api-App-Id": SUPERJOB_CLIENT_SECRET,
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=30,
        )
        user_response.raise_for_status()
        user_data = user_response.json()
    except (requests.RequestException, ValueError) as exc:
        return render_template(
            "callback.html",
            success=False,
            title="Токен получен, профиль недоступен",
            message=f"Не удалось проверить профиль пользователя: {exc}",
        ), 502

    display_name = (
        user_data.get("name")
        or user_data.get("email")
        or user_data.get("id")
        or "пользователь SuperJob"
    )

    # Тестовая версия намеренно не сохраняет access_token и refresh_token.
    return render_template(
        "callback.html",
        success=True,
        title="SuperJob подключён",
        message=f"Авторизация успешна. Профиль: {display_name}.",
    )


@app.get("/health")
def health():
    return {"status": "ok", "oauth_configured": oauth_configured()}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
