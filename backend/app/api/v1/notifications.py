import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.schemas.notifications import NotificationOut, UnreadCountOut
from app.services import notification_service as notify_svc

router = APIRouter(tags=["notifications"])


@router.get("/me/notifications", response_model=list[NotificationOut])
def my_notifications(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[NotificationOut]:
    return notify_svc.list_for_user(db, user)


@router.get("/me/notifications/unread-count", response_model=UnreadCountOut)
def my_unread_count(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> UnreadCountOut:
    return notify_svc.unread_count(db, user)


@router.post("/me/notifications/{notification_id}/read", response_model=NotificationOut)
def read_notification(
    notification_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> NotificationOut:
    return notify_svc.mark_read(db, user, notification_id)


@router.post("/me/notifications/read-all", response_model=UnreadCountOut)
def read_all_notifications(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> UnreadCountOut:
    return notify_svc.mark_all_read(db, user)