from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import grant_role_by_email
from tests.test_booking_concurrency import _register

client = TestClient(app)


def test_comments_reactions_moderation(seeded_db):
    _, author_h = _register("PostAuthor")
    _, reader_h = _register("PostReader")

    created = client.post(
        "/api/v1/community/posts",
        headers=author_h,
        json={
            "kind": "question",
            "title": "Anyone know a good electrician?",
            "body": "Need small wiring fix near Lokhandwala this week.",
            "area_label": "Andheri",
            "latitude": 19.13,
            "longitude": 72.83,
        },
    )
    assert created.status_code == 201
    post_id = created.json()["id"]

    react = client.post(
        f"/api/v1/community/posts/{post_id}/reactions",
        headers=reader_h,
        json={"reaction": "helpful"},
    )
    assert react.status_code == 200
    assert react.json()["helpful_count"] == 1

    comment = client.post(
        f"/api/v1/community/posts/{post_id}/comments",
        headers=reader_h,
        json={"body": "Try the assistance tab — saw good reviews."},
    )
    assert comment.status_code == 201

    detail = client.get(f"/api/v1/community/posts/{post_id}", headers=author_h)
    assert detail.status_code == 200
    assert len(detail.json()["comments"]) == 1
    assert detail.json()["comment_count"] >= 1

    _, admin_h = _register("CommAdmin")
    me = client.get("/api/v1/me", headers=admin_h)
    grant_role_by_email(me.json()["email"], "administrator")

    hidden = client.post(
        f"/api/v1/admin/community/posts/{post_id}/hide",
        headers=admin_h,
        json={"reason": "Contains contact info against policy."},
    )
    assert hidden.status_code == 200

    feed = client.get("/api/v1/community/posts", headers=reader_h)
    assert not any(p["id"] == post_id for p in feed.json())