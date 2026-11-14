import uuid

from fastapi import HTTPException, status
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint, ST_SetSRID
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.community import CommunityComment, CommunityPost, CommunityReaction
from app.models.item import Item, ItemStatus
from app.models.user import User
from app.schemas.community import (
    CommunityCommentCreate,
    CommunityCommentOut,
    CommunityPostCreate,
    CommunityPostDetail,
    CommunityPostOut,
    CommunityReactionSet,
)


def _point(lat: float, lng: float) -> WKTElement:
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def _reaction_counts(db: Session, post_id: uuid.UUID) -> tuple[int, int]:
    rows = db.execute(
        select(CommunityReaction.reaction, func.count())
        .where(CommunityReaction.post_id == post_id)
        .group_by(CommunityReaction.reaction)
    ).all()
    helpful = thanks = 0
    for reaction, count in rows:
        if reaction == "helpful":
            helpful = int(count)
        elif reaction == "thanks":
            thanks = int(count)
    return helpful, thanks


def _my_reaction(db: Session, post_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    row = db.get(CommunityReaction, (post_id, user_id))
    return row.reaction if row else None


def _comment_count(db: Session, post_id: uuid.UUID) -> int:
    c = db.scalar(
        select(func.count())
        .select_from(CommunityComment)
        .where(CommunityComment.post_id == post_id, CommunityComment.is_hidden.is_(False))
    )
    return int(c or 0)


def list_posts(
    db: Session,
    viewer: User | None,
    *,
    kind: str | None,
    latitude: float | None,
    longitude: float | None,
    radius_km: float,
    limit: int = 50,
    include_hidden: bool = False,
) -> list[CommunityPostOut]:
    stmt = select(CommunityPost).options(joinedload(CommunityPost.author).joinedload(User.profile)).limit(limit)
    if not include_hidden:
        stmt = stmt.where(CommunityPost.is_hidden.is_(False))
    if kind:
        stmt = stmt.where(CommunityPost.kind == kind)

    if latitude is not None and longitude is not None:
        origin = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        stmt = stmt.where(
            (CommunityPost.location.is_(None))
            | (ST_DWithin(CommunityPost.location, origin, radius_km * 1000))
        )
        stmt = stmt.order_by(ST_Distance(CommunityPost.location, origin).asc().nulls_last(), CommunityPost.created_at.desc())
    else:
        stmt = stmt.order_by(CommunityPost.created_at.desc())

    posts = db.scalars(stmt).unique().all()
    return [_post_out(db, p, viewer) for p in posts]


def get_post_detail(db: Session, viewer: User, post_id: uuid.UUID) -> CommunityPostDetail:
    post = db.scalar(
        select(CommunityPost)
        .where(CommunityPost.id == post_id)
        .options(
            joinedload(CommunityPost.author).joinedload(User.profile),
            joinedload(CommunityPost.comments).joinedload(CommunityComment.author).joinedload(User.profile),
        )
    )
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    is_admin = any(r.slug == "administrator" for r in viewer.roles)
    if post.is_hidden and not is_admin and post.author_id != viewer.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    base = _post_out(db, post, viewer)
    comments = [
        _comment_out(c, viewer)
        for c in post.comments
        if not c.is_hidden or c.author_id == viewer.id
    ]
    return CommunityPostDetail(**base.model_dump(), comments=comments)


def create_post(db: Session, user: User, data: CommunityPostCreate) -> CommunityPostOut:
    if data.linked_listing_id:
        item = db.get(Item, data.linked_listing_id)
        if item is None or item.status != ItemStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Linked listing not found or inactive")

    loc = None
    if data.latitude is not None and data.longitude is not None:
        loc = _point(data.latitude, data.longitude)
    post = CommunityPost(
        author_id=user.id,
        kind=data.kind,
        title=data.title.strip(),
        body=data.body.strip(),
        area_label=data.area_label.strip(),
        location=loc,
        linked_listing_id=data.linked_listing_id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    post = db.scalar(
        select(CommunityPost).where(CommunityPost.id == post.id).options(joinedload(CommunityPost.author).joinedload(User.profile))
    )
    assert post is not None
    return _post_out(db, post, user)


def add_comment(db: Session, user: User, post_id: uuid.UUID, data: CommunityCommentCreate) -> CommunityCommentOut:
    post = db.get(CommunityPost, post_id)
    if post is None or post.is_hidden:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    comment = CommunityComment(post_id=post_id, author_id=user.id, body=data.body.strip())
    db.add(comment)
    if post.author_id != user.id:
        from app.services import notification_service as notify_svc

        notify_svc.emit(
            db,
            post.author_id,
            kind="community",
            title="New comment on your post",
            body=data.body.strip()[:120],
            link_path="/app/community",
            dedupe_key=None,
        )
    db.commit()
    db.refresh(comment)
    author = db.get(User, user.id)
    return _comment_out(comment, user, author_name=author.profile.display_name if author and author.profile else "Neighbour")


def set_reaction(db: Session, user: User, post_id: uuid.UUID, data: CommunityReactionSet) -> CommunityPostOut:
    post = db.get(CommunityPost, post_id)
    if post is None or post.is_hidden:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    existing = db.get(CommunityReaction, (post_id, user.id))
    if existing and existing.reaction == data.reaction:
        db.delete(existing)
    elif existing:
        existing.reaction = data.reaction
        db.add(existing)
    else:
        db.add(CommunityReaction(post_id=post_id, user_id=user.id, reaction=data.reaction))
    db.commit()
    post = db.scalar(
        select(CommunityPost).where(CommunityPost.id == post_id).options(joinedload(CommunityPost.author).joinedload(User.profile))
    )
    assert post is not None
    return _post_out(db, post, user)


def hide_post(db: Session, admin: User, post_id: uuid.UUID, *, reason: str) -> CommunityPostOut:
    post = db.get(CommunityPost, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    post.is_hidden = True
    post.hidden_reason = reason.strip()
    db.add(post)
    from app.services import audit_service as audit_svc

    audit_svc.record(db, admin, action="community_hide", target_type="community_post", target_id=post_id, detail={"reason": reason})
    notify_author = post.author_id
    from app.services import notification_service as notify_svc

    notify_svc.emit(
        db,
        notify_author,
        kind="community",
        title="Post removed by moderation",
        body=reason[:200],
        link_path="/app/community",
        dedupe_key=f"mod-hide-{post_id}",
    )
    db.commit()
    post = db.scalar(
        select(CommunityPost).where(CommunityPost.id == post_id).options(joinedload(CommunityPost.author).joinedload(User.profile))
    )
    assert post is not None
    return _post_out(db, post, admin)


def list_all_posts_admin(db: Session, *, hidden_only: bool = False) -> list[CommunityPostOut]:
    stmt = select(CommunityPost).options(joinedload(CommunityPost.author).joinedload(User.profile)).order_by(
        CommunityPost.created_at.desc()
    )
    if hidden_only:
        stmt = stmt.where(CommunityPost.is_hidden.is_(True))
    else:
        stmt = stmt.where(CommunityPost.is_hidden.is_(False))
    posts = db.scalars(stmt).unique().all()
    return [_post_out(db, p, None) for p in posts]


def _post_out(db: Session, post: CommunityPost, viewer: User | None) -> CommunityPostOut:
    name = post.author.profile.display_name if post.author and post.author.profile else "Neighbour"
    helpful, thanks = _reaction_counts(db, post.id)
    my_r = _my_reaction(db, post.id, viewer.id) if viewer else None
    listing_title = None
    if post.linked_listing_id:
        item = db.get(Item, post.linked_listing_id)
        listing_title = item.title if item else None
    return CommunityPostOut(
        id=post.id,
        kind=post.kind,
        title=post.title,
        body=post.body,
        area_label=post.area_label,
        author_name=name,
        is_mine=viewer is not None and post.author_id == viewer.id,
        linked_listing_id=post.linked_listing_id,
        linked_listing_title=listing_title,
        helpful_count=helpful,
        thanks_count=thanks,
        my_reaction=my_r,
        comment_count=_comment_count(db, post.id),
        created_at=post.created_at,
    )


def _comment_out(comment: CommunityComment, viewer: User, *, author_name: str | None = None) -> CommunityCommentOut:
    name = author_name
    if name is None and comment.author and comment.author.profile:
        name = comment.author.profile.display_name
    name = name or "Neighbour"
    return CommunityCommentOut(
        id=comment.id,
        author_name=name,
        body=comment.body,
        is_mine=comment.author_id == viewer.id,
        created_at=comment.created_at,
    )