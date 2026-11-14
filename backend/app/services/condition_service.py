import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.condition_report import ConditionPhase, ConditionReportPhoto, RentalConditionReport
from app.models.rental_booking import RentalBooking, RentalBookingStatus
from app.models.user import User
from app.schemas.condition import ConditionPhotoOut, ConditionReportOut
from app.services.booking_service import get_booking
from app.services.storage_service import save_upload


def _photo_url(object_key: str, scope: str) -> str:
    return f"/api/v1/files/{scope}/{object_key}"


def assert_participant(db: Session, booking: RentalBooking, user: User):
    from app.services.availability_service import get_item_or_404

    item = get_item_or_404(db, booking.item_id)
    if user.id not in (booking.renter_id, item.owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


def _phase_allowed(booking: RentalBooking, phase: ConditionPhase) -> None:
    if phase == ConditionPhase.PICKUP and booking.status not in (
        RentalBookingStatus.CONFIRMED,
        RentalBookingStatus.ACTIVE,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pickup report not allowed for this status")
    if phase == ConditionPhase.RETURN and booking.status not in (
        RentalBookingStatus.ACTIVE,
        RentalBookingStatus.RETURNED,
        RentalBookingStatus.COMPLETED,
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Return report not allowed for this status")


async def create_report(
    db: Session,
    user: User,
    booking_id: uuid.UUID,
    *,
    phase: ConditionPhase,
    notes: str | None,
    damage_notes: str | None,
    files: list[UploadFile],
) -> RentalConditionReport:
    booking = get_booking(db, booking_id)
    assert_participant(db, booking, user)
    _phase_allowed(booking, phase)

    existing = db.scalar(
        select(RentalConditionReport).where(
            RentalConditionReport.rental_booking_id == booking_id,
            RentalConditionReport.phase == phase.value,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A report for this phase already exists and cannot be overwritten",
        )

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one photo is required")

    report = RentalConditionReport(
        rental_booking_id=booking_id,
        phase=phase.value,
        notes=notes,
        damage_notes=damage_notes,
        created_by_id=user.id,
    )
    db.add(report)
    db.flush()

    for file in files[:10]:
        key, filename, size = await save_upload(file, prefix=f"condition/{booking_id}/{phase.value}")
        db.add(
            ConditionReportPhoto(
                report_id=report.id,
                object_key=key,
                original_filename=filename,
                content_type=file.content_type or "image/jpeg",
                byte_size=size,
            )
        )

    db.commit()
    loaded = db.scalar(
        select(RentalConditionReport)
        .where(RentalConditionReport.id == report.id)
        .options(joinedload(RentalConditionReport.photos))
    )
    if loaded is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Report not saved")
    return loaded


def list_reports(db: Session, user: User, booking_id: uuid.UUID) -> list[ConditionReportOut]:
    booking = get_booking(db, booking_id)
    assert_participant(db, booking, user)
    reports = db.scalars(
        select(RentalConditionReport)
        .where(RentalConditionReport.rental_booking_id == booking_id)
        .options(joinedload(RentalConditionReport.photos))
        .order_by(RentalConditionReport.created_at)
    ).all()
    return [_report_out(r) for r in reports]


def _report_out(report: RentalConditionReport) -> ConditionReportOut:
    photos = [
        ConditionPhotoOut(
            id=p.id,
            original_filename=p.original_filename,
            content_type=p.content_type,
            url=_photo_url(p.object_key, "condition"),
        )
        for p in report.photos
    ]
    return ConditionReportOut(
        id=report.id,
        rental_booking_id=report.rental_booking_id,
        phase=report.phase,
        notes=report.notes,
        damage_notes=report.damage_notes,
        created_at=report.created_at,
        owner_acknowledged_at=report.owner_acknowledged_at,
        renter_acknowledged_at=report.renter_acknowledged_at,
        photos=photos,
    )


def acknowledge_report(db: Session, user: User, booking_id: uuid.UUID, report_id: uuid.UUID) -> ConditionReportOut:
    booking = get_booking(db, booking_id)
    from app.services.availability_service import get_item_or_404

    item = get_item_or_404(db, booking.item_id)
    report = db.scalar(
        select(RentalConditionReport)
        .where(RentalConditionReport.id == report_id, RentalConditionReport.rental_booking_id == booking_id)
        .options(joinedload(RentalConditionReport.photos))
    )
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    now = datetime.now(UTC)
    if user.id == item.owner_id:
        if report.owner_acknowledged_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already acknowledged")
        report.owner_acknowledged_at = now
    elif user.id == booking.renter_id:
        if report.renter_acknowledged_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already acknowledged")
        report.renter_acknowledged_at = now
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    db.add(report)
    db.commit()
    db.refresh(report)
    return _report_out(report)


def can_access_condition_file(db: Session, user: User | None, object_key: str) -> bool:
    photo = db.scalar(select(ConditionReportPhoto).where(ConditionReportPhoto.object_key == object_key))
    if photo is None:
        return False
    report = db.get(RentalConditionReport, photo.report_id)
    if report is None:
        return False
    booking = db.get(RentalBooking, report.rental_booking_id)
    if booking is None:
        return False
    from app.services.availability_service import get_item_or_404

    item = get_item_or_404(db, booking.item_id)
    if user is None:
        return False
    return user.id in (booking.renter_id, item.owner_id)