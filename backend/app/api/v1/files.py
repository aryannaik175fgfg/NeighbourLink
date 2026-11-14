from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.models.condition_report import ItemPhoto
from app.services import condition_service as cond_svc
from app.services.storage_service import resolve_object_path

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/listing/{object_key:path}")
def get_listing_photo(object_key: str, db: Annotated[Session, Depends(get_db)]) -> FileResponse:
    row = db.scalar(select(ItemPhoto).where(ItemPhoto.object_key == object_key))
    if row is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    path = resolve_object_path(object_key)
    return FileResponse(path, media_type=row.content_type)


@router.get("/condition/{object_key:path}")
def get_condition_photo(
    object_key: str,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    if not cond_svc.can_access_condition_file(db, user, object_key):
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    from app.models.condition_report import ConditionReportPhoto

    row = db.scalar(select(ConditionReportPhoto).where(ConditionReportPhoto.object_key == object_key))
    media = row.content_type if row else "application/octet-stream"
    path = resolve_object_path(object_key)
    return FileResponse(path, media_type=media)