import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RentalBookingStatus(StrEnum):
    REQUESTED = "requested"
    AWAITING_PAYMENT = "awaiting_payment"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    RETURNED = "returned"
    COMPLETED = "completed"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    DISPUTED = "disputed"


PROTECTED_BOOKING_STATUSES = frozenset(
    {
        RentalBookingStatus.REQUESTED,
        RentalBookingStatus.AWAITING_PAYMENT,
        RentalBookingStatus.CONFIRMED,
        RentalBookingStatus.ACTIVE,
    }
)


class RentalBooking(Base):
    __tablename__ = "rental_bookings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("items.id", ondelete="CASCADE"), index=True, nullable=False
    )
    renter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=RentalBookingStatus.REQUESTED, index=True, nullable=False)
    rental_days: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_price_cents_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    deposit_cents_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    renter_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    return_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    item: Mapped["Item"] = relationship(back_populates="bookings")
    renter: Mapped["User"] = relationship(foreign_keys=[renter_id])
    payments: Mapped[list["Payment"]] = relationship(back_populates="booking")
    condition_reports: Mapped[list["RentalConditionReport"]] = relationship(back_populates="booking")
    conversation: Mapped["RentalConversation | None"] = relationship(back_populates="booking", uselist=False)
    deposit_escrow: Mapped["DepositEscrow | None"] = relationship(back_populates="booking", uselist=False)