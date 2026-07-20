# HH vacancy search fix

Changes applied to the uploaded project version:

- Added the required `HH-User-Agent` header to HH API requests.
- Kept the standard `User-Agent` header for compatibility.
- Vacancy search now uses the stored OAuth access token.
- If HH returns 403 for the authorized search, the app retries once as a public request.
- Render still starts `app.py` (`gunicorn app:app`).

The project was syntax-checked with `python -m py_compile`.
