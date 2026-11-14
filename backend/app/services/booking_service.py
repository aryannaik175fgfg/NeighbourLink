import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.item import Item, ItemStatus
from app.models.rental_booking import RentalBooking, RentalBookingStatus
from app.models.user import User
from app.schemas.bookings import BookingQuoteOut, BookingRequestCreate, RentalBookingOut
from app.core.config import settings
from app.services.availability_service import dates_are_available, get_item_or_404
from app.services.payment_service import expire_stale_holds
from app.services.listing_service import _lat_lng_from_item, item_to_public


def compute_quote(*, item: Item, start_date: date, end_date: date) -> BookingQuoteOut:
    rental_days = (end_date - start_date).days + 1
    if rental_days < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date range")
    if rental_days > 90:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum rental period is 90 days")

    subtotal = item.daily_price_cents * rental_days
    total = subtotal + item.deposit_cents
    return BookingQuoteOut(
        start_date=start_date,
        end_date=end_date,
        rental_days=rental_days,
        daily_price_cents=item.daily_price_cents,
        deposit_cents=item.deposit_cents,
        subtotal_cents=subtotal,
        total_cents=total,
    )


def request_booking(db: Session, user: User, item_id: uuid.UUID, data: BookingRequestCreate) -> RentalBooking:
    item = db.scalar(
        select(Item).where(Item.id == item_id).options(joinedload(Item.category), joinedload(Item.owner).joinedload(User.profile))
    )
    if item is None or item.status != ItemStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not available")
    if item.owner_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot rent your own listing")

    quote = compute_quote(item=item, start_date=data.start_date, end_date=data.end_date)
    dates_are_available(db, item_id=item_id, start_date=data.start_date, end_date=data.end_date)

    booking = RentalBooking(
        item_id=item_id,
        renter_id=user.id,
        start_date=data.start_date,
        end_date=data.end_date,
        status=RentalBookingStatus.REQUESTED,
        rental_days=quote.rental_days,
        daily_price_cents_snapshot=item.daily_price_cents,
        deposit_cents_snapshot=item.deposit_cents,
        subtotal_cents=quote.subtotal_cents,
        total_cents=quote.total_cents,
        renter_note=data.renter_note,
    )
    db.add(booking)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="These dates were just booked by someone else",
        ) from exc
    db.refresh(booking)
    return booking


