import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PaymentIntentOut(BaseModel):
    payment_id: uuid.UUID
    rental_booking_id: uuid.UUID | None = None
    service_job_id: uuid.UUID | None = None
    amount_cents: int
    currency: str
    status: str
    provider: str
    idempotency_key: str
    checkout_token: str


class PaymentOut(BaseModel):
    id: uuid.UUID
    rental_booking_id: uuid.UUID | None = None
    service_job_id: uuid.UUID | None = None
    amount_cents: int
    currency: str
    status: str
    provider: str
    succeeded_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentWebhookPayload(BaseModel):
    event_id: str = Field(min_length=8, max_length=128)
    event_type: str
    payment_id: uuid.UUID
    status: str