import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SkillVerificationOut(BaseModel):
    portfolio_user_id: uuid.UUID
    category_id: uuid.UUID
    category_slug: str
    category_name: str
    provider_name: str
    provider_headline: str
    verification_status: str
    admin_note: str | None
    reviewed_at: datetime | None


class SkillVerificationDecision(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=1000)