# AI Career Agent

Flask MVP with independent vacancy providers.

## Vacancy architecture

- `services/trudvsem_provider.py` — official open API of «Работа России».
- `services/superjob_provider.py` — SuperJob OAuth/API adapter.
- `services/hh_provider.py` — HeadHunter adapter placeholder while vacancy search returns 403.
- `/vacancies` — unified search page.

The provider layer normalizes each source to one vacancy schema so new platforms can be added without rebuilding the UI.

## Environment variables

- `FLASK_SECRET_KEY`
- `TOKEN_ENCRYPTION_KEY`
- `SUPERJOB_CLIENT_ID`
- `SUPERJOB_CLIENT_SECRET`
- `SUPERJOB_REDIRECT_URI`
- `HH_CLIENT_ID`
- `HH_CLIENT_SECRET`
- `HH_REDIRECT_URI`
- `HH_USER_AGENT`
- optional `DATA_DIR`
