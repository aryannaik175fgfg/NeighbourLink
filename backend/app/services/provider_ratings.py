import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assistance import AssistanceReview


def provider_rating_aggregate(db: Session, provider_id: uuid.UUID) -> tuple[float | None, int]:
    row = db.execute(
        select(func.avg(AssistanceReview.rating), func.count())
        .select_from(AssistanceReview)
        .where(AssistanceReview.provider_id == provider_id)
    ).one()
    count = int(row[1] or 0)
    if count == 0:
        return None, 0
    return round(float(row[0]), 1), count