from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import grant_role_by_email
from tests.test_booking_concurrency import _register

client = TestClient(app)


def test_identity_dispute_audit(seeded_db):
    email, headers = _register("Phase7User")
    me = client.get("/api/v1/me", headers=headers)
    grant_role_by_email(me.json()["email"], "administrator")
    admin_login = client.post(
        "/api/v1/auth/login", json={"email": me.json()["email"], "password": "long-secure-pass-123"}
    )
    admin_h = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    ident = client.post(
        "/api/v1/me/identity",
        headers=headers,
        json={"document_type": "pan", "document_reference": "XXXX1234", "user_note": "Legal name matches profile"},
    )
    assert ident.status_code == 201

    queue = client.get("/api/v1/admin/identity-verifications", headers=admin_h)
    assert queue.status_code == 200
    assert len(queue.json()) >= 1

    user_id = ident.json()["user_id"]
    decided = client.post(
        f"/api/v1/admin/identity-verifications/{user_id}",
        headers=admin_h,
        json={"approve": True, "note": "Documents OK"},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "approved"

    _, owner_h = _register("DisputeOwner")
    _, renter_h = _register("DisputeRenter")

    listing = client.post(
        "/api/v1/listings",
        headers=owner_h,
        json={
            "category_slug": "power-tools",
            "title": "Dispute drill",
            "description": "Test item for dispute flow with enough text here.",
            "condition": "good",
            "daily_price_cents": 50000,
            "deposit_cents": 100000,
            "public_area_label": "Test area",
            "latitude": 19.11,
            "longitude": 72.87,
        },
    )
    assert listing.status_code == 201
    item_id = listing.json()["id"]

    booking = client.post(
        f"/api/v1/listings/{item_id}/booking-requests",
        headers=renter_h,
        json={"start_date": "2026-12-01", "end_date": "2026-12-03", "renter_note": "Need it"},
    )
    assert booking.status_code == 201
    booking_id = booking.json()["id"]

    dispute = client.post(
        "/api/v1/disputes",
        headers=renter_h,
        json={
            "subject_type": "rental_booking",
            "subject_id": booking_id,
            "reason": "Item was not as described when I tried to pick it up.",
        },
    )
    assert dispute.status_code == 201

    admin_disputes = client.get("/api/v1/admin/disputes", headers=admin_h)
    assert admin_disputes.status_code == 200
    dispute_id = dispute.json()["id"]

    resolved = client.patch(
        f"/api/v1/admin/disputes/{dispute_id}",
        headers=admin_h,
        json={"status": "resolved", "resolution_notes": "Deposit refunded per policy."},
    )
    assert resolved.status_code == 200

    audit = client.get("/api/v1/admin/audit-log", headers=admin_h)
    assert audit.status_code == 200
    assert len(audit.json()) >= 2


def test_ready_endpoint(seeded_db):
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json()["database"] == "ok"