import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.item import Item
from app.models.rental_booking import RentalBooking
from app.models.rental_messaging import RentalConversation, RentalMessage
from app.models.user import User
from app.schemas.messages import ConversationOut, MessageCreate, MessageOut


def _booking_participant(booking: RentalBooking, user: User, owner_id: uuid.UUID) -> bool:
    return user.id in (booking.renter_id, owner_id)


def ensure_rental_conversation(db: Session, booking: RentalBooking) -> RentalConversation:
    existing = db.scalar(select(RentalConversation).where(RentalConversation.rental_booking_id == booking.id))
    if existing:
        return existing
    conv = RentalConversation(rental_booking_id=booking.id)
    db.add(conv)
    db.flush()
    return conv


def conversation_for_booking(db: Session, user: User, booking_id: uuid.UUID) -> ConversationOut:
    booking = db.scalar(
        select(RentalBooking).where(RentalBooking.id == booking_id).options(joinedload(RentalBooking.item))
    )
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    owner_id = db.scalar(select(Item.owner_id).where(Item.id == booking.item_id))
    if owner_id is None or not _booking_participant(booking, user, owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")
    conv = db.scalar(
        select(RentalConversation)
        .where(RentalConversation.rental_booking_id == booking_id)
        .options(joinedload(RentalConversation.messages), joinedload(RentalConversation.booking))
    )
    if conv is None:
        conv = ensure_rental_conversation(db, booking)
        db.commit()
        conv = db.scalar(
            select(RentalConversation)
            .where(RentalConversation.id == conv.id)
            .options(joinedload(RentalConversation.messages), joinedload(RentalConversation.booking))
        )
    assert conv is not None
    return rental_conversation_to_out(db, conv, user, owner_id)


def list_rental_conversations(db: Session, user: User) -> list[ConversationOut]:
    stmt = (
        select(RentalConversation)
        .join(RentalBooking, RentalConversation.rental_booking_id == RentalBooking.id)
        .join(Item, RentalBooking.item_id == Item.id)
        .where((RentalBooking.renter_id == user.id) | (Item.owner_id == user.id))
        .options(joinedload(RentalConversation.messages), joinedload(RentalConversation.booking).joinedload(RentalBooking.item))
        .order_by(RentalConversation.created_at.desc())
    )
    convs = db.scalars(stmt).unique().all()
    out: list[ConversationOut] = []
    for conv in convs:
        owner_id = conv.booking.item.owner_id
        out.append(rental_conversation_to_out(db, conv, user, owner_id))
    return out


def get_rental_conversation(db: Session, user: User, conversation_id: uuid.UUID) -> RentalConversation:
    conv = db.scalar(
        select(RentalConversation)
        .where(RentalConversation.id == conversation_id)
        .options(joinedload(RentalConversation.messages), joinedload(RentalConversation.booking).joinedload(RentalBooking.item))
    )
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    owner_id = conv.booking.item.owner_id
    if not _booking_participant(conv.booking, user, owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")
    return conv


def post_rental_message(db: Session, user: User, conversation_id: uuid.UUID, body: MessageCreate) -> MessageOut:
    conv = get_rental_conversation(db, user, conversation_id)
    text = body.body.strip()
    booking = conv.booking
    owner_id = booking.item.owner_id
    recipient_id = booking.renter_id if user.id == owner_id else owner_id
    msg = RentalMessage(conversation_id=conv.id, sender_id=user.id, body=text)
    db.add(msg)
    from app.services import notification_service as notify_svc

    preview = text if len(text) <= 120 else f"{text[:117]}..."
    notify_svc.emit(
        db,
        recipient_id,
        kind="message",
        title="New message on a rental",
        body=preview,
        link_path=f"/app/messages/{conv.id}",
    )
    db.commit()
    db.refresh(msg)
    return _rental_message_out(db, msg, viewer_id=user.id)


def _rental_message_out(db: Session, msg: RentalMessage, *, viewer_id: uuid.UUID) -> MessageOut:
    sender = db.get(User, msg.sender_id)
    name = sender.profile.display_name if sender and sender.profile else "User"
    return MessageOut(
        id=msg.id,
        sender_id=msg.sender_id,
        sender_name=name,
        body=msg.body,
        created_at=msg.created_at,
        is_mine=msg.sender_id == viewer_id,
    )


def rental_conversation_to_out(
    db: Session, conv: RentalConversation, viewer: User, owner_id: uuid.UUID
) -> ConversationOut:
    booking = conv.booking
    partner_id = booking.renter_id if viewer.id == owner_id else owner_id
    partner = db.get(User, partner_id)
    partner_name = partner.profile.display_name if partner and partner.profile else "Neighbour"
    messages = [_rental_message_out(db, m, viewer_id=viewer.id) for m in conv.messages]
    last = messages[-1].body if messages else None
    title = booking.item.title if booking.item else "Rental booking"
    return ConversationOut(
        id=conv.id,
        kind="rental_booking",
        service_job_id=None,
        rental_booking_id=booking.id,
        job_title=title,
        job_status=booking.status,
        partner_name=partner_name,
        last_message_preview=last,
        messages=messages,
    )