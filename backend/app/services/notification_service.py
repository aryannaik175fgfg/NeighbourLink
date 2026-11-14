import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User
from app.schemas.notifications import NotificationOut, UnreadCountOut


def emit(
    db: Session,
    user_id: uuid.UUID,
    *,
    kind: str,
    title: str,
    body: str,
    link_path: str | None = None,
    dedupe_key: str | None = None,
) -> Notification | None:
    from app.services import settings_service as sett_svc

    if not sett_svc.notification_allowed(db, user_id, kind):
        return None
    note = Notification(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        link_path=link_path,
        dedupe_key=dedupe_key,
    )
    if dedupe_key:
        existing = db.scalar(
            select(Notification).where(Notification.user_id == user_id, Notification.dedupe_key == dedupe_key)
        )
        if existing:
            return existing
    db.add(note)
    db.flush()
    from app.services.notification_delivery import deliver_email

    deliver_email(db, user_id, note)
    return note


def list_for_user(db: Session, user: User, *, limit: int = 50) -> list[NotificationOut]:
    rows = db.scalars(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(limit)
    ).all()
    return [NotificationOut.model_validate(r) for r in rows]


def unread_count(db: Session, user: User) -> UnreadCountOut:
    count = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return UnreadCountOut(count=int(count or 0))


def mark_read(db: Session, user: User, notification_id: uuid.UUID) -> NotificationOut:
    note = db.get(Notification, notification_id)
    if note is None or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if note.read_at is None:
        note.read_at = datetime.now(UTC)
        db.add(note)
        db.commit()
        db.refresh(note)
    return NotificationOut.model_validate(note)


def mark_all_read(db: Session, user: User) -> UnreadCountOut:
    notes = db.scalars(
        select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    ).all()
    now = datetime.now(UTC)
    for note in notes:
        note.read_at = now
        db.add(note)
    db.commit()
    return UnreadCountOut(count=0)