from fastapi.testclient import TestClient

from app.main import app
from tests.test_booking_concurrency import _register

client = TestClient(app)


def test_settings_and_password(seeded_db):
    email, headers = _register("SettingsUser")

    settings = client.get("/api/v1/me/settings", headers=headers)
    assert settings.status_code == 200
    assert settings.json()["notify_rentals"] is True

    patched = client.patch(
        "/api/v1/me/settings",
        headers=headers,
        json={
            "preferred_locale": "hi",
            "notify_messages": False,
            "default_latitude": 19.11,
            "default_longitude": 72.87,
            "default_radius_km": 15,
        },
    )
    assert patched.status_code == 200
    assert patched.json()["preferred_locale"] == "hi"
    assert patched.json()["notify_messages"] is False

    bad = client.post(
        "/api/v1/me/change-password",
        headers=headers,
        json={"current_password": "wrong", "new_password": "new-long-pass-99"},
    )
    assert bad.status_code == 400

    ok = client.post(
        "/api/v1/me/change-password",
        headers=headers,
        json={"current_password": "long-secure-pass-123", "new_password": "another-secure-pass-456"},
    )
    assert ok.status_code == 204

    login = client.post("/api/v1/auth/login", json={"email": email, "password": "another-secure-pass-456"})
    assert login.status_code == 200