import io
import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.test_booking_concurrency import _register

client = TestClient(app)

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _paid_booking(owner_h, renter_h):
    listing = client.post(
        "/api/v1/listings",
        headers=owner_h,
        json={
            "category_slug": "power-tools",
            "title": f"Condition {uuid.uuid4().hex[:4]}",
            "description": "Condition report test listing.",
            "condition": "good",
            "daily_price_cents": 10000,
            "deposit_cents": 0,
            "public_area_label": "Test",
            "latitude": 19.0,
            "longitude": 72.0,
        },
    )
    item_id = listing.json()["id"]
    req = client.post(
        f"/api/v1/listings/{item_id}/booking-requests",
        headers=renter_h,
        json={"start_date": "2028-03-01", "end_date": "2028-03-02"},
    )
    booking_id = req.json()["id"]
    client.post(f"/api/v1/rental-bookings/{booking_id}/accept", headers=owner_h, json={})
    intent = client.post(f"/api/v1/rental-bookings/{booking_id}/payment-intent", headers=renter_h).json()
    client.post(
        f"/api/v1/rental-bookings/{booking_id}/sandbox-pay",
        headers=renter_h,
        params={"payment_id": intent["payment_id"]},
    )
    return booking_id, owner_h, renter_h


def test_condition_report_immutable(seeded_db):
    _, owner_h = _register("CondOwner")
    _, renter_h = _register("CondRenter")
    booking_id, owner_h, renter_h = _paid_booking(owner_h, renter_h)

    files = {"photos": ("pickup.png", io.BytesIO(TINY_PNG), "image/png")}
    data = {"phase": "pickup", "notes": "Scratches on handle", "damage_notes": "Minor"}
    r1 = client.post(
        f"/api/v1/rental-bookings/{booking_id}/condition-reports",
        headers=owner_h,
        data=data,
        files=files,
    )
    assert r1.status_code == 201, r1.text
    r2 = client.post(
        f"/api/v1/rental-bookings/{booking_id}/condition-reports",
        headers=renter_h,
        data=data,
        files=files,
    )
    assert r2.status_code == 409

    ack = client.post(
        f"/api/v1/rental-bookings/{booking_id}/condition-reports/{r1.json()['id']}/acknowledge",
        headers=renter_h,
    )
    assert ack.status_code == 200
    assert ack.json()["renter_acknowledged_at"] is not None


def test_listing_photo_upload(seeded_db):
    _, owner_h = _register("PhotoOwner")
    listing = client.post(
        "/api/v1/listings",
        headers=owner_h,
        json={
            "category_slug": "power-tools",
            "title": "Photo listing",
            "description": "Has a listing photograph.",
            "condition": "good",
            "daily_price_cents": 10000,
            "deposit_cents": 0,
            "public_area_label": "Test",
            "latitude": 19.0,
            "longitude": 72.0,
        },
    )
    item_id = listing.json()["id"]
    up = client.post(
        f"/api/v1/listings/{item_id}/photos",
        headers=owner_h,
        files={"file": ("cover.png", io.BytesIO(TINY_PNG), "image/png")},
    )
    assert up.status_code == 201
    pub = client.get(f"/api/v1/listings/{item_id}")
    assert len(pub.json()["photo_urls"]) == 1