def booking_to_out(
    db: Session,
    booking: RentalBooking,
    *,
    viewer: User,
    include_listing: bool = False,
) -> RentalBookingOut:
    item = db.scalar(
        select(Item).where(Item.id == booking.item_id).options(joinedload(Item.category), joinedload(Item.owner).joinedload(User.profile))
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Booking item missing")

    is_owner = item.owner_id == viewer.id
    renter = db.scalar(select(User).where(User.id == booking.renter_id).options(joinedload(User.profile)))

    listing = None
    if include_listing:
        lat, lng = _lat_lng_from_item(item, db)
        listing = item_to_public(
            item,
            owner_name=item.owner.profile.display_name,
            latitude=lat,
            longitude=lng,
        )

    from app.services import escrow_service as escrow_svc

    return RentalBookingOut(
        id=booking.id,
        item_id=booking.item_id,
        item_title=item.title,
        status=booking.status,
        deposit_escrow_status=escrow_svc.escrow_status_for_booking(db, booking.id),
        start_date=booking.start_date,
        end_date=booking.end_date,
        rental_days=booking.rental_days,
        subtotal_cents=booking.subtotal_cents,
        total_cents=booking.total_cents,
        deposit_cents_snapshot=booking.deposit_cents_snapshot,
        daily_price_cents_snapshot=booking.daily_price_cents_snapshot,
        renter_note=booking.renter_note,
        owner_note=booking.owner_note,
        created_at=booking.created_at,
        hold_expires_at=booking.hold_expires_at,
        paid_at=booking.paid_at,
        pickup_at=booking.pickup_at,
        return_at=booking.return_at,
        completed_at=booking.completed_at,
        is_owner_view=is_owner,
        renter_display_name=renter.profile.display_name if renter and is_owner else None,
        listing=listing,
    )


def list_renter_bookings(db: Session, user: User) -> list[RentalBooking]:
    expire_stale_holds(db)
    return list(
        db.scalars(
            select(RentalBooking)
            .where(RentalBooking.renter_id == user.id)
            .order_by(RentalBooking.created_at.desc())
        ).all()
    )


def list_owner_incoming(db: Session, user: User) -> list[RentalBooking]:
    expire_stale_holds(db)
    return list(
        db.scalars(
            select(RentalBooking)
            .join(Item, RentalBooking.item_id == Item.id)
            .where(Item.owner_id == user.id)
            .order_by(RentalBooking.created_at.desc())
        ).all()
    )


def get_booking(db: Session, booking_id: uuid.UUID) -> RentalBooking:
    booking = db.get(RentalBooking, booking_id)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking


def assert_booking_participant(db: Session, booking: RentalBooking, user: User) -> Item:
    item = get_item_or_404(db, booking.item_id)
    if booking.renter_id != user.id and item.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this booking")
    return item


def owner_accept(db: Session, user: User, booking_id: uuid.UUID, owner_note: str | None) -> RentalBooking:
    booking = get_booking(db, booking_id)
    item = get_item_or_404(db, booking.item_id)
    if item.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your listing")
    if booking.status != RentalBookingStatus.REQUESTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking is not awaiting your response")

    booking.status = RentalBookingStatus.AWAITING_PAYMENT
    booking.owner_note = owner_note
    booking.responded_at = datetime.now(UTC)
    booking.hold_expires_at = datetime.now(UTC) + timedelta(minutes=settings.payment_hold_minutes)
    db.add(booking)
    from app.services import notification_service as notify_svc

    from app.services.rental_message_service import ensure_rental_conversation

    ensure_rental_conversation(db, booking)
    notify_svc.emit(
        db,
        booking.renter_id,
        kind="rental_payment",
        title="Booking accepted — pay to confirm",
        body="The owner accepted your rental request. Complete payment before the hold expires.",
        link_path="/app/activity",
        dedupe_key=f"rental-awaiting-pay-{booking.id}",
    )
    db.commit()
    db.refresh(booking)
    return booking


def owner_decline(db: Session, user: User, booking_id: uuid.UUID, owner_note: str | None) -> RentalBooking:
    booking = get_booking(db, booking_id)
    item = get_item_or_404(db, booking.item_id)
    if item.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your listing")
    if booking.status != RentalBookingStatus.REQUESTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking is not awaiting your response")

    booking.status = RentalBookingStatus.DECLINED
    booking.owner_note = owner_note
    booking.responded_at = datetime.now(UTC)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def renter_cancel(db: Session, user: User, booking_id: uuid.UUID) -> RentalBooking:
    booking = get_booking(db, booking_id)
    if booking.renter_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your booking")
    if booking.status not in (RentalBookingStatus.REQUESTED, RentalBookingStatus.AWAITING_PAYMENT):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This booking cannot be cancelled")

    booking.status = RentalBookingStatus.CANCELLED
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def record_pickup(db: Session, user: User, booking_id: uuid.UUID) -> RentalBooking:
    booking = get_booking(db, booking_id)
    item = get_item_or_404(db, booking.item_id)
    if item.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can record pickup")
    if booking.status != RentalBookingStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking is not confirmed")

    booking.status = RentalBookingStatus.ACTIVE
    booking.pickup_at = datetime.now(UTC)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def record_return(db: Session, user: User, booking_id: uuid.UUID) -> RentalBooking:
    booking = get_booking(db, booking_id)
    item = get_item_or_404(db, booking.item_id)
    if item.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can record return")
    if booking.status != RentalBookingStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rental is not active")

    booking.status = RentalBookingStatus.RETURNED
    booking.return_at = datetime.now(UTC)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def confirm_completion(db: Session, user: User, booking_id: uuid.UUID) -> RentalBooking:
    booking = get_booking(db, booking_id)
    if booking.renter_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the renter can confirm completion")
    if booking.status != RentalBookingStatus.RETURNED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rental is not returned yet")

    booking.status = RentalBookingStatus.COMPLETED
    booking.completed_at = datetime.now(UTC)
    from app.services import escrow_service as escrow_svc

    escrow_svc.release_to_renter(db, booking, note="Deposit returned after successful rental completion")
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking