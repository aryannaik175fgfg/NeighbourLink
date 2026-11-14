import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.listings import ListingPublic


class DateRange(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def valid_range(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class AvailabilityBlockCreate(DateRange):
    note: str | None = Field(default=None, max_length=255)


class AvailabilityBlockOut(BaseModel):
    id: uuid.UUID
    start_date: date
    end_date: date
    note: str | None

    model_config = {"from_attributes": True}


class CalendarBusyRange(BaseModel):
    start_date: date
    end_date: date
    kind: str  # "booked" | "blocked"


class ItemAvailabilityOut(BaseModel):
    item_id: uuid.UUID
    blocks: list[AvailabilityBlockOut]
    busy: list[CalendarBusyRange]


class BookingRequestCreate(DateRange):
    renter_note: str | None = Field(default=None, max_length=500)


class BookingQuoteOut(BaseModel):
    start_date: date
    end_date: date
    rental_days: int
    daily_price_cents: int
    deposit_cents: int
    subtotal_cents: int
    total_cents: int


class RentalBookingOut(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    item_title: str
    status: str
    start_date: date
    end_date: date
    rental_days: int
    subtotal_cents: int
    total_cents: int
    deposit_cents_snapshot: int
    daily_price_cents_snapshot: int
    renter_note: str | None
    owner_note: str | None
    created_at: datetime
    hold_expires_at: datetime | None = None
    paid_at: datetime | None = None
    pickup_at: datetime | None = None
    return_at: datetime | None = None
    completed_at: datetime | None = None
    is_owner_view: bool = False
    renter_display_name: str | None = None
    listing: ListingPublic | None = None
    deposit_escrow_status: str | None = None

    model_config = {"from_attributes": True}


class BookingOwnerAction(BaseModel):
    owner_note: str | None = Field(default=None, max_length=500)