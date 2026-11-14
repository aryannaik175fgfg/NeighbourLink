import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str
    body: str
    created_at: datetime
    is_mine: bool = False


class ConversationOut(BaseModel):
    id: uuid.UUID
    kind: str = "service_job"
    service_job_id: uuid.UUID | None = None
    rental_booking_id: uuid.UUID | None = None
    job_title: str
    job_status: str
    partner_name: str
    last_message_preview: str | None
    messages: list[MessageOut]