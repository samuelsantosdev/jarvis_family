"""
Configuration settings loaded from environment variables or defaults.
Copy .env.example to .env and fill in the values before running.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./jarvis.db")

# ── JWT ───────────────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-use-a-long-random-string")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# ── Email (SMTP) ──────────────────────────────────────────────────────────────
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME", "Jarvis Family")
EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", SMTP_USER)

# ── Application ───────────────────────────────────────────────────────────────
APP_HOST: str = os.getenv("APP_HOST", "http://localhost:8000")
FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:8000")

# ── Auth0 ─────────────────────────────────────────────────────────────────────
AUTH0_DOMAIN: str = os.getenv("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID: str = os.getenv("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET: str = os.getenv("AUTH0_CLIENT_SECRET", "")
AUTH0_AUDIENCE: str = os.getenv("AUTH0_AUDIENCE", "")
AUTH0_CALLBACK_URL: str = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:8000/auth/social/callback")
