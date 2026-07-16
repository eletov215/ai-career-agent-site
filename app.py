import os

from flask import Flask, render_template, request

app = Flask(__name__)


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/privacy")
def privacy():
    return render_template("privacy.html")


@app.get("/oauth/superjob/callback")
def superjob_callback():
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        return (
            render_template(
                "callback.html",
                success=False,
                message=(
                    "Авторизация отклонена или завершилась "
                    f"ошибкой: {error}"
                ),
            ),
            400,
        )

    if not code:
        return (
            render_template(
                "callback.html",
                success=False,
                message=(
                    "Код авторизации не получен. "
                    "Эта страница используется как OAuth callback."
                ),
            ),
            400,
        )

    return render_template(
        "callback.html",
        success=True,
        message=(
            "Авторизация SuperJob успешно завершена. "
            "Можно закрыть эту страницу."
        ),
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
