"""
FastAPI application – authentication routes.

Routes
------
POST /auth/register         – create a new user account (sends confirmation email)
GET  /auth/confirm/{token}  – confirm email (sends welcome email, enables login)
POST /auth/login            – email + password login (confirmed accounts only)
GET  /auth/social/url       – get Auth0 authorization URL for social login
GET  /auth/social/callback  – Auth0 OAuth2 callback (exchanges code for tokens)
GET  /healthz               – liveness probe
"""
import secrets
import urllib.parse
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from api import models, schemas
from api.auth import create_access_token, hash_password, verify_password
from api.config import (
    APP_HOST,
    AUTH0_AUDIENCE,
    AUTH0_CALLBACK_URL,
    AUTH0_CLIENT_ID,
    AUTH0_CLIENT_SECRET,
    AUTH0_DOMAIN,
)
from api.database import engine, get_db
from api.email_service import send_confirmation_email, send_welcome_email

# Create tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Jarvis Family Auth API",
    description="Authentication backend for the Jarvis Family Tkinter application.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok"}


# ── Registration ──────────────────────────────────────────────────────────────

@app.post(
    "/auth/register",
    response_model=schemas.RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
async def register(body: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user.  A confirmation email is sent immediately."""
    existing = db.query(models.User).filter(models.User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    token = secrets.token_urlsafe(32)
    user = models.User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        confirmation_token=token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    await send_confirmation_email(user.email, user.name, token, APP_HOST)

    return schemas.RegisterResponse(
        message="Registration successful. Please check your email to confirm your account.",
        email=user.email,
    )


# ── Email confirmation ────────────────────────────────────────────────────────

@app.get(
    "/auth/confirm/{token}",
    response_class=HTMLResponse,
    tags=["auth"],
)
async def confirm_email(token: str, db: Session = Depends(get_db)):
    """Validate the confirmation token and activate the user account."""
    user = db.query(models.User).filter(models.User.confirmation_token == token).first()
    if not user:
        return HTMLResponse(
            content=_html_page(
                "Invalid or Expired Link",
                "The confirmation link is invalid or has already been used.",
                success=False,
            ),
            status_code=400,
        )

    if user.is_confirmed:
        return HTMLResponse(
            content=_html_page(
                "Already Confirmed",
                f"The account for <strong>{user.email}</strong> is already confirmed. "
                "You can close this tab and log in.",
                success=True,
            )
        )

    user.is_confirmed = True
    user.confirmation_token = None
    db.commit()

    await send_welcome_email(user.email, user.name)

    return HTMLResponse(
        content=_html_page(
            "Email Confirmed!",
            f"Hello <strong>{user.name}</strong>! Your email has been confirmed. "
            "You can now close this tab and log in to Jarvis Family.",
            success=True,
        )
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@app.post(
    "/auth/login",
    response_model=schemas.TokenResponse,
    tags=["auth"],
)
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password.  Only confirmed accounts are allowed."""
    user = db.query(models.User).filter(models.User.email == body.email).first()

    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_confirmed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please confirm your email address before logging in.",
        )

    access_token = create_access_token({"sub": user.id, "email": user.email})
    return schemas.TokenResponse(
        access_token=access_token,
        name=user.name,
        email=user.email,
    )


# ── Social login (Auth0) ──────────────────────────────────────────────────────

@app.get(
    "/auth/social/url",
    response_model=schemas.SocialLoginUrlResponse,
    tags=["auth"],
)
def social_login_url(
    connection: Optional[str] = Query(
        None,
        description="Auth0 connection name, e.g. 'google-oauth2' or 'apple'",
    )
):
    """Return the Auth0 authorization URL to redirect the user's browser to."""
    if not AUTH0_DOMAIN or not AUTH0_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Social login is not configured (AUTH0_DOMAIN / AUTH0_CLIENT_ID missing).",
        )

    params: dict = {
        "response_type": "code",
        "client_id": AUTH0_CLIENT_ID,
        "redirect_uri": AUTH0_CALLBACK_URL,
        "scope": "openid profile email",
    }
    if AUTH0_AUDIENCE:
        params["audience"] = AUTH0_AUDIENCE
    if connection:
        params["connection"] = connection

    url = f"https://{AUTH0_DOMAIN}/authorize?" + urllib.parse.urlencode(params)
    return schemas.SocialLoginUrlResponse(authorization_url=url)


@app.get(
    "/auth/social/callback",
    response_model=schemas.TokenResponse,
    tags=["auth"],
)
async def social_callback(
    code: str = Query(..., description="Authorization code returned by Auth0"),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Exchange the Auth0 authorization code for tokens, upsert the user,
    and return our own JWT.
    """
    if not AUTH0_DOMAIN or not AUTH0_CLIENT_ID or not AUTH0_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Social login is not configured.",
        )

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            json={
                "grant_type": "authorization_code",
                "client_id": AUTH0_CLIENT_ID,
                "client_secret": AUTH0_CLIENT_SECRET,
                "code": code,
                "redirect_uri": AUTH0_CALLBACK_URL,
            },
        )

    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code with Auth0.",
        )

    token_data = token_resp.json()
    id_token = token_data.get("id_token", "")

    # Fetch user info from Auth0
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            f"https://{AUTH0_DOMAIN}/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )

    if userinfo_resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve user info from Auth0.",
        )

    userinfo = userinfo_resp.json()
    sub: str = userinfo["sub"]
    email: str = userinfo.get("email", "")
    name: str = userinfo.get("name", email)

    # Upsert the user
    user = db.query(models.User).filter(models.User.auth0_sub == sub).first()
    if not user:
        # Check if user exists by email (e.g. already registered with password)
        user = db.query(models.User).filter(models.User.email == email).first()
        if user:
            user.auth0_sub = sub
            user.is_confirmed = True
        else:
            user = models.User(
                name=name,
                email=email,
                auth0_sub=sub,
                is_confirmed=True,
            )
            db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token({"sub": user.id, "email": user.email})
    return schemas.TokenResponse(
        access_token=access_token,
        name=user.name,
        email=user.email,
    )


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _html_page(title: str, message: str, success: bool = True) -> str:
    color = "#4CAF50" if success else "#f44336"
    icon = "✅" if success else "❌"
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>{title} – Jarvis Family</title>
      <style>
        body {{font-family:Arial,sans-serif;display:flex;align-items:center;
              justify-content:center;min-height:100vh;margin:0;background:#f5f5f5;}}
        .card {{background:#fff;border-radius:8px;padding:40px;max-width:480px;
               text-align:center;box-shadow:0 2px 12px rgba(0,0,0,.1);}}
        .icon {{font-size:48px;}}
        h1 {{color:{color};}}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="icon">{icon}</div>
        <h1>{title}</h1>
        <p>{message}</p>
      </div>
    </body>
    </html>
    """
