# AI Career Agent

## Local launch on Windows

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Open:

- http://127.0.0.1:10000
- http://127.0.0.1:10000/privacy
- http://127.0.0.1:10000/oauth/superjob/callback

## Render deployment

1. Upload all files to GitHub.
2. In Render choose New → Web Service.
3. Connect the repository.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`
6. Use:
   - Site: `https://YOUR-SERVICE.onrender.com`
   - Callback: `https://YOUR-SERVICE.onrender.com/oauth/superjob/callback`

Do not commit secrets or access tokens to GitHub.
