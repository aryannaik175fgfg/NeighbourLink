from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.identity import IdentityStatus, UserIdentityVerification
from app.models.user import User
from app.schemas.identity import IdentityAdminRow, IdentityDecision, IdentityOut, IdentitySubmit
from app.services import audit_service as audit_svc
from app.services import notification_service as notify_svc


def get_mine(db: Session, user: User) -> IdentityOut | None:
    row = db.get(UserIdentityVerification, user.id)
    if row is None:
        return None
    return IdentityOut.model_validate(row)


def submit(db: Session, user: User, body: IdentitySubmit) -> IdentityOut:
    existing = db.get(UserIdentityVerification, user.id)
    if existing and existing.status == IdentityStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Verification already pending review")
    if existing and existing.status == IdentityStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identity already verified")

    ref = body.document_reference.strip()
    if existing:
        existing.document_type = body.document_type
        existing.document_reference = ref
        existing.user_note = body.user_note.strip() if body.user_note else None
        existing.status = IdentityStatus.PENDING
        existing.admin_note = None
        existing.reviewed_by = None
        existing.reviewed_at = None
        existing.submitted_at = datetime.now(UTC)
        row = existing
    else:
        row = UserIdentityVerification(
            user_id=user.id,
            document_type=body.document_type,
            document_reference=ref,
            user_note=body.user_note.strip() if body.user_note else None,
            status=IdentityStatus.PENDING,
        )
        db.add(row)
    db.flush()
    notify_svc.emit(
        db,
        user.id,
        kind="identity",
        title="Identity submitted",
        body="An administrator will review your documents.",
        link_path="/app/profile",
        dedupe_key=f"identity-submitted-{user.id}",
    )
    db.commit()
    db.refresh(row)
    return IdentityOut.model_validate(row)


def list_for_admin(db: Session, *, status_filter: str | None = "pending") -> list[IdentityAdminRow]:
    stmt = (
        select(UserIdentityVerification)
        .join(User, UserIdentityVerification.user_id == User.id)
        .options(joinedload(UserIdentityVerification.user).joinedload(User.profile))
    )
    if status_filter:
        stmt = stmt.where(UserIdentityVerification.status == status_filter)
    stmt = stmt.order_by(UserIdentityVerification.submitted_at)
    rows = db.scalars(stmt).unique().all()
    out: list[IdentityAdminRow] = []
    for row in rows:
        out.append(
            IdentityAdminRow(
                user_id=row.user_id,
                display_name=row.user.profile.display_name,
                email=row.user.email,
                document_type=row.document_type,
                document_reference=row.document_reference,
                user_note=row.user_note,
                status=row.status,
                submitted_at=row.submitted_at,
            )
        )
    return out


def decide(db: Session, admin: User, user_id, body: IdentityDecision) -> IdentityOut:
    from uuid import UUID

    uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
    row = db.get(UserIdentityVerification, uid)
    if row is None or row.status != IdentityStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending verification not found")

    if body.approve:
        row.status = IdentityStatus.APPROVED
        row.admin_note = body.note.strip() if body.note else None
    else:
        if not body.note or len(body.note.strip()) < 5:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejection requires a note")
        row.status = IdentityStatus.REJECTED
        row.admin_note = body.note.strip()
    row.reviewed_by = admin.id
    row.reviewed_at = datetime.now(UTC)
    db.add(row)
    audit_svc.record(
        db,
        admin,
        action="identity_decision",
        target_type="user",
        target_id=uid,
        detail={"approve": body.approve, "note": row.admin_note},
    )
    notify_svc.emit(
        db,
        uid,
        kind="identity",
        title="Identity verified" if body.approve else "Identity not verified",
        body=row.admin_note or ("Your identity is now verified on NeighbourLink." if body.approve else "See admin note and resubmit."),
        link_path="/app/profile",
        dedupe_key=f"identity-decided-{uid}-{row.reviewed_at.isoformat()}",
    )
    db.commit()
    db.refresh(row)
    return IdentityOut.model_validate(row)