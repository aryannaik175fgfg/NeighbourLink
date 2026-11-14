import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.schemas.community import (
    CommunityCommentCreate,
    CommunityCommentOut,
    CommunityPostCreate,
    CommunityPostDetail,
    CommunityPostOut,
    CommunityReactionSet,
)
from app.services import community_service as comm

router = APIRouter(tags=["community"])


@router.get("/community/posts", response_model=list[CommunityPostOut])
def list_community_posts(
    db: Annotated[Session, Depends(get_db)],
    user: CurrentUser,
    kind: str | None = None,
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float = Query(default=25, ge=1, le=200),
) -> list[CommunityPostOut]:
    return comm.list_posts(db, user, kind=kind, latitude=latitude, longitude=longitude, radius_km=radius_km)


@router.post("/community/posts", response_model=CommunityPostOut, status_code=201)
def create_community_post(
    body: CommunityPostCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CommunityPostOut:
    return comm.create_post(db, user, body)


@router.get("/community/posts/{post_id}", response_model=CommunityPostDetail)
def get_post(
    post_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> CommunityPostDetail:
    return comm.get_post_detail(db, user, post_id)


@router.post("/community/posts/{post_id}/comments", response_model=CommunityCommentOut, status_code=201)
def add_comment(
    post_id: uuid.UUID,
    body: CommunityCommentCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CommunityCommentOut:
    return comm.add_comment(db, user, post_id, body)


@router.post("/community/posts/{post_id}/reactions", response_model=CommunityPostOut)
def react(
    post_id: uuid.UUID,
    body: CommunityReactionSet,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CommunityPostOut:
    return comm.set_reaction(db, user, post_id, body)