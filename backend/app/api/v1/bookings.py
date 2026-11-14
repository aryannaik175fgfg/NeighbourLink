import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.schemas.bookings import (
    AvailabilityBlockCreate,
    AvailabilityBlockOut,
    BookingOwnerAction,
    BookingQuoteOut,
    BookingRequestCreate,
    ItemAvailabilityOut,
    RentalBookingOut,
)
from app.services import availability_service as avail_svc
from app.services import booking_service as book_svc

router = APIRouter(tags=["bookings"])


@router.get("/listings/{item_id}/availability", response_model=ItemAvailabilityOut)
def listing_availability(item_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> ItemAvailabilityOut:
    return avail_svc.get_availability(db, item_id)


@router.post("/listings/{item_id}/availability/blocks", response_model=AvailabilityBlockOut, status_code=201)
def create_availability_block(
    item_id: uuid.UUID,
    body: AvailabilityBlockCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> AvailabilityBlockOut:
    block = avail_svc.add_block(db, user, item_id, body)
    return AvailabilityBlockOut.model_validate(block)


@router.delete("/listings/{item_id}/availability/blocks/{block_id}", status_code=204)
def delete_availability_block(
    item_id: uuid.UUID,
    block_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    avail_svc.delete_block(db, user, item_id, block_id)


@router.get("/listings/{item_id}/booking-quote", response_model=BookingQuoteOut)
def booking_quote(
    item_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
) -> BookingQuoteOut:
    item = avail_svc.get_item_or_404(db, item_id)
    if item.status != "active":
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not available")
    return book_svc.compute_quote(item=item, start_date=start_date, end_date=end_date)


@router.post("/listings/{item_id}/booking-requests", response_model=RentalBookingOut, status_code=201)
def create_booking_request(
    item_id: uuid.UUID,
    body: BookingRequestCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> RentalBookingOut:
    booking = book_svc.request_booking(db, user, item_id, body)
    return book_svc.booking_to_out(db, booking, viewer=user)


@router.get("/me/rental-bookings", response_model=list[RentalBookingOut])
def my_rental_bookings(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[RentalBookingOut]:
    bookings = book_svc.list_renter_bookings(db, user)
    return [book_svc.booking_to_out(db, b, viewer=user) for b in bookings]


@router.get("/me/owner/booking-requests", response_model=list[RentalBookingOut])
def owner_booking_requests(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[RentalBookingOut]:
    bookings = book_svc.list_owner_incoming(db, user)
    return [book_svc.booking_to_out(db, b, viewer=user) for b in bookings]


@router.post("/rental-bookings/{booking_id}/accept", response_model=RentalBookingOut)
def accept_booking(
    booking_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    body: BookingOwnerAction | None = None,
) -> RentalBookingOut:
    note = body.owner_note if body else None
    booking = book_svc.owner_accept(db, user, booking_id, note)
    return book_svc.booking_to_out(db, booking, viewer=user)


@router.post("/rental-bookings/{booking_id}/decline", response_model=RentalBookingOut)
def decline_booking(
    booking_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    body: BookingOwnerAction | None = None,
) -> RentalBookingOut:
    note = body.owner_note if body else None
    booking = book_svc.owner_decline(db, user, booking_id, note)
    return book_svc.booking_to_out(db, booking, viewer=user)


@router.post("/rental-bookings/{booking_id}/cancel", response_model=RentalBookingOut)
def cancel_booking(booking_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> RentalBookingOut:
    booking = book_svc.renter_cancel(db, user, booking_id)
    return book_svc.booking_to_out(db, booking, viewer=user)


@router.post("/rental-bookings/{booking_id}/pickup", response_model=RentalBookingOut)
def pickup_booking(booking_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> RentalBookingOut:
    booking = book_svc.record_pickup(db, user, booking_id)
    return book_svc.booking_to_out(db, booking, viewer=user)


@router.post("/rental-bookings/{booking_id}/return", response_model=RentalBookingOut)
def return_booking(booking_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> RentalBookingOut:
    booking = book_svc.record_return(db, user, booking_id)
    return book_svc.booking_to_out(db, booking, viewer=user)


@router.post("/rental-bookings/{booking_id}/complete", response_model=RentalBookingOut)
def complete_booking(booking_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> RentalBookingOut:
    booking = book_svc.confirm_completion(db, user, booking_id)
    return book_svc.booking_to_out(db, booking, viewer=user)