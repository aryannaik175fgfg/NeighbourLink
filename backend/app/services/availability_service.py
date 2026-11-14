import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.availability import ItemAvailabilityBlock
from app.models.item import Item, ItemStatus
from app.models.rental_booking import PROTECTED_BOOKING_STATUSES, RentalBooking
from app.models.user import User
from app.schemas.bookings import AvailabilityBlockCreate, CalendarBusyRange, ItemAvailabilityOut


def _ranges_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    return a_start <= b_end and b_start <= a_end


def get_item_or_404(db: Session, item_id: uuid.UUID) -> Item:
    item = db.scalar(select(Item).where(Item.id == item_id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return item


def assert_owner(user: User, item: Item) -> None:
    if item.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your listing")


def get_availability(db: Session, item_id: uuid.UUID) -> ItemAvailabilityOut:
    item = get_item_or_404(db, item_id)
    blocks = db.scalars(
        select(ItemAvailabilityBlock).where(ItemAvailabilityBlock.item_id == item_id).order_by(ItemAvailabilityBlock.start_date)
    ).all()

    bookings = db.scalars(
        select(RentalBooking).where(
            RentalBooking.item_id == item_id,
            RentalBooking.status.in_(tuple(PROTECTED_BOOKING_STATUSES)),
        )
    ).all()

    busy: list[CalendarBusyRange] = []
    for b in blocks:
        busy.append(CalendarBusyRange(start_date=b.start_date, end_date=b.end_date, kind="blocked"))
    for bk in bookings:
        busy.append(CalendarBusyRange(start_date=bk.start_date, end_date=bk.end_date, kind="booked"))

    from app.schemas.bookings import AvailabilityBlockOut

    return ItemAvailabilityOut(
        item_id=item.id,
        blocks=[AvailabilityBlockOut.model_validate(b) for b in blocks],
        busy=busy,
    )


def add_block(db: Session, user: User, item_id: uuid.UUID, data: AvailabilityBlockCreate) -> ItemAvailabilityBlock:
    item = get_item_or_404(db, item_id)
    assert_owner(user, item)
    if item.status != ItemStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Listing is not active")

    overlap_booking = db.scalar(
        select(RentalBooking).where(
            RentalBooking.item_id == item_id,
            RentalBooking.status.in_(tuple(PROTECTED_BOOKING_STATUSES)),
            RentalBooking.start_date <= data.end_date,
            RentalBooking.end_date >= data.start_date,
        )
    )
    if overlap_booking:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Range overlaps an active booking")

    block = ItemAvailabilityBlock(
        item_id=item_id,
        start_date=data.start_date,
        end_date=data.end_date,
        note=data.note,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


def delete_block(db: Session, user: User, item_id: uuid.UUID, block_id: uuid.UUID) -> None:
    item = get_item_or_404(db, item_id)
    assert_owner(user, item)
    block = db.scalar(select(ItemAvailabilityBlock).where(ItemAvailabilityBlock.id == block_id, ItemAvailabilityBlock.item_id == item_id))
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    db.delete(block)
    db.commit()


def dates_are_available(
    db: Session,
    *,
    item_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> None:
    block = db.scalar(
        select(ItemAvailabilityBlock).where(
            ItemAvailabilityBlock.item_id == item_id,
            ItemAvailabilityBlock.start_date <= end_date,
            ItemAvailabilityBlock.end_date >= start_date,
        )
    )
    if block:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Selected dates include blocked days")

    overlap = db.scalar(
        select(RentalBooking).where(
            RentalBooking.item_id == item_id,
            RentalBooking.status.in_(tuple(PROTECTED_BOOKING_STATUSES)),
            RentalBooking.start_date <= end_date,
            RentalBooking.end_date >= start_date,
        )
    )
    if overlap:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Selected dates are not available")