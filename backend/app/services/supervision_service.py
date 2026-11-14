import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.assistance import ServiceCategory
from app.models.role import Role
from app.models.supervision import SupervisionEndorsement, SupervisionRelationship, SupervisionStatus
from app.models.user import User
from app.schemas.supervision import EndorsementCreate, EndorsementOut, SupervisionOut, SupervisionRequestCreate


def _has_role(user: User, slug: str) -> bool:
    return any(r.slug == slug for r in user.roles)


def trainee_has_active_supervision(db: Session, user_id: uuid.UUID) -> bool:
    rel = db.scalar(
        select(SupervisionRelationship).where(
            SupervisionRelationship.trainee_id == user_id,
            SupervisionRelationship.status == SupervisionStatus.ACTIVE,
        )
    )
    return rel is not None


def request_supervisor(db: Session, trainee: User, body: SupervisionRequestCreate) -> SupervisionOut:
    if not _has_role(trainee, "trainee"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trainee role required to request supervision")
    supervisor = db.scalar(select(User).where(User.email == body.supervisor_email.lower()))
    if supervisor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor not found")
    if supervisor.id == trainee.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot supervise yourself")
    if not _has_role(supervisor, "supervisor"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a supervisor")

    existing = db.scalar(
        select(SupervisionRelationship).where(
            SupervisionRelationship.trainee_id == trainee.id,
            SupervisionRelationship.status.in_((SupervisionStatus.PENDING, SupervisionStatus.ACTIVE)),
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have a pending or active supervision")

    rel = SupervisionRelationship(
        trainee_id=trainee.id,
        supervisor_id=supervisor.id,
        trainee_note=body.trainee_note.strip() if body.trainee_note else None,
        status=SupervisionStatus.PENDING,
    )
    db.add(rel)
    from app.services import notification_service as notify_svc

    notify_svc.emit(
        db,
        supervisor.id,
        kind="supervision",
        title="New trainee request",
        body=f"{trainee.profile.display_name} asked you to supervise them.",
        link_path="/app/mentorship",
        dedupe_key=f"supervision-req-{rel.id}",
    )
    db.commit()
    db.refresh(rel)
    return _rel_out(db, rel)


def list_for_user(db: Session, user: User) -> list[SupervisionOut]:
    stmt = (
        select(SupervisionRelationship)
        .where(
            (SupervisionRelationship.trainee_id == user.id) | (SupervisionRelationship.supervisor_id == user.id)
        )
        .order_by(SupervisionRelationship.created_at.desc())
    )
    rows = db.scalars(stmt).all()
    return [_rel_out(db, r) for r in rows]


def pending_for_supervisor(db: Session, supervisor: User) -> list[SupervisionOut]:
    if not _has_role(supervisor, "supervisor"):
        return []
    rows = db.scalars(
        select(SupervisionRelationship).where(
            SupervisionRelationship.supervisor_id == supervisor.id,
            SupervisionRelationship.status == SupervisionStatus.PENDING,
        )
    ).all()
    return [_rel_out(db, r) for r in rows]


def respond(db: Session, supervisor: User, relationship_id: uuid.UUID, *, accept: bool) -> SupervisionOut:
    rel = db.get(SupervisionRelationship, relationship_id)
    if rel is None or rel.supervisor_id != supervisor.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if rel.status != SupervisionStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request already handled")
    rel.status = SupervisionStatus.ACTIVE if accept else SupervisionStatus.DECLINED
    rel.responded_at = datetime.now(UTC)
    db.add(rel)
    from app.services import notification_service as notify_svc

    notify_svc.emit(
        db,
        rel.trainee_id,
        kind="supervision",
        title="Supervision update",
        body="Your supervisor accepted." if accept else "Your supervisor declined the request.",
        link_path="/app/mentorship",
        dedupe_key=f"supervision-resp-{rel.id}",
    )
    db.commit()
    db.refresh(rel)
    return _rel_out(db, rel)


def endorse(db: Session, supervisor: User, body: EndorsementCreate) -> EndorsementOut:
    if not _has_role(supervisor, "supervisor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Supervisor role required")
    rel = db.scalar(
        select(SupervisionRelationship).where(
            SupervisionRelationship.trainee_id == body.trainee_id,
            SupervisionRelationship.supervisor_id == supervisor.id,
            SupervisionRelationship.status == SupervisionStatus.ACTIVE,
        )
    )
    if rel is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active supervision with this trainee")
    cat_id = None
    cat_name = None
    if body.category_slug:
        cat = db.scalar(select(ServiceCategory).where(ServiceCategory.slug == body.category_slug))
        if cat is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown category")
        cat_id = cat.id
        cat_name = cat.name
    entry = SupervisionEndorsement(relationship_id=rel.id, category_id=cat_id, note=body.note.strip())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    trainee = db.get(User, body.trainee_id)
    name = trainee.profile.display_name if trainee and trainee.profile else "Trainee"
    return EndorsementOut(
        id=entry.id,
        trainee_name=name,
        category_name=cat_name,
        note=entry.note,
        created_at=entry.created_at,
    )


def list_endorsements_for_trainee(db: Session, trainee: User) -> list[EndorsementOut]:
    rows = db.scalars(
        select(SupervisionEndorsement)
        .join(SupervisionRelationship)
        .where(SupervisionRelationship.trainee_id == trainee.id)
        .options(joinedload(SupervisionEndorsement.relationship))
        .order_by(SupervisionEndorsement.created_at.desc())
    ).all()
    out: list[EndorsementOut] = []
    for entry in rows:
        cat_name = None
        if entry.category_id:
            cat = db.get(ServiceCategory, entry.category_id)
            cat_name = cat.name if cat else None
        trainee_user = db.get(User, entry.relationship.trainee_id)
        name = trainee_user.profile.display_name if trainee_user and trainee_user.profile else "Trainee"
        out.append(
            EndorsementOut(
                id=entry.id,
                trainee_name=name,
                category_name=cat_name,
                note=entry.note,
                created_at=entry.created_at,
            )
        )
    return out


def _rel_out(db: Session, rel: SupervisionRelationship) -> SupervisionOut:
    trainee = db.get(User, rel.trainee_id)
    supervisor = db.get(User, rel.supervisor_id)
    return SupervisionOut(
        id=rel.id,
        trainee_id=rel.trainee_id,
        supervisor_id=rel.supervisor_id,
        trainee_name=trainee.profile.display_name if trainee and trainee.profile else "Trainee",
        supervisor_name=supervisor.profile.display_name if supervisor and supervisor.profile else "Supervisor",
        status=rel.status,
        trainee_note=rel.trainee_note,
        created_at=rel.created_at,
        responded_at=rel.responded_at,
    )


def grant_trainee_role(db: Session, user: User) -> None:
    if _has_role(user, "trainee"):
        return
    role = db.scalar(select(Role).where(Role.slug == "trainee"))
    if role is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Roles not seeded")
    user.roles.append(role)
    db.add(user)
    db.commit()