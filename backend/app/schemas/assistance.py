import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ServiceCategoryOut(BaseModel):
    slug: str
    name: str
    requires_verification: bool = False

    model_config = {"from_attributes": True}


class ProviderCategoryOut(BaseModel):
    slug: str
    name: str
    verification_status: str

    model_config = {"from_attributes": True}


class AssistanceReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=5, max_length=2000)


class AssistanceReviewOut(BaseModel):
    rating: int
    comment: str
    created_at: datetime


class PortfolioCreate(BaseModel):
    headline: str = Field(min_length=3, max_length=160)
    introduction: str = Field(min_length=10, max_length=5000)
    service_area_label: str = Field(min_length=2, max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    category_slugs: list[str] = Field(min_length=1, max_length=10)


class ProviderPublic(BaseModel):
    user_id: uuid.UUID
    display_name: str
    headline: str
    introduction: str
    service_area_label: str
    latitude: float
    longitude: float
    categories: list[ServiceCategoryOut]
    assistance_rating: float | None = None
    assistance_rating_count: int = 0
    distance_meters: float | None = None


class ServiceRequestCreate(BaseModel):
    category_slug: str
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    service_area_label: str = Field(min_length=2, max_length=255)
    latitude: float
    longitude: float
    budget_cents: int | None = Field(default=None, ge=0)


class ServiceRequestOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    status: str
    service_area_label: str
    budget_cents: int | None
    category: ServiceCategoryOut
    offer_count: int = 0
    created_at: datetime


class OfferCreate(BaseModel):
    price_cents: int = Field(ge=100)
    included_work: str = Field(min_length=5, max_length=5000)
    excluded_work: str | None = Field(default=None, max_length=2000)
    estimated_days: int = Field(default=1, ge=1, le=90)


class OfferOut(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    provider_name: str
    price_cents: int
    included_work: str
    excluded_work: str | None
    estimated_days: int
    status: str
    created_at: datetime


class ServiceJobEventOut(BaseModel):
    event_type: str
    summary: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceJobOut(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    request_title: str
    status: str
    price_cents_snapshot: int
    included_work_snapshot: str
    provider_name: str
    customer_name: str
    is_provider_view: bool
    hold_expires_at: datetime | None = None
    paid_at: datetime | None = None
    started_at: datetime | None = None
    timeline: list[ServiceJobEventOut] = []
    conversation_id: uuid.UUID | None = None
    has_review: bool = False
    created_at: datetime