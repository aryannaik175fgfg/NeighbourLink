from fastapi.testclient import TestClient

from app.main import app
from tests.test_booking_concurrency import _register

client = TestClient(app)


def test_save_and_unsave_listing(seeded_db):
    _, owner_h = _register("WishOwner")
    _, buyer_h = _register("WishBuyer")

    listing = client.post(
        "/api/v1/listings",
        headers=owner_h,
        json={
            "category_slug": "power-tools",
            "title": "Wishlist drill",
            "description": "Cordless drill for weekend projects.",
            "condition": "good",
            "daily_price_cents": 80000,
            "deposit_cents": 200000,
            "public_area_label": "Bandra",
            "latitude": 19.06,
            "longitude": 72.83,
        },
    )
    assert listing.status_code == 201
    item_id = listing.json()["id"]

    save = client.put(f"/api/v1/me/wishlist/{item_id}", headers=buyer_h)
    assert save.status_code == 204

    ids = client.get("/api/v1/me/wishlist/ids", headers=buyer_h)
    assert item_id in [str(x) for x in ids.json()]

    mine = client.get("/api/v1/me/wishlist", headers=buyer_h)
    assert len(mine.json()) == 1

    unsave = client.delete(f"/api/v1/me/wishlist/{item_id}", headers=buyer_h)
    assert unsave.status_code == 204
    assert client.get("/api/v1/me/wishlist/ids", headers=buyer_h).json() == []