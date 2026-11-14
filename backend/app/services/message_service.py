import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.assistance import ServiceConversation, ServiceJob, ServiceMessage
from app.models.user import User
from app.schemas.messages import ConversationOut, MessageCreate, MessageOut


def ensure_conversation(db: Session, job: ServiceJob) -> ServiceConversation:
    existing = db.scalar(select(ServiceConversation).where(ServiceConversation.service_job_id == job.id))
    if existing:
        return existing
    conv = ServiceConversation(service_job_id=job.id)
    db.add(conv)
    db.flush()
    return conv


def _job_participant(job: ServiceJob, user: User) -> bool:
    return job.provider_id == user.id or job.customer_id == user.id


def list_my_conversations(db: Session, user: User) -> list[ConversationOut]:
    from app.services.rental_message_service import list_rental_conversations

    stmt = (
        select(ServiceConversation)
        .join(ServiceJob, ServiceConversation.service_job_id == ServiceJob.id)
        .where((ServiceJob.provider_id == user.id) | (ServiceJob.customer_id == user.id))
        .options(
            joinedload(ServiceConversation.job),
            joinedload(ServiceConversation.messages),
        )
        .order_by(ServiceConversation.created_at.desc())
    )
    convs = db.scalars(stmt).unique().all()
    service_out = [conversation_to_out(db, c, user) for c in convs]
    rental_out = list_rental_conversations(db, user)
    merged = service_out + rental_out
    from datetime import datetime, timezone

    def _sort_key(c: ConversationOut) -> datetime:
        if c.messages:
            return c.messages[-1].created_at
        return datetime.min.replace(tzinfo=timezone.utc)

    merged.sort(key=_sort_key, reverse=True)
    return merged


def get_conversation(db: Session, user: User, conversation_id: uuid.UUID) -> ServiceConversation:
    conv = db.scalar(
        select(ServiceConversation)
        .where(ServiceConversation.id == conversation_id)
        .options(joinedload(ServiceConversation.job), joinedload(ServiceConversation.messages))
    )
    if conv is None:
        from app.models.rental_messaging import RentalConversation

        if db.get(RentalConversation, conversation_id) is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use rental conversation handler")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if not _job_participant(conv.job, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")
    return conv


def get_conversation_out(db: Session, user: User, conversation_id: uuid.UUID) -> ConversationOut:
    from app.models.rental_messaging import RentalConversation
    from app.services.rental_message_service import get_rental_conversation, rental_conversation_to_out

    svc = db.scalar(
        select(ServiceConversation)
        .where(ServiceConversation.id == conversation_id)
        .options(joinedload(ServiceConversation.job), joinedload(ServiceConversation.messages))
    )
    if svc is not None:
        if not _job_participant(svc.job, user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")
        return conversation_to_out(db, svc, user)
    rental = get_rental_conversation(db, user, conversation_id)
    return rental_conversation_to_out(db, rental, user, rental.booking.item.owner_id)


def conversation_for_job(db: Session, user: User, job_id: uuid.UUID) -> ConversationOut:
    job = db.get(ServiceJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not _job_participant(job, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant")
    conv = db.scalar(
        select(ServiceConversation)
        .where(ServiceConversation.service_job_id == job_id)
        .options(joinedload(ServiceConversation.job), joinedload(ServiceConversation.messages))
    )
    if conv is None:
        conv = ensure_conversation(db, job)
        db.commit()
        conv = db.scalar(
            select(ServiceConversation)
            .where(ServiceConversation.id == conv.id)
            .options(joinedload(ServiceConversation.job), joinedload(ServiceConversation.messages))
        )
    assert conv is not None
    return conversation_to_out(db, conv, user)


def post_message(db: Session, user: User, conversation_id: uuid.UUID, body: MessageCreate) -> MessageOut:
    from app.models.rental_messaging import RentalConversation
    from app.services.rental_message_service import post_rental_message

    if db.get(RentalConversation, conversation_id) is not None:
        return post_rental_message(db, user, conversation_id, body)
    conv = get_conversation(db, user, conversation_id)
    text = body.body.strip()
    if len(text) < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message is empty")
    msg = ServiceMessage(conversation_id=conv.id, sender_id=user.id, body=text)
    db.add(msg)
    recipient_id = conv.job.customer_id if user.id == conv.job.provider_id else conv.job.provider_id
    from app.services import notification_service as notify_svc

    preview = text if len(text) <= 120 else f"{text[:117]}..."
    notify_svc.emit(
        db,
        recipient_id,
        kind="message",
        title="New message on a service job",
        body=preview,
        link_path=f"/app/messages/{conv.id}",
    )
    db.commit()
    db.refresh(msg)
    return _message_out(db, msg)


def _message_out(db: Session, msg: ServiceMessage) -> MessageOut:
    sender = db.get(User, msg.sender_id)
    name = sender.profile.display_name if sender and sender.profile else "User"
    return MessageOut(
        id=msg.id,
        sender_id=msg.sender_id,
        sender_name=name,
        body=msg.body,
        created_at=msg.created_at,
        is_mine=False,
    )


def conversation_to_out(db: Session, conv: ServiceConversation, viewer: User) -> ConversationOut:
    job = conv.job
    partner_id = job.customer_id if job.provider_id == viewer.id else job.provider_id
    partner = db.get(User, partner_id)
    partner_name = partner.profile.display_name if partner and partner.profile else "Neighbour"
    messages = [_message_out(db, m) for m in conv.messages]
    for m in messages:
        m.is_mine = m.sender_id == viewer.id
    last = messages[-1].body if messages else None
    from app.models.assistance import ServiceRequest

    title_row = db.get(ServiceRequest, job.request_id)
    return ConversationOut(
        id=conv.id,
        kind="service_job",
        service_job_id=job.id,
        rental_booking_id=None,
        job_title=title_row.title if title_row else "Service job",
        job_status=job.status,
        partner_name=partner_name,
        last_message_preview=last,
        messages=messages,
    )