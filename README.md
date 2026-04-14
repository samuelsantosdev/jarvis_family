# Jarvis Family

A Python application with a **Tkinter** desktop client and a **FastAPI** backend that provides authentication with:

- **Email / Password** registration and login
- **Email confirmation** (account activated only after clicking the link)
- **Welcome email** sent on successful confirmation
- **Social login** (Gmail, Apple, any Auth0 connection) via OAuth2 in the system browser
- Only **confirmed** accounts can log in

---

## Project Structure

```
jarvis_family/
├── api/                  # FastAPI backend
│   ├── main.py           # Routes: /auth/register, /auth/confirm/{token}, /auth/login, /auth/social/*
│   ├── models.py         # SQLAlchemy User model
│   ├── database.py       # DB engine + session factory
│   ├── auth.py           # JWT + password hashing helpers
│   ├── email_service.py  # SMTP email sending (confirmation & welcome)
│   ├── schemas.py        # Pydantic request/response models
│   ├── config.py         # Settings from environment variables
│   ├── requirements.txt
│   └── .env.example      # Copy to .env and fill in your values
├── client/               # Tkinter desktop client
│   ├── main.py           # Entry-point
│   ├── config.py         # Client config (API URL, Auth0 callback port)
│   ├── views/
│   │   ├── login.py      # Main window: email/password + social login buttons
│   │   └── register.py   # Registration dialog
│   ├── services/
│   │   ├── api_client.py # HTTP client for the FastAPI backend
│   │   └── auth0_client.py # Auth0 OAuth2 flow (opens browser, local callback server)
│   └── requirements.txt
├── tests/
│   └── test_api.py       # pytest tests for the API
└── pyproject.toml        # pytest configuration
```

---

## Quick Start

### 1 – Backend (FastAPI)

```bash
# Install dependencies
cd api/
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env – at minimum set SMTP_* and SECRET_KEY
# For social login set AUTH0_* values too

# Run the server (from repo root)
cd ..
uvicorn api.main:app --reload
# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 2 – Desktop Client (Tkinter)

```bash
pip install -r client/requirements.txt

# Run from repo root
python -m client.main
```

### 3 – Run Tests

```bash
pip install pytest
pytest tests/
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Create a new account (sends confirmation email) |
| `GET`  | `/auth/confirm/{token}` | Confirm email address (activates account, sends welcome email) |
| `POST` | `/auth/login` | Login with email + password (confirmed accounts only) |
| `GET`  | `/auth/social/url` | Get Auth0 authorization URL for social login |
| `GET`  | `/auth/social/callback` | Auth0 OAuth2 callback (exchange code → JWT) |
| `GET`  | `/healthz` | Liveness probe |

Full interactive documentation is available at `http://localhost:8000/docs` once the server is running.

---

## Configuration

All settings are read from environment variables (or a `.env` file placed next to `api/config.py`).

### API (`api/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./jarvis.db` | SQLAlchemy database URL |
| `SECRET_KEY` | *(must be set)* | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT lifetime |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port (STARTTLS) |
| `SMTP_USER` | | Sender email address |
| `SMTP_PASSWORD` | | Sender email password / app-password |
| `EMAILS_FROM_NAME` | `Jarvis Family` | Sender display name |
| `APP_HOST` | `http://localhost:8000` | Public base URL (used in confirmation links) |
| `AUTH0_DOMAIN` | | Auth0 tenant domain, e.g. `my-tenant.auth0.com` |
| `AUTH0_CLIENT_ID` | | Auth0 application client ID |
| `AUTH0_CLIENT_SECRET` | | Auth0 application client secret |
| `AUTH0_CALLBACK_URL` | `http://localhost:8000/auth/social/callback` | Must match Auth0 dashboard |

> **SMTP not configured?** The app still runs – email content is printed to the console log instead. This makes local development easy.

### Client (`client/.env` or environment)

| Variable | Default | Description |
|----------|---------|-------------|
| `API_BASE_URL` | `http://localhost:8000` | FastAPI backend URL |
| `AUTH0_CALLBACK_PORT` | `8080` | Local port for the OAuth callback server |

---

## Auth0 Social Login Setup

1. Go to [Auth0 Dashboard](https://manage.auth0.com) → Applications → **Create Application** (Regular Web Application).
2. In *Allowed Callback URLs* add `http://localhost:8000/auth/social/callback`.
3. Enable the desired social connections (Google, Apple, …) under *Authentication → Social*.
4. Copy **Domain**, **Client ID**, and **Client Secret** into `api/.env`.
5. Restart the API server.

The desktop client will open the system browser for the social login flow and automatically capture the callback.