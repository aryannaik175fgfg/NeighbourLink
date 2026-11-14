import uuid
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.models.condition_report import ConditionPhase
from app.schemas.condition import ConditionReportOut
from app.services import condition_service as cond_svc

router = APIRouter(tags=["condition"])


@router.get("/rental-bookings/{booking_id}/condition-reports", response_model=list[ConditionReportOut])
def list_condition_reports(
    booking_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[ConditionReportOut]:
    return cond_svc.list_reports(db, user, booking_id)


@router.post("/rental-bookings/{booking_id}/condition-reports", response_model=ConditionReportOut, status_code=201)
async def create_condition_report(
    booking_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    phase: Annotated[ConditionPhase, Form()],
    notes: Annotated[str | None, Form()] = None,
    damage_notes: Annotated[str | None, Form()] = None,
    photos: Annotated[list[UploadFile], File()] = ...,
) -> ConditionReportOut:
    report = await cond_svc.create_report(
        db,
        user,
        booking_id,
        phase=phase,
        notes=notes,
        damage_notes=damage_notes,
        files=photos,
    )
    return cond_svc._report_out(report)


@router.post("/rental-bookings/{booking_id}/condition-reports/{report_id}/acknowledge", response_model=ConditionReportOut)
def acknowledge_condition_report(
    booking_id: uuid.UUID,
    report_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ConditionReportOut:
    return cond_svc.acknowledge_report(db, user, booking_id, report_id)