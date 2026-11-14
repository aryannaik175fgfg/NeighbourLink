from fastapi.testclient import TestClient

from app.main import app
from tests.test_booking_concurrency import _register

client = TestClient(app)


def test_notification_on_message(seeded_db):
    _, customer_h = _register("NotifCust")
    _, provider_h = _register("NotifProv")

    client.put(
        "/api/v1/me/provider-portfolio",
        headers=provider_h,
        json={
            "headline": "Helper",
            "introduction": "General help.",
            "service_area_label": "Bandra",
            "latitude": 19.06,
            "longitude": 72.83,
            "category_slugs": ["general"],
        },
    )
    req = client.post(
        "/api/v1/service-requests",
        headers=customer_h,
        json={
            "category_slug": "general",
            "title": "Shelf",
            "description": "Install shelf",
            "service_area_label": "Bandra",
            "latitude": 19.06,
            "longitude": 72.83,
        },
    )
    request_id = req.json()["id"]
    offer = client.post(
        f"/api/v1/service-requests/{request_id}/offers",
        headers=provider_h,
        json={"price_cents": 50000, "included_work": "Install", "estimated_days": 1},
    )
    job = client.post(f"/api/v1/offers/{offer.json()['id']}/accept", headers=customer_h)
    job_id = job.json()["id"]

    unread = client.get("/api/v1/me/notifications/unread-count", headers=customer_h)
    assert unread.json()["count"] >= 1

    conv = client.get(f"/api/v1/service-jobs/{job_id}/conversation", headers=customer_h)
    conv_id = conv.json()["id"]
    client.post(f"/api/v1/conversations/{conv_id}/messages", headers=customer_h, json={"body": "Keys under mat"})

    provider_unread = client.get("/api/v1/me/notifications/unread-count", headers=provider_h)
    assert provider_unread.json()["count"] >= 1

    items = client.get("/api/v1/me/notifications", headers=provider_h)
    assert any(n["kind"] == "message" for n in items.json())