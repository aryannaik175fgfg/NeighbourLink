import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.schemas.supervision import (
    EndorsementCreate,
    EndorsementOut,
    SupervisionOut,
    SupervisionRequestCreate,
    SupervisionRespond,
)
from app.services import supervision_service as sup_svc

router = APIRouter(prefix="/me/supervision", tags=["supervision"])


@router.post("/request", response_model=SupervisionOut, status_code=201)
def request_supervision(
    body: SupervisionRequestCreate, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> SupervisionOut:
    return sup_svc.request_supervisor(db, user, body)


@router.get("", response_model=list[SupervisionOut])
def my_supervision(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[SupervisionOut]:
    return sup_svc.list_for_user(db, user)


@router.get("/pending", response_model=list[SupervisionOut])
def pending_requests(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[SupervisionOut]:
    return sup_svc.pending_for_supervisor(db, user)


@router.post("/requests/{relationship_id}", response_model=SupervisionOut)
def respond_request(
    relationship_id: uuid.UUID,
    body: SupervisionRespond,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SupervisionOut:
    return sup_svc.respond(db, user, relationship_id, accept=body.accept)


@router.post("/endorsements", response_model=EndorsementOut, status_code=201)
def create_endorsement(
    body: EndorsementCreate, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> EndorsementOut:
    return sup_svc.endorse(db, user, body)


@router.get("/endorsements", response_model=list[EndorsementOut])
def my_endorsements(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[EndorsementOut]:
    return sup_svc.list_endorsements_for_trainee(db, user)


@router.post("/trainee/enroll", status_code=204)
def enroll_trainee(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> None:
    sup_svc.grant_trainee_role(db, user)