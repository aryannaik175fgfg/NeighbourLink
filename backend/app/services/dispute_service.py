import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assistance import ServiceJob, ServiceJobStatus
from app.models.dispute import Dispute, DisputeStatus, DisputeSubjectType
from app.models.item import Item
from app.models.rental_booking import RentalBooking, RentalBookingStatus
from app.models.user import User
from app.schemas.dispute import DisputeCreate, DisputeOut, DisputeResolve
from app.services import audit_service as audit_svc
from app.services import notification_service as notify_svc


def _user_can_access_subject(db: Session, user: User, subject_type: str, subject_id: uuid.UUID) -> None:
    if subject_type == DisputeSubjectType.RENTAL_BOOKING:
        booking = db.get(RentalBooking, subject_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        owner_id = db.scalar(select(Item.owner_id).where(Item.id == booking.item_id))
        if user.id not in (booking.renter_id, owner_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a party to this booking")
        return
    if subject_type == DisputeSubjectType.SERVICE_JOB:
        job = db.get(ServiceJob, subject_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service job not found")
        if user.id not in (job.customer_id, job.provider_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a party to this job")
        return
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid subject type")


def open_dispute(db: Session, user: User, body: DisputeCreate) -> DisputeOut:
    _user_can_access_subject(db, user, body.subject_type, body.subject_id)
    existing = db.scalar(
        select(Dispute).where(
            Dispute.subject_type == body.subject_type,
            Dispute.subject_id == body.subject_id,
            Dispute.status.in_((DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW)),
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An open dispute already exists for this item")

    dispute = Dispute(
        subject_type=body.subject_type,
        subject_id=body.subject_id,
        opened_by=user.id,
        reason=body.reason.strip(),
        status=DisputeStatus.OPEN,
    )
    db.add(dispute)

    if body.subject_type == DisputeSubjectType.RENTAL_BOOKING:
        booking = db.get(RentalBooking, body.subject_id)
        if booking and booking.status not in (
            RentalBookingStatus.DECLINED,
            RentalBookingStatus.CANCELLED,
            RentalBookingStatus.EXPIRED,
            RentalBookingStatus.COMPLETED,
        ):
            booking.status = RentalBookingStatus.DISPUTED
            db.add(booking)
    elif body.subject_type == DisputeSubjectType.SERVICE_JOB:
        job = db.get(ServiceJob, body.subject_id)
        if job and job.status not in (ServiceJobStatus.COMPLETED, ServiceJobStatus.CANCELLED):
            job.status = ServiceJobStatus.DISPUTED
            db.add(job)

    db.commit()
    db.refresh(dispute)
    notify_svc.emit(
        db,
        user.id,
        kind="dispute",
        title="Dispute opened",
        body="Our team will review your case.",
        link_path="/app/disputes",
        dedupe_key=f"dispute-opened-{dispute.id}",
    )
    db.commit()
    return DisputeOut.model_validate(dispute)


def list_mine(db: Session, user: User) -> list[DisputeOut]:
    stmt = select(Dispute).where(Dispute.opened_by == user.id).order_by(Dispute.created_at.desc())
    rows = db.scalars(stmt).all()
    party_stmt = select(Dispute).order_by(Dispute.created_at.desc())
    all_rows = db.scalars(party_stmt).all()
    seen: set[uuid.UUID] = set()
    out: list[DisputeOut] = []
    for row in all_rows:
        if row.id in seen:
            continue
        try:
            _user_can_access_subject(db, user, row.subject_type, row.subject_id)
        except HTTPException:
            continue
        seen.add(row.id)
        out.append(DisputeOut.model_validate(row))
    for row in rows:
        if row.id not in seen:
            out.append(DisputeOut.model_validate(row))
    out.sort(key=lambda d: d.created_at, reverse=True)
    return out


def list_admin(db: Session, *, status_filter: str | None = None) -> list[DisputeOut]:
    stmt = select(Dispute).order_by(Dispute.created_at.desc())
    if status_filter:
        stmt = stmt.where(Dispute.status == status_filter)
    rows = db.scalars(stmt).all()
    return [DisputeOut.model_validate(r) for r in rows]


def resolve_dispute(db: Session, admin: User, dispute_id: uuid.UUID, body: DisputeResolve) -> DisputeOut:
    dispute = db.get(Dispute, dispute_id)
    if dispute is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")
    if dispute.status in (DisputeStatus.RESOLVED, DisputeStatus.CLOSED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dispute already closed")

    dispute.status = body.status
    dispute.resolution_notes = body.resolution_notes.strip()
    dispute.resolved_by = admin.id
    db.add(dispute)
    audit_svc.record(
        db,
        admin,
        action="dispute_resolve",
        target_type="dispute",
        target_id=dispute_id,
        detail={"status": body.status, "notes": dispute.resolution_notes},
    )
    if body.deposit_outcome and dispute.subject_type == DisputeSubjectType.RENTAL_BOOKING:
        booking = db.get(RentalBooking, dispute.subject_id)
        from app.services import escrow_service as escrow_svc

        if booking and body.deposit_outcome == "release_renter":
            escrow_svc.release_to_renter(
                db, booking, note=f"Dispute resolution: {body.resolution_notes[:200]}"
            )
        elif booking and body.deposit_outcome == "release_owner":
            escrow_svc.release_to_owner(
                db, booking, note=f"Dispute resolution: {body.resolution_notes[:200]}"
            )

    notify_svc.emit(
        db,
        dispute.opened_by,
        kind="dispute",
        title="Dispute update",
        body=body.resolution_notes[:240],
        link_path="/app/disputes",
        dedupe_key=f"dispute-resolved-{dispute_id}",
    )
    db.commit()
    db.refresh(dispute)
    return DisputeOut.model_validate(dispute)