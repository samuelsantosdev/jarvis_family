"""
Pydantic schemas for request/response validation.
"""
from typing import Optional

from pydantic import BaseModel, EmailStr


# ── Registration ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    message: str
    email: str


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    email: str


# ── Email confirmation ────────────────────────────────────────────────────────

class ConfirmResponse(BaseModel):
    message: str


# ── Social login (Auth0) ──────────────────────────────────────────────────────

class SocialLoginUrlResponse(BaseModel):
    authorization_url: str


class SocialCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


# ── Generic error ─────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str
