import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RoleOut(BaseModel):
    slug: str
    name: str

    model_config = {"from_attributes": True}


class ProfileOut(BaseModel):
    display_name: str
    bio: str | None = None
    phone: str | None = None
    preferred_locale: str
    approximate_location: str | None = None

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    bio: str | None = Field(default=None, max_length=1000)
    phone: str | None = Field(default=None, max_length=32)
    preferred_locale: str | None = Field(default=None, pattern=r"^(en|hi|mr)$")
    approximate_location: str | None = Field(default=None, max_length=255)


class MeResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    created_at: datetime
    profile: ProfileOut
    roles: list[RoleOut]

    model_config = {"from_attributes": True}
