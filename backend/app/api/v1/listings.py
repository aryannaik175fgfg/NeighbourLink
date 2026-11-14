import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.models.rental_category import RentalCategory
from app.schemas.condition import ItemPhotoOut
from app.schemas.listings import (
    CategoryOut,
    ListingCreate,
    ListingOwner,
    ListingPublic,
    ListingSearchParams,
    ListingUpdate,
)
from app.services import item_photo_service as photo_svc
from app.services import listing_service as svc
from app.services.listing_service import _lat_lng_from_item, item_to_public

router = APIRouter(tags=["listings"])


@router.get("/rental-categories", response_model=list[CategoryOut])
def list_categories(db: Annotated[Session, Depends(get_db)]) -> list[CategoryOut]:
    cats = db.scalars(select(RentalCategory).order_by(RentalCategory.sort_order, RentalCategory.name)).all()
    return [CategoryOut.model_validate(c) for c in cats]


@router.get("/listings", response_model=list[ListingPublic])
def search_listings(
    db: Annotated[Session, Depends(get_db)],
    q: str | None = None,
    category: str | None = None,
    min_price_cents: int | None = Query(default=None, ge=0),
    max_price_cents: int | None = Query(default=None, ge=0),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float = Query(default=25, ge=0.5, le=200),
    sort: str = Query(default="relevance", pattern=r"^(relevance|price_asc|price_desc|distance)$"),
) -> list[ListingPublic]:
    params = ListingSearchParams(
        q=q,
        category=category,
        min_price_cents=min_price_cents,
        max_price_cents=max_price_cents,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        sort=sort,
    )
    return svc.search_listings(db, params)


@router.get("/listings/{listing_id}", response_model=ListingPublic)
def get_listing(listing_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> ListingPublic:
    return svc.get_listing_public(db, listing_id)


@router.post("/listings", response_model=ListingOwner, status_code=201)
def create_listing(
    body: ListingCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ListingOwner:
    item = svc.create_listing(db, user, body)
    lat, lng = _lat_lng_from_item(item, db)
    public = item_to_public(
        item,
        owner_name=user.profile.display_name,
        latitude=lat,
        longitude=lng,
    )
    return ListingOwner(
        **public.model_dump(),
        exact_address=item.exact_address,
        pickup_instructions=item.pickup_instructions,
    )


@router.get("/me/listings", response_model=list[ListingOwner])
def my_listings(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[ListingOwner]:
    items = svc.list_owned(db, user)
    result: list[ListingOwner] = []
    for item in items:
        lat, lng = _lat_lng_from_item(item, db)
        public = item_to_public(
            item,
            owner_name=user.profile.display_name,
            latitude=lat,
            longitude=lng,
        )
        result.append(
            ListingOwner(
                **public.model_dump(),
                exact_address=item.exact_address,
                pickup_instructions=item.pickup_instructions,
            )
        )
    return result


@router.post("/listings/{listing_id}/photos", response_model=ItemPhotoOut, status_code=201)
async def upload_listing_photo(
    listing_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
) -> ItemPhotoOut:
    return await photo_svc.upload_item_photo(db, user, listing_id, file)


@router.get("/listings/{listing_id}/photos", response_model=list[ItemPhotoOut])
def list_listing_photos(listing_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]) -> list[ItemPhotoOut]:
    return photo_svc.list_item_photos(db, listing_id)


@router.patch("/listings/{listing_id}", response_model=ListingOwner)
def update_listing(
    listing_id: uuid.UUID,
    body: ListingUpdate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ListingOwner:
    item = svc.update_listing(db, user, listing_id, body)
    lat, lng = _lat_lng_from_item(item, db)
    public = item_to_public(
        item,
        owner_name=user.profile.display_name,
        latitude=lat,
        longitude=lng,
    )
    return ListingOwner(
        **public.model_dump(),
        exact_address=item.exact_address,
        pickup_instructions=item.pickup_instructions,
    )