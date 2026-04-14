"""
API integration tests using FastAPI TestClient (no real SMTP / Auth0 needed).

Run with:
    cd /path/to/jarvis_family
    pytest tests/
"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.database import Base, get_db
from api.main import app

# ── In-memory SQLite for tests ────────────────────────────────────────────────
# StaticPool ensures all connections share the same in-memory database instance.
TEST_DATABASE_URL = "sqlite://"

_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def override_get_db():
    db = _TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def client():
    return TestClient(app)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register(client, name="Alice", email="alice@example.com", password="secret123"):
    with patch(
        "api.main.send_confirmation_email",
        new_callable=AsyncMock,
    ) as mock_mail:
        resp = client.post("/auth/register", json={"name": name, "email": email, "password": password})
        return resp, mock_mail


def _confirm_token(client, token: str):
    """Follow the confirmation link."""
    return client.get(f"/auth/confirm/{token}", follow_redirects=True)


# ── Tests: health ─────────────────────────────────────────────────────────────


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── Tests: registration ───────────────────────────────────────────────────────


def test_register_success(client):
    resp, mock_mail = _register(client)
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert "message" in data
    mock_mail.assert_called_once()


def test_register_duplicate_email(client):
    _register(client)
    resp, _ = _register(client)
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"].lower()


def test_register_missing_fields(client):
    resp = client.post("/auth/register", json={"name": "Bob", "email": "bob@example.com"})
    assert resp.status_code == 422  # validation error


# ── Tests: email confirmation ─────────────────────────────────────────────────


def test_confirm_email_success(client):
    _register(client)

    # Retrieve the token directly from the DB
    db = _TestingSessionLocal()
    from api.models import User
    user = db.query(User).filter(User.email == "alice@example.com").first()
    token = user.confirmation_token
    db.close()

    with patch("api.main.send_welcome_email", new_callable=AsyncMock) as mock_welcome:
        resp = client.get(f"/auth/confirm/{token}")

    assert resp.status_code == 200
    assert "confirmed" in resp.text.lower()
    mock_welcome.assert_called_once()


def test_confirm_email_invalid_token(client):
    resp = client.get("/auth/confirm/totally-invalid-token")
    assert resp.status_code == 400
    assert "invalid" in resp.text.lower()


def test_confirm_email_already_confirmed(client):
    _register(client)

    db = _TestingSessionLocal()
    from api.models import User
    user = db.query(User).filter(User.email == "alice@example.com").first()
    token = user.confirmation_token
    db.close()

    # First confirmation
    with patch("api.main.send_welcome_email", new_callable=AsyncMock):
        client.get(f"/auth/confirm/{token}")

    # Second confirmation (token is now None)
    resp = client.get(f"/auth/confirm/{token}")
    assert resp.status_code == 400  # token no longer exists


# ── Tests: login ──────────────────────────────────────────────────────────────


def test_login_unconfirmed_account(client):
    _register(client)
    resp = client.post("/auth/login", json={"email": "alice@example.com", "password": "secret123"})
    assert resp.status_code == 403
    assert "confirm" in resp.json()["detail"].lower()


def test_login_success(client):
    _register(client)

    db = _TestingSessionLocal()
    from api.models import User
    user = db.query(User).filter(User.email == "alice@example.com").first()
    token = user.confirmation_token
    db.close()

    with patch("api.main.send_welcome_email", new_callable=AsyncMock):
        client.get(f"/auth/confirm/{token}")

    resp = client.post("/auth/login", json={"email": "alice@example.com", "password": "secret123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == "alice@example.com"


def test_login_wrong_password(client):
    _register(client)

    db = _TestingSessionLocal()
    from api.models import User
    user = db.query(User).filter(User.email == "alice@example.com").first()
    token = user.confirmation_token
    db.close()

    with patch("api.main.send_welcome_email", new_callable=AsyncMock):
        client.get(f"/auth/confirm/{token}")

    resp = client.post("/auth/login", json={"email": "alice@example.com", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post("/auth/login", json={"email": "nobody@example.com", "password": "pass"})
    assert resp.status_code == 401


# ── Tests: social login URL (Auth0 not configured) ────────────────────────────


def test_social_url_not_configured(client):
    resp = client.get("/auth/social/url")
    assert resp.status_code == 501  # Not Implemented
