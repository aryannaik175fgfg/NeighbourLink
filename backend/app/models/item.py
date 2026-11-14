import uuid
from datetime import datetime
from enum import StrEnum

from geoalchemy2 import Geography
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ItemCondition(StrEnum):
    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"


class ItemStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    INACTIVE = "inactive"


class Item(Base):
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rental_categories.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    condition: Mapped[str] = mapped_column(String(32), nullable=False)
    daily_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    deposit_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default=ItemStatus.ACTIVE, index=True, nullable=False)
    pickup_instructions: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    public_area_label: Mapped[str] = mapped_column(String(255), nullable=False)
    exact_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[object] = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="items")
    category: Mapped["RentalCategory"] = relationship(back_populates="items")
    availability_blocks: Mapped[list["ItemAvailabilityBlock"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["RentalBooking"]] = relationship(back_populates="item")
    photos: Mapped[list["ItemPhoto"]] = relationship(back_populates="item", cascade="all, delete-orphan")