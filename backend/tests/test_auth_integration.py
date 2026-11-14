import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
client = TestClient(app)


def _require_db(database_available: bool):
    if not database_available:
        pytest.skip("PostgreSQL not available (start Docker: docker compose up -d)")


def test_health(database_available: bool):
    _require_db(database_available)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_register_login_me_profile(seeded_db, database_available: bool):
    _require_db(database_available)
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    password = "long-secure-pass-123"

    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Test Neighbour"},
    )
    assert reg.status_code == 201, reg.text
    tokens = reg.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me = client.get("/api/v1/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert any(r["slug"] == "customer" for r in me.json()["roles"])

    patch = client.patch(
        "/api/v1/me/profile",
        headers=headers,
        json={"approximate_location": "Bandra West"},
    )
    assert patch.status_code == 200

    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200