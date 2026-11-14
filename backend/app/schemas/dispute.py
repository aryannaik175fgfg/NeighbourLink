import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DisputeCreate(BaseModel):
    subject_type: str = Field(pattern=r"^(rental_booking|service_job)$")
    subject_id: uuid.UUID
    reason: str = Field(min_length=10, max_length=2000)


class DisputeOut(BaseModel):
    id: uuid.UUID
    subject_type: str
    subject_id: uuid.UUID
    opened_by: uuid.UUID
    reason: str
    status: str
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DisputeResolve(BaseModel):
    status: str = Field(pattern=r"^(under_review|resolved|closed)$")
    resolution_notes: str = Field(min_length=5, max_length=2000)
    deposit_outcome: str | None = Field(
        default=None,
        pattern=r"^(release_renter|release_owner)$",
        description="For rental disputes with a held deposit",
    )