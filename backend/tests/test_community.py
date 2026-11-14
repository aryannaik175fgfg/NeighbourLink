from fastapi.testclient import TestClient

from app.main import app
from tests.test_booking_concurrency import _register

client = TestClient(app)


def test_create_and_list_community_post(seeded_db):
    _, headers = _register("NeighborBoard")

    created = client.post(
        "/api/v1/community/posts",
        headers=headers,
        json={
            "kind": "recommendation",
            "title": "Great drill owner on 12th Road",
            "body": "Borrowed a Bosch drill last week — owner was on time and item was as described.",
            "area_label": "Bandra West",
            "latitude": 19.06,
            "longitude": 72.83,
        },
    )
    assert created.status_code == 201
    assert created.json()["is_mine"] is True

    feed = client.get(
        "/api/v1/community/posts",
        headers=headers,
        params={"latitude": 19.06, "longitude": 72.83, "radius_km": 30},
    )
    assert feed.status_code == 200
    assert any(p["title"] == "Great drill owner on 12th Road" for p in feed.json())