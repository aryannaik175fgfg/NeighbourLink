import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConditionPhotoOut(BaseModel):
    id: uuid.UUID
    original_filename: str
    content_type: str
    url: str

    model_config = {"from_attributes": True}


class ConditionReportOut(BaseModel):
    id: uuid.UUID
    rental_booking_id: uuid.UUID
    phase: str
    notes: str | None
    damage_notes: str | None
    created_at: datetime
    owner_acknowledged_at: datetime | None
    renter_acknowledged_at: datetime | None
    photos: list[ConditionPhotoOut]


class ItemPhotoOut(BaseModel):
    id: uuid.UUID
    url: str
    sort_order: int
    original_filename: str