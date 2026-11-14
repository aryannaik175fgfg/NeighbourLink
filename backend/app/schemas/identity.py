import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class IdentitySubmit(BaseModel):
    document_type: str = Field(min_length=2, max_length=32, pattern=r"^(aadhaar|pan|passport|other)$")
    document_reference: str = Field(min_length=4, max_length=32, description="Last digits or masked reference only")
    user_note: str | None = Field(default=None, max_length=500)


class IdentityOut(BaseModel):
    user_id: uuid.UUID
    document_type: str
    document_reference: str
    user_note: str | None
    status: str
    admin_note: str | None
    submitted_at: datetime
    reviewed_at: datetime | None

    model_config = {"from_attributes": True}


class IdentityAdminRow(BaseModel):
    user_id: uuid.UUID
    display_name: str
    email: str
    document_type: str
    document_reference: str
    user_note: str | None
    status: str
    submitted_at: datetime


class IdentityDecision(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=500)