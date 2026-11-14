import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AdminAuditLog
from app.models.user import User
from app.schemas.audit import AuditLogOut


def record(
    db: Session,
    actor: User | None,
    *,
    action: str,
    target_type: str,
    target_id: str | uuid.UUID,
    detail: dict[str, Any] | None = None,
) -> None:
    entry = AdminAuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        detail=detail or {},
    )
    db.add(entry)


def list_recent(db: Session, *, limit: int = 100) -> list[AuditLogOut]:
    stmt = select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(min(limit, 500))
    rows = db.scalars(stmt).all()
    return [AuditLogOut.model_validate(r) for r in rows]