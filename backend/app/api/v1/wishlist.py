import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.schemas.listings import ListingPublic
from app.services import wishlist_service as wl

router = APIRouter(tags=["wishlist"])


@router.get("/me/wishlist", response_model=list[ListingPublic])
def my_wishlist(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[ListingPublic]:
    return wl.list_saved(db, user)


@router.get("/me/wishlist/ids", response_model=list[uuid.UUID])
def my_wishlist_ids(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[uuid.UUID]:
    return wl.saved_ids(db, user)


@router.put("/me/wishlist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def save_item(
    item_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> Response:
    wl.add_saved(db, user, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me/wishlist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsave_item(
    item_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> Response:
    wl.remove_saved(db, user, item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)