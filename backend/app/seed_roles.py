"""Seed default roles. Run: python -m app.seed_roles"""

import uuid

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.role import Role

DEFAULT_ROLES = [
    ("customer", "Customer / renter", "Discover items, book rentals, publish service requests"),
    ("item_owner", "Item owner", "Create and manage rental listings"),
    ("provider", "Independent service provider", "Offer local assistance services"),
    ("trainee", "Trainee", "Develop skills under supervision"),
    ("supervisor", "Supervisor", "Mentor trainees and endorse observed skills"),
    ("administrator", "Administrator", "Platform verification, moderation, and disputes"),
]


def main() -> None:
    db = SessionLocal()
    try:
        for slug, name, description in DEFAULT_ROLES:
            existing = db.scalar(select(Role).where(Role.slug == slug))
            if existing is None:
                db.add(Role(id=uuid.uuid4(), slug=slug, name=name, description=description))
        db.commit()
        print(f"Seeded {len(DEFAULT_ROLES)} roles.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
