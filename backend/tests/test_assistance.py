import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.test_booking_concurrency import _register

client = TestClient(app)


def test_assistance_offer_accept_one_job(seeded_db):
    _, customer_h = _register("SvcCustomer")
    _, provider_h = _register("SvcProvider")

    client.put(
        "/api/v1/me/provider-portfolio",
        headers=provider_h,
        json={
            "headline": "Local plumber",
            "introduction": "Ten years fixing leaks and taps in the neighbourhood.",
            "service_area_label": "Andheri",
            "latitude": 19.1136,
            "longitude": 72.8697,
            "category_slugs": ["general"],
        },
    )

    req = client.post(
        "/api/v1/service-requests",
        headers=customer_h,
        json={
            "category_slug": "general",
            "title": "Leaking kitchen tap",
            "description": "Steady drip under the sink, needs repair tomorrow if possible.",
            "service_area_label": "Andheri West",
            "latitude": 19.1136,
            "longitude": 72.8697,
            "budget_cents": 150000,
        },
    )
    assert req.status_code == 201
    request_id = req.json()["id"]

    offer = client.post(
        f"/api/v1/service-requests/{request_id}/offers",
        headers=provider_h,
        json={
            "price_cents": 120000,
            "included_work": "Replace washer and test",
            "excluded_work": "New tap unit",
            "estimated_days": 1,
        },
    )
    assert offer.status_code == 201
    offer_id = offer.json()["id"]

    job = client.post(f"/api/v1/offers/{offer_id}/accept", headers=customer_h)
    assert job.status_code == 200
    assert job.json()["status"] == "awaiting_payment"
    job_id = job.json()["id"]

    intent = client.post(f"/api/v1/service-jobs/{job_id}/payment-intent", headers=customer_h)
    assert intent.status_code == 200
    payment_id = intent.json()["payment_id"]
    paid = client.post(
        f"/api/v1/service-jobs/{job_id}/sandbox-pay",
        headers=customer_h,
        params={"payment_id": payment_id},
    )
    assert paid.status_code == 200

    jobs = client.get("/api/v1/me/service-jobs", headers=customer_h)
    row = next(j for j in jobs.json() if j["id"] == job_id)
    assert row["status"] == "confirmed"
    assert len(row["timeline"]) >= 2

    started = client.post(f"/api/v1/service-jobs/{job_id}/start", headers=provider_h)
    assert started.status_code == 200

    dup = client.post(f"/api/v1/offers/{offer_id}/accept", headers=customer_h)
    assert dup.status_code in (400, 404, 409)


def test_provider_search(seeded_db):
    _, provider_h = _register("MapProvider")
    client.put(
        "/api/v1/me/provider-portfolio",
        headers=provider_h,
        json={
            "headline": "Handyman",
            "introduction": "General repairs and odd jobs for nearby residents.",
            "service_area_label": "Bandra",
            "latitude": 19.0600,
            "longitude": 72.8300,
            "category_slugs": ["general"],
        },
    )
    res = client.get("/api/v1/providers", params={"latitude": 19.06, "longitude": 72.83, "radius_km": 30})
    assert res.status_code == 200
    assert any(p["headline"] == "Handyman" for p in res.json())
    match = next(p for p in res.json() if p["headline"] == "Handyman")
    assert match["assistance_rating_count"] >= 0