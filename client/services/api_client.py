"""
HTTP client that talks to the Jarvis Family FastAPI backend.
"""
from typing import Optional

import httpx

from client.config import API_BASE_URL


class APIClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._token: Optional[str] = None

    # ── Auth token ────────────────────────────────────────────────────────────

    @property
    def token(self) -> Optional[str]:
        return self._token

    @token.setter
    def token(self, value: Optional[str]) -> None:
        self._token = value

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, name: str, email: str, password: str) -> dict:
        """Register a new account.  Returns the JSON response or raises on error."""
        response = httpx.post(
            f"{self.base_url}/auth/register",
            json={"name": name, "email": email, "password": password},
            timeout=10,
        )
        if response.status_code == 201:
            return response.json()
        _raise(response)

    # ── Login ─────────────────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> dict:
        """Login and store the returned JWT.  Returns the user dict."""
        response = httpx.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            self._token = data["access_token"]
            return data
        _raise(response)

    # ── Social login ──────────────────────────────────────────────────────────

    def get_social_login_url(self, connection: Optional[str] = None) -> str:
        """Return the Auth0 authorization URL for a social login."""
        params = {}
        if connection:
            params["connection"] = connection
        response = httpx.get(
            f"{self.base_url}/auth/social/url",
            params=params,
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()["authorization_url"]
        _raise(response)


# ── Helper ────────────────────────────────────────────────────────────────────

def _raise(response: httpx.Response) -> None:
    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text
    raise APIError(detail, status_code=response.status_code)


class APIError(Exception):
    def __init__(self, detail: str, status_code: int = 0):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
