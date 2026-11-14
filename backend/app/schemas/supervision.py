import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SupervisionRequestCreate(BaseModel):
    supervisor_email: EmailStr
    trainee_note: str | None = Field(default=None, max_length=500)


class SupervisionOut(BaseModel):
    id: uuid.UUID
    trainee_id: uuid.UUID
    supervisor_id: uuid.UUID
    trainee_name: str
    supervisor_name: str
    status: str
    trainee_note: str | None
    created_at: datetime
    responded_at: datetime | None


class SupervisionRespond(BaseModel):
    accept: bool


class EndorsementCreate(BaseModel):
    trainee_id: uuid.UUID
    category_slug: str | None = Field(default=None, max_length=64)
    note: str = Field(min_length=5, max_length=1000)


class EndorsementOut(BaseModel):
    id: uuid.UUID
    trainee_name: str
    category_name: str | None
    note: str
    created_at: datetime