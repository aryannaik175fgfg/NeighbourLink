"""Seed rental categories. Run: python -m app.seed_categories"""

import uuid

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.rental_category import RentalCategory

CATEGORIES = [
    ("cameras", "Cameras & photo", 10),
    ("power-tools", "Power tools", 20),
    ("audio", "Speakers & audio", 30),
    ("computing", "Laptops & accessories", 40),
    ("sports", "Sports equipment", 50),
    ("household", "Household equipment", 60),
    ("other", "Other", 99),
]


def main() -> None:
    db = SessionLocal()
    try:
        for slug, name, sort_order in CATEGORIES:
            existing = db.scalar(select(RentalCategory).where(RentalCategory.slug == slug))
            if existing is None:
                db.add(RentalCategory(id=uuid.uuid4(), slug=slug, name=name, sort_order=sort_order))
        db.commit()
        print(f"Seeded {len(CATEGORIES)} rental categories.")
    finally:
        db.close()


if __name__ == "__main__":
    main()