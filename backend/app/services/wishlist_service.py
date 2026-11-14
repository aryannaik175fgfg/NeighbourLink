import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.item import Item
from app.models.user import User
from app.models.wishlist import RentalWishlistItem
from app.schemas.listings import ListingPublic
from app.services.listing_service import _lat_lng_from_item, _photo_urls, item_to_public


def list_saved(db: Session, user: User) -> list[ListingPublic]:
    items = db.scalars(
        select(Item)
        .join(RentalWishlistItem, RentalWishlistItem.item_id == Item.id)
        .where(RentalWishlistItem.user_id == user.id)
        .options(joinedload(Item.category), joinedload(Item.owner).joinedload(User.profile))
        .order_by(RentalWishlistItem.created_at.desc())
    ).all()
    out: list[ListingPublic] = []
    for item in items:
        lat, lng = _lat_lng_from_item(item, db)
        out.append(
            item_to_public(
                item,
                owner_name=item.owner.profile.display_name,
                latitude=lat,
                longitude=lng,
                photo_urls=_photo_urls(db, item.id),
            )
        )
    return out


def saved_ids(db: Session, user: User) -> list[uuid.UUID]:
    return list(
        db.scalars(select(RentalWishlistItem.item_id).where(RentalWishlistItem.user_id == user.id).order_by(RentalWishlistItem.created_at.desc()))
    )


def add_saved(db: Session, user: User, item_id: uuid.UUID) -> None:
    item = db.get(Item, item_id)
    if item is None or item.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if item.owner_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot save your own listing")
    existing = db.get(RentalWishlistItem, (user.id, item_id))
    if existing:
        return
    db.add(RentalWishlistItem(user_id=user.id, item_id=item_id))
    db.commit()


def remove_saved(db: Session, user: User, item_id: uuid.UUID) -> None:
    row = db.get(RentalWishlistItem, (user.id, item_id))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in saved items")
    db.delete(row)
    db.commit()