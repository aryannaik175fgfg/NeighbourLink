import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class ItemConditionEnum(StrEnum):
    new = "new"
    like_new = "like_new"
    good = "good"
    fair = "fair"


class ListingCreate(BaseModel):
    category_slug: str
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    condition: ItemConditionEnum
    daily_price_cents: int = Field(ge=100, le=50_000_000)
    deposit_cents: int = Field(default=0, ge=0, le=50_000_000)
    public_area_label: str = Field(min_length=2, max_length=255)
    exact_address: str | None = Field(default=None, max_length=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    pickup_instructions: str | None = Field(default=None, max_length=2000)


class ListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    condition: ItemConditionEnum | None = None
    daily_price_cents: int | None = Field(default=None, ge=100, le=50_000_000)
    deposit_cents: int | None = Field(default=None, ge=0, le=50_000_000)
    public_area_label: str | None = Field(default=None, min_length=2, max_length=255)
    exact_address: str | None = Field(default=None, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    pickup_instructions: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern=r"^(active|paused|inactive)$")


class CategoryOut(BaseModel):
    slug: str
    name: str

    model_config = {"from_attributes": True}


class ListingPublic(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    condition: str
    daily_price_cents: int
    deposit_cents: int
    status: str
    public_area_label: str
    category: CategoryOut
    owner_display_name: str
    latitude: float
    longitude: float
    distance_meters: float | None = None
    created_at: datetime
    photo_urls: list[str] = []


class ListingOwner(ListingPublic):
    exact_address: str | None
    pickup_instructions: str | None


class ListingSearchParams(BaseModel):
    q: str | None = None
    category: str | None = None
    min_price_cents: int | None = Field(default=None, ge=0)
    max_price_cents: int | None = Field(default=None, ge=0)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float | None = Field(default=25, ge=0.5, le=200)
    sort: str = Field(default="relevance", pattern=r"^(relevance|price_asc|price_desc|distance)$")

    @field_validator("max_price_cents")
    @classmethod
    def max_gte_min(cls, v: int | None, info):
        min_p = info.data.get("min_price_cents")
        if v is not None and min_p is not None and v < min_p:
            raise ValueError("max_price_cents must be >= min_price_cents")
        return v