import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import grant_role_by_email
from tests.test_booking_concurrency import _register

client = TestClient(app)


def _complete_job_flow(customer_h, provider_h, request_id: str, offer_id: str) -> str:
    job = client.post(f"/api/v1/offers/{offer_id}/accept", headers=customer_h)
    assert job.status_code == 200
    job_id = job.json()["id"]
    intent = client.post(f"/api/v1/service-jobs/{job_id}/payment-intent", headers=customer_h)
    payment_id = intent.json()["payment_id"]
    client.post(f"/api/v1/service-jobs/{job_id}/sandbox-pay", headers=customer_h, params={"payment_id": payment_id})
    client.post(f"/api/v1/service-jobs/{job_id}/start", headers=provider_h)
    client.post(f"/api/v1/service-jobs/{job_id}/submit-completion", headers=provider_h)
    client.post(f"/api/v1/service-jobs/{job_id}/confirm-completion", headers=customer_h)
    return job_id


def test_regulated_skill_and_admin_approval(seeded_db):
    _, admin_h = _register("SkillAdmin")
    me = client.get("/api/v1/me", headers=admin_h)
    grant_role_by_email(me.json()["email"], "administrator")
    _, customer_h = _register("SkillCust")
    _, provider_h = _register("SkillProv")

    client.put(
        "/api/v1/me/provider-portfolio",
        headers=provider_h,
        json={
            "headline": "Licensed plumber",
            "introduction": "Certified for residential plumbing work.",
            "service_area_label": "Andheri",
            "latitude": 19.1136,
            "longitude": 72.8697,
            "category_slugs": ["plumbing"],
        },
    )
    cats = client.get("/api/v1/me/provider-portfolio/categories", headers=provider_h)
    assert cats.json()[0]["verification_status"] == "pending"

    req = client.post(
        "/api/v1/service-requests",
        headers=customer_h,
        json={
            "category_slug": "plumbing",
            "title": "Burst pipe",
            "description": "Water leaking in bathroom wall.",
            "service_area_label": "Andheri",
            "latitude": 19.1136,
            "longitude": 72.8697,
        },
    )
    request_id = req.json()["id"]
    blocked = client.post(
        f"/api/v1/service-requests/{request_id}/offers",
        headers=provider_h,
        json={"price_cents": 100000, "included_work": "Inspect and patch", "estimated_days": 1},
    )
    assert blocked.status_code == 403

    pending = client.get("/api/v1/admin/skill-verifications", headers=admin_h)
    assert pending.status_code == 200
    provider_id = client.get("/api/v1/me", headers=provider_h).json()["id"]
    row = next(r for r in pending.json() if r["portfolio_user_id"] == provider_id)

    approve = client.post(
        f"/api/v1/admin/skill-verifications/{row['portfolio_user_id']}/{row['category_id']}",
        headers=admin_h,
        json={"approve": True, "note": "Credential verified"},
    )
    assert approve.status_code == 200

    offer = client.post(
        f"/api/v1/service-requests/{request_id}/offers",
        headers=provider_h,
        json={"price_cents": 100000, "included_work": "Inspect and patch", "estimated_days": 1},
    )
    assert offer.status_code == 201


def test_review_and_messages(seeded_db):
    _, customer_h = _register("MsgCust")
    _, provider_h = _register("MsgProv")

    client.put(
        "/api/v1/me/provider-portfolio",
        headers=provider_h,
        json={
            "headline": "Helper",
            "introduction": "General neighbourhood jobs.",
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
            "title": "Shelf install",
            "description": "Mount two shelves in bedroom.",
            "service_area_label": "Bandra",
            "latitude": 19.06,
            "longitude": 72.83,
        },
    )
    request_id = req.json()["id"]
    offer = client.post(
        f"/api/v1/service-requests/{request_id}/offers",
        headers=provider_h,
        json={"price_cents": 80000, "included_work": "Drill and mount", "estimated_days": 1},
    )
    job_id = _complete_job_flow(customer_h, provider_h, request_id, offer.json()["id"])

    conv = client.get(f"/api/v1/service-jobs/{job_id}/conversation", headers=customer_h)
    assert conv.status_code == 200
    conv_id = conv.json()["id"]
    sent = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        headers=customer_h,
        json={"body": "Thanks — tools are in the hall cupboard."},
    )
    assert sent.status_code == 201

    review = client.post(
        f"/api/v1/service-jobs/{job_id}/review",
        headers=customer_h,
        json={"rating": 5, "comment": "Neat work, on time, would hire again."},
    )
    assert review.status_code == 201

    search = client.get("/api/v1/providers", params={"category": "general", "latitude": 19.06, "longitude": 72.83})
    assert search.status_code == 200
    match = next(p for p in search.json() if p["headline"] == "Helper")
    assert match["assistance_rating_count"] == 1
    assert match["assistance_rating"] == 5.0