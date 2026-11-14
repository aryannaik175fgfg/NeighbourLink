"""Seed service categories. Run: python -m app.seed_service_categories"""

import uuid

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.assistance import ServiceCategory

REGULATED = frozenset({"plumbing", "electrical"})

CATEGORIES = [
    ("plumbing", "Plumbing", 10),
    ("electrical", "Electrical", 20),
    ("cleaning", "Cleaning", 30),
    ("furniture-assembly", "Furniture assembly", 40),
    ("appliance-repair", "Appliance repair", 50),
    ("gardening", "Gardening", 60),
    ("general", "General help", 99),
]


def main() -> None:
    db = SessionLocal()
    try:
        for slug, name, sort_order in CATEGORIES:
            existing = db.scalar(select(ServiceCategory).where(ServiceCategory.slug == slug))
            if existing is None:
                db.add(
                    ServiceCategory(
                        id=uuid.uuid4(),
                        slug=slug,
                        name=name,
                        sort_order=sort_order,
                        requires_verification=slug in REGULATED,
                    )
                )
            else:
                existing.requires_verification = slug in REGULATED
        db.commit()
        print(f"Seeded {len(CATEGORIES)} service categories.")
    finally:
        db.close()


if __name__ == "__main__":
    main()