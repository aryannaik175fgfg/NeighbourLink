import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.escrow import DepositEscrow, EscrowStatus
from app.models.payment import Payment, PaymentStatus
from app.models.rental_booking import RentalBooking


def try_create_hold(db: Session, booking: RentalBooking, payment: Payment) -> DepositEscrow | None:
    if payment.status != PaymentStatus.SUCCEEDED or booking.deposit_cents_snapshot <= 0:
        return None
    existing = db.scalar(select(DepositEscrow).where(DepositEscrow.rental_booking_id == booking.id))
    if existing:
        return existing
    hold = DepositEscrow(
        rental_booking_id=booking.id,
        payment_id=payment.id,
        amount_cents=booking.deposit_cents_snapshot,
        status=EscrowStatus.HELD,
    )
    db.add(hold)
    db.flush()
    return hold


def escrow_status_for_booking(db: Session, booking_id: uuid.UUID) -> str | None:
    row = db.scalar(select(DepositEscrow).where(DepositEscrow.rental_booking_id == booking_id))
    return row.status if row else None


def release_to_renter(db: Session, booking: RentalBooking, *, note: str) -> DepositEscrow | None:
    hold = db.scalar(select(DepositEscrow).where(DepositEscrow.rental_booking_id == booking.id))
    if hold is None or hold.status != EscrowStatus.HELD:
        return hold
    hold.status = EscrowStatus.RELEASED_TO_RENTER
    hold.settlement_note = note
    hold.settled_at = datetime.now(UTC)
    db.add(hold)
    return hold


def release_to_owner(db: Session, booking: RentalBooking, *, note: str) -> DepositEscrow | None:
    hold = db.scalar(select(DepositEscrow).where(DepositEscrow.rental_booking_id == booking.id))
    if hold is None or hold.status != EscrowStatus.HELD:
        return hold
    hold.status = EscrowStatus.RELEASED_TO_OWNER
    hold.settlement_note = note
    hold.settled_at = datetime.now(UTC)
    db.add(hold)
    return hold