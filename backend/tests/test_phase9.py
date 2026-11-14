from fastapi.testclient import TestClient

from app.main import app
from tests.test_booking_concurrency import _register

client = TestClient(app)


def test_deposit_escrow_lifecycle(seeded_db):
    _, owner_h = _register("EscrowOwner")
    _, renter_h = _register("EscrowRenter")

    listing = client.post(
        "/api/v1/listings",
        headers=owner_h,
        json={
            "category_slug": "power-tools",
            "title": "Escrow drill",
            "description": "Deposit escrow test item.",
            "condition": "good",
            "daily_price_cents": 50000,
            "deposit_cents": 250000,
            "public_area_label": "Test",
            "latitude": 19.0,
            "longitude": 72.0,
        },
    )
    item_id = listing.json()["id"]
    booking = client.post(
        f"/api/v1/listings/{item_id}/booking-requests",
        headers=renter_h,
        json={"start_date": "2026-11-20", "end_date": "2026-11-22"},
    )
    booking_id = booking.json()["id"]

    client.post(f"/api/v1/rental-bookings/{booking_id}/accept", headers=owner_h, json={})

    intent = client.post(f"/api/v1/rental-bookings/{booking_id}/payment-intent", headers=renter_h)
    pay = client.post(
        f"/api/v1/rental-bookings/{booking_id}/sandbox-pay",
        headers=renter_h,
        params={"payment_id": intent.json()["payment_id"]},
    )
    assert pay.status_code == 200

    mine = client.get("/api/v1/me/rental-bookings", headers=renter_h)
    row = next(b for b in mine.json() if b["id"] == booking_id)
    assert row["deposit_escrow_status"] == "held"

    client.post(f"/api/v1/rental-bookings/{booking_id}/pickup", headers=owner_h)
    client.post(f"/api/v1/rental-bookings/{booking_id}/return", headers=owner_h)
    client.post(f"/api/v1/rental-bookings/{booking_id}/complete", headers=renter_h)

    mine = client.get("/api/v1/me/rental-bookings", headers=renter_h)
    row = next(b for b in mine.json() if b["id"] == booking_id)
    assert row["deposit_escrow_status"] == "released_to_renter"