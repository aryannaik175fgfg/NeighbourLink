import json
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.services.payment_service import build_webhook_signature
from tests.test_booking_concurrency import _register

client = TestClient(app)


def _accept_flow(owner_h, renter_h):
    listing = client.post(
        "/api/v1/listings",
        headers=owner_h,
        json={
            "category_slug": "power-tools",
            "title": f"Pay test {uuid.uuid4().hex[:4]}",
            "description": "Payment sandbox integration test listing.",
            "condition": "good",
            "daily_price_cents": 10000,
            "deposit_cents": 5000,
            "public_area_label": "Test",
            "latitude": 19.0,
            "longitude": 72.0,
        },
    )
    item_id = listing.json()["id"]
    req = client.post(
        f"/api/v1/listings/{item_id}/booking-requests",
        headers=renter_h,
        json={"start_date": "2027-01-10", "end_date": "2027-01-11"},
    )
    booking_id = req.json()["id"]
    client.post(f"/api/v1/rental-bookings/{booking_id}/accept", headers=owner_h, json={})
    return booking_id, renter_h


def test_webhook_idempotent(seeded_db):
    _, owner_h = _register("PayOwner")
    _, renter_h = _register("PayRenter")
    booking_id, renter_h = _accept_flow(owner_h, renter_h)

    intent = client.post(f"/api/v1/rental-bookings/{booking_id}/payment-intent", headers=renter_h)
    assert intent.status_code == 200
    payment_id = intent.json()["payment_id"]

    payload = {
        "event_id": f"evt-{payment_id}",
        "event_type": "payment.succeeded",
        "payment_id": payment_id,
        "status": "succeeded",
    }
    body = json.dumps(payload).encode("utf-8")
    sig = build_webhook_signature(body)
    headers = {"X-NL-Signature": sig, "Content-Type": "application/json"}

    w1 = client.post("/api/v1/webhooks/payments", content=body, headers=headers)
    w2 = client.post("/api/v1/webhooks/payments", content=body, headers=headers)
    assert w1.status_code == 200
    assert w2.status_code == 200
    assert w1.json()["status"] == "succeeded"

    booking = client.get("/api/v1/me/rental-bookings", headers=renter_h)
    row = next(x for x in booking.json() if x["id"] == booking_id)
    assert row["status"] == "confirmed"


def test_sandbox_pay_and_lifecycle(seeded_db):
    _, owner_h = _register("LifeOwner")
    _, renter_h = _register("LifeRenter")
    booking_id, renter_h = _accept_flow(owner_h, renter_h)

    intent = client.post(f"/api/v1/rental-bookings/{booking_id}/payment-intent", headers=renter_h).json()
    pay = client.post(
        f"/api/v1/rental-bookings/{booking_id}/sandbox-pay",
        headers=renter_h,
        params={"payment_id": intent["payment_id"]},
    )
    assert pay.status_code == 200

    pickup = client.post(f"/api/v1/rental-bookings/{booking_id}/pickup", headers=owner_h)
    ret = client.post(f"/api/v1/rental-bookings/{booking_id}/return", headers=owner_h)
    done = client.post(f"/api/v1/rental-bookings/{booking_id}/complete", headers=renter_h)
    assert pickup.status_code == 200
    assert ret.status_code == 200
    assert done.status_code == 200
    assert done.json()["status"] == "completed"