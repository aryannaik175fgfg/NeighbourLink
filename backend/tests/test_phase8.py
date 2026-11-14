from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import grant_role_by_email
from tests.test_booking_concurrency import _register

client = TestClient(app)


def test_rental_messages_and_supervision(seeded_db):
    _, owner_h = _register("RentalMsgOwner")
    _, renter_h = _register("RentalMsgRenter")

    listing = client.post(
        "/api/v1/listings",
        headers=owner_h,
        json={
            "category_slug": "power-tools",
            "title": "Message test drill",
            "description": "For rental conversation tests.",
            "condition": "good",
            "daily_price_cents": 50000,
            "deposit_cents": 0,
            "public_area_label": "Test",
            "latitude": 19.0,
            "longitude": 72.0,
        },
    )
    item_id = listing.json()["id"]
    booking = client.post(
        f"/api/v1/listings/{item_id}/booking-requests",
        headers=renter_h,
        json={"start_date": "2026-12-20", "end_date": "2026-12-22"},
    )
    booking_id = booking.json()["id"]

    client.post(
        f"/api/v1/rental-bookings/{booking_id}/accept",
        headers=owner_h,
        json={"owner_note": "OK"},
    )

    conv = client.get(f"/api/v1/rental-bookings/{booking_id}/conversation", headers=renter_h)
    assert conv.status_code == 200
    conv_id = conv.json()["id"]
    assert conv.json()["kind"] == "rental_booking"

    sent = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=renter_h,
        json={"body": "What time is pickup?"},
    )
    assert sent.status_code == 201

    threads = client.get("/api/v1/me/conversations", headers=owner_h)
    assert any(t["id"] == conv_id for t in threads.json())

    _, trainee_h = _register("TraineeA")
    _, supervisor_h = _register("SupervisorB")
    sup_me = client.get("/api/v1/me", headers=supervisor_h)
    grant_role_by_email(sup_me.json()["email"], "supervisor")

    client.post("/api/v1/me/supervision/trainee/enroll", headers=trainee_h)
    sup_email = sup_me.json()["email"]
    req = client.post(
        "/api/v1/me/supervision/request",
        headers=trainee_h,
        json={"supervisor_email": sup_email, "trainee_note": "Learning wiring basics"},
    )
    assert req.status_code == 201
    rel_id = req.json()["id"]

    accepted = client.post(
        f"/api/v1/me/supervision/requests/{rel_id}",
        headers=supervisor_h,
        json={"accept": True},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "active"

    sessions = client.get("/api/v1/me/sessions", headers=trainee_h)
    assert sessions.status_code == 200
    assert len(sessions.json()) >= 1