import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.schemas.dispute import DisputeCreate, DisputeOut
from app.services import dispute_service as dispute_svc

router = APIRouter(prefix="/disputes", tags=["disputes"])


@router.get("/mine", response_model=list[DisputeOut])
def my_disputes(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[DisputeOut]:
    return dispute_svc.list_mine(db, user)


@router.post("", response_model=DisputeOut, status_code=201)
def create_dispute(
    body: DisputeCreate, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> DisputeOut:
    return dispute_svc.open_dispute(db, user, body)


@router.get("/{dispute_id}", response_model=DisputeOut)
def get_dispute(
    dispute_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> DisputeOut:
    rows = dispute_svc.list_mine(db, user)
    for row in rows:
        if row.id == dispute_id:
            return row
    from fastapi import HTTPException, status

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found")