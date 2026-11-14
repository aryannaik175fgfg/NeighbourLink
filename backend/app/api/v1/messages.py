import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.schemas.messages import ConversationOut, MessageCreate, MessageOut
from app.services import message_service as msg_svc
from app.services import rental_message_service as rent_msg_svc

router = APIRouter(tags=["messages"])


@router.get("/me/conversations", response_model=list[ConversationOut])
def my_conversations(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[ConversationOut]:
    return msg_svc.list_my_conversations(db, user)


@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> ConversationOut:
    return msg_svc.get_conversation_out(db, user, conversation_id)


@router.get("/service-jobs/{job_id}/conversation", response_model=ConversationOut)
def job_conversation(
    job_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> ConversationOut:
    return msg_svc.conversation_for_job(db, user, job_id)


@router.get("/rental-bookings/{booking_id}/conversation", response_model=ConversationOut)
def rental_booking_conversation(
    booking_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> ConversationOut:
    return rent_msg_svc.conversation_for_booking(db, user, booking_id)


@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut, status_code=201)
def send_message(
    conversation_id: uuid.UUID,
    body: MessageCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> MessageOut:
    msg = msg_svc.post_message(db, user, conversation_id, body)
    msg.is_mine = True
    return msg