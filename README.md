# SuperJob OAuth test

Required Render environment variables:

- `SUPERJOB_CLIENT_ID` — application ID
- `SUPERJOB_CLIENT_SECRET` — rotated Secret Key
- `SUPERJOB_REDIRECT_URI` — `https://ai-career-agent-site.onrender.com/oauth/superjob/callback`
- `FLASK_SECRET_KEY` — a long random value

Do not put secrets in GitHub.

After deployment:

1. Open the website.
2. Click **Подключить SuperJob**.
3. Sign in on SuperJob.
4. Confirm that the callback shows **SuperJob подключён**.

The test does not persist access or refresh tokens.
