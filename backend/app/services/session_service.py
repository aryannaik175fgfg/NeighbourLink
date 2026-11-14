import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.session import Session as UserSession
from app.models.user import User
from app.schemas.session import SessionOut


def list_sessions(db: Session, user: User, *, current_session_id: uuid.UUID | None) -> list[SessionOut]:
    rows = db.scalars(
        select(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .order_by(UserSession.created_at.desc())
    ).all()
    now = datetime.now(UTC)
    out: list[SessionOut] = []
    for row in rows:
        if row.expires_at < now:
            continue
        out.append(
            SessionOut(
                id=row.id,
                user_agent=row.user_agent,
                created_at=row.created_at,
                expires_at=row.expires_at,
                is_current=current_session_id is not None and row.id == current_session_id,
            )
        )
    return out


def revoke_session(db: Session, user: User, session_id: uuid.UUID, *, current_session_id: uuid.UUID | None) -> None:
    if current_session_id is not None and session_id == current_session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot revoke the current session from here")
    row = db.get(UserSession, session_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        db.add(row)
        db.commit()


def revoke_other_sessions(db: Session, user: User, *, current_session_id: uuid.UUID | None) -> int:
    if current_session_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current session unknown")
    rows = db.scalars(
        select(UserSession).where(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
            UserSession.id != current_session_id,
        )
    ).all()
    now = datetime.now(UTC)
    count = 0
    for row in rows:
        row.revoked_at = now
        db.add(row)
        count += 1
    db.commit()
    return count