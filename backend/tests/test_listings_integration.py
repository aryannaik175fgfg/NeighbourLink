import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_and_search_listing(seeded_db, database_available: bool):
    if not database_available:
        pytest.skip("PostgreSQL not available")

    email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "long-secure-pass-123", "display_name": "Owner"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    h = _headers(token)

    create = client.post(
        "/api/v1/listings",
        headers=h,
        json={
            "category_slug": "power-tools",
            "title": "Cordless drill kit",
            "description": "18V drill with bits and case. Good for quick home jobs.",
            "condition": "good",
            "daily_price_cents": 35000,
            "deposit_cents": 50000,
            "public_area_label": "Andheri East, Mumbai",
            "exact_address": "Private address line",
            "latitude": 19.1136,
            "longitude": 72.8697,
            "pickup_instructions": "Message before pickup.",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["title"] == "Cordless drill kit"
    assert body.get("exact_address") == "Private address line"

    public = client.get(f"/api/v1/listings/{body['id']}")
    assert public.status_code == 200
    pub = public.json()
    assert "exact_address" not in pub

    search = client.get(
        "/api/v1/listings",
        params={"q": "drill", "latitude": 19.1136, "longitude": 72.8697, "radius_km": 50},
    )
    assert search.status_code == 200
    assert any(x["id"] == body["id"] for x in search.json())

    me_roles = client.get("/api/v1/me", headers=h)
    assert any(r["slug"] == "item_owner" for r in me_roles.json()["roles"])