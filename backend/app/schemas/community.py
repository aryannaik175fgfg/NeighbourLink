import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CommunityPostCreate(BaseModel):
    kind: str = Field(pattern=r"^(recommendation|question|announcement)$")
    title: str = Field(min_length=3, max_length=160)
    body: str = Field(min_length=10, max_length=5000)
    area_label: str = Field(min_length=2, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    linked_listing_id: uuid.UUID | None = None


class CommunityCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class CommunityCommentOut(BaseModel):
    id: uuid.UUID
    author_name: str
    body: str
    is_mine: bool = False
    created_at: datetime


class CommunityReactionSet(BaseModel):
    reaction: str = Field(pattern=r"^(helpful|thanks)$")


class CommunityPostOut(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    body: str
    area_label: str
    author_name: str
    is_mine: bool = False
    linked_listing_id: uuid.UUID | None = None
    linked_listing_title: str | None = None
    helpful_count: int = 0
    thanks_count: int = 0
    my_reaction: str | None = None
    comment_count: int = 0
    created_at: datetime


class CommunityPostDetail(CommunityPostOut):
    comments: list[CommunityCommentOut] = []


class CommunityModerationHide(BaseModel):
    reason: str = Field(min_length=5, max_length=500)