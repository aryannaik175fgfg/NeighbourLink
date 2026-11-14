import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register(name: str) -> tuple[str, dict[str, str]]:
    email = f"{name}-{uuid.uuid4().hex[:8]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "long-secure-pass-123", "display_name": name},
    )
    assert res.status_code == 201
    token = res.json()["access_token"]
    return email, {"Authorization": f"Bearer {token}"}


def test_two_renters_same_dates_one_wins(seeded_db):
    _, owner_h = _register("Owner")
    _, renter_a = _register("RenterA")
    _, renter_b = _register("RenterB")

    listing = client.post(
        "/api/v1/listings",
        headers=owner_h,
        json={
            "category_slug": "power-tools",
            "title": "Exclusive drill",
            "description": "Only one person can book these dates.",
            "condition": "good",
            "daily_price_cents": 50000,
            "deposit_cents": 0,
            "public_area_label": "Test area",
            "latitude": 19.0,
            "longitude": 72.0,
        },
    )
    assert listing.status_code == 201
    item_id = listing.json()["id"]
    payload = {"start_date": "2026-12-10", "end_date": "2026-12-12"}

    def attempt(headers):
        return client.post(f"/api/v1/listings/{item_id}/booking-requests", headers=headers, json=payload)

    with ThreadPoolExecutor(max_workers=2) as pool:
        r1, r2 = list(pool.map(attempt, [renter_a, renter_b]))

    codes = sorted([r1.status_code, r2.status_code])
    assert codes == [201, 409], (r1.text, r2.text)


def test_owner_accept_moves_to_awaiting_payment(seeded_db):
    _, owner_h = _register("Owner2")
    _, renter_h = _register("RenterC")

    listing = client.post(
        "/api/v1/listings",
        headers=owner_h,
        json={
            "category_slug": "power-tools",
            "title": "Drill to accept",
            "description": "Booking flow test item for acceptance.",
            "condition": "good",
            "daily_price_cents": 40000,
            "deposit_cents": 10000,
            "public_area_label": "Test",
            "latitude": 19.0,
            "longitude": 72.0,
        },
    )
    item_id = listing.json()["id"]
    req = client.post(
        f"/api/v1/listings/{item_id}/booking-requests",
        headers=renter_h,
        json={"start_date": "2026-11-20", "end_date": "2026-11-22"},
    )
    assert req.status_code == 201
    booking_id = req.json()["id"]
    assert req.json()["status"] == "requested"

    accept = client.post(f"/api/v1/rental-bookings/{booking_id}/accept", headers=owner_h, json={})
    assert accept.status_code == 200
    assert accept.json()["status"] == "awaiting_payment"
    assert accept.json()["total_cents"] == 40000 * 3 + 10000