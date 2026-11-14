import uuid
from math import isfinite

from fastapi import HTTPException, status
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint, ST_SetSRID
from geoalchemy2.types import Geometry
from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.condition_report import ItemPhoto
from app.models.item import Item, ItemStatus
from app.models.rental_category import RentalCategory
from app.models.role import Role
from app.models.user import User
from app.schemas.listings import ListingCreate, ListingPublic, ListingSearchParams, ListingUpdate


def _point_wkt(latitude: float, longitude: float) -> WKTElement:
    if not isfinite(latitude) or not isfinite(longitude):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid coordinates")
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


def ensure_item_owner_role(db: Session, user: User) -> None:
    if any(r.slug == "item_owner" for r in user.roles):
        return
    role = db.scalar(select(Role).where(Role.slug == "item_owner"))
    if role is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Roles not seeded")
    user.roles.append(role)
    db.add(user)


def _location_geom():
    return cast(Item.location, Geometry(geometry_type="POINT", srid=4326))


def _lat_lng_from_item(item: Item, db: Session) -> tuple[float, float]:
    geom = _location_geom()
    row = db.execute(
        select(
            func.ST_Y(geom).label("lat"),
            func.ST_X(geom).label("lng"),
        ).where(Item.id == item.id)
    ).one()
    return float(row.lat), float(row.lng)


def _photo_urls(db: Session, item_id: uuid.UUID) -> list[str]:
    photos = db.scalars(select(ItemPhoto).where(ItemPhoto.item_id == item_id).order_by(ItemPhoto.sort_order)).all()
    return [f"/api/v1/files/listing/{p.object_key}" for p in photos]


def item_to_public(
    item: Item,
    *,
    owner_name: str,
    latitude: float,
    longitude: float,
    distance_meters: float | None = None,
    photo_urls: list[str] | None = None,
) -> ListingPublic:
    return ListingPublic(
        id=item.id,
        title=item.title,
        description=item.description,
        condition=item.condition,
        daily_price_cents=item.daily_price_cents,
        deposit_cents=item.deposit_cents,
        status=item.status,
        public_area_label=item.public_area_label,
        category=item.category,
        owner_display_name=owner_name,
        latitude=round(latitude, 4),
        longitude=round(longitude, 4),
        distance_meters=round(distance_meters, 1) if distance_meters is not None else None,
        created_at=item.created_at,
        photo_urls=photo_urls or [],
    )


def create_listing(db: Session, user: User, data: ListingCreate) -> Item:
    category = db.scalar(select(RentalCategory).where(RentalCategory.slug == data.category_slug))
    if category is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown category")

    ensure_item_owner_role(db, user)

    item = Item(
        owner_id=user.id,
        category_id=category.id,
        title=data.title.strip(),
        description=data.description.strip(),
        condition=data.condition.value,
        daily_price_cents=data.daily_price_cents,
        deposit_cents=data.deposit_cents,
        status=ItemStatus.ACTIVE,
        public_area_label=data.public_area_label.strip(),
        exact_address=data.exact_address.strip() if data.exact_address else None,
        pickup_instructions=data.pickup_instructions.strip() if data.pickup_instructions else None,
        location=_point_wkt(data.latitude, data.longitude),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    item = db.scalar(
        select(Item).where(Item.id == item.id).options(joinedload(Item.category), joinedload(Item.owner).joinedload(User.profile))
    )
    assert item is not None
    return item


def search_listings(db: Session, params: ListingSearchParams) -> list[ListingPublic]:
    stmt = (
        select(Item)
        .join(RentalCategory)
        .join(User, Item.owner_id == User.id)
        .options(joinedload(Item.category), joinedload(Item.owner).joinedload(User.profile))
        .where(Item.status == ItemStatus.ACTIVE)
    )

    if params.category:
        stmt = stmt.where(RentalCategory.slug == params.category)

    if params.q:
        like = f"%{params.q.strip()}%"
        stmt = stmt.where(or_(Item.title.ilike(like), Item.description.ilike(like)))

    if params.min_price_cents is not None:
        stmt = stmt.where(Item.daily_price_cents >= params.min_price_cents)
    if params.max_price_cents is not None:
        stmt = stmt.where(Item.daily_price_cents <= params.max_price_cents)

    distance_m = None
    if params.latitude is not None and params.longitude is not None:
        origin = ST_SetSRID(ST_MakePoint(params.longitude, params.latitude), 4326)
        radius_m = (params.radius_km or 25) * 1000
        stmt = stmt.where(ST_DWithin(Item.location, origin, radius_m))
        distance_m = ST_Distance(Item.location, origin)

    if params.sort == "price_asc":
        stmt = stmt.order_by(Item.daily_price_cents.asc())
    elif params.sort == "price_desc":
        stmt = stmt.order_by(Item.daily_price_cents.desc())
    elif params.sort == "distance" and distance_m is not None:
        stmt = stmt.order_by(distance_m.asc())
    else:
        stmt = stmt.order_by(Item.created_at.desc())

    stmt = stmt.limit(100)
    items = db.scalars(stmt).unique().all()
    results: list[ListingPublic] = []
    origin = None
    if params.latitude is not None and params.longitude is not None:
        origin = ST_SetSRID(ST_MakePoint(params.longitude, params.latitude), 4326)

    for item in items:
        lat, lng = _lat_lng_from_item(item, db)
        urls = _photo_urls(db, item.id)
        dist = None
        if origin is not None:
            dist = db.scalar(select(ST_Distance(Item.location, origin)).where(Item.id == item.id))
            dist = float(dist) if dist is not None else None
        results.append(
            item_to_public(
                item,
                owner_name=item.owner.profile.display_name,
                latitude=lat,
                longitude=lng,
                distance_meters=dist,
                photo_urls=urls,
            )
        )

    if params.sort == "distance" and origin is not None:
        results.sort(key=lambda x: x.distance_meters if x.distance_meters is not None else 1e12)

    return results


def get_listing_public(db: Session, listing_id: uuid.UUID) -> ListingPublic:
    item = db.scalar(
        select(Item)
        .where(Item.id == listing_id, Item.status == ItemStatus.ACTIVE)
        .options(joinedload(Item.category), joinedload(Item.owner).joinedload(User.profile))
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    lat, lng = _lat_lng_from_item(item, db)
    return item_to_public(
        item,
        owner_name=item.owner.profile.display_name,
        latitude=lat,
        longitude=lng,
        photo_urls=_photo_urls(db, item.id),
    )


def list_owned(db: Session, user: User) -> list[Item]:
    return list(
        db.scalars(
            select(Item)
            .where(Item.owner_id == user.id)
            .options(joinedload(Item.category))
            .order_by(Item.created_at.desc())
        ).all()
    )


def update_listing(db: Session, user: User, listing_id: uuid.UUID, data: ListingUpdate) -> Item:
    item = db.scalar(select(Item).where(Item.id == listing_id).options(joinedload(Item.category)))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if item.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your listing")

    payload = data.model_dump(exclude_unset=True)
    lat = payload.pop("latitude", None)
    lng = payload.pop("longitude", None)
    for key, value in payload.items():
        if hasattr(value, "value"):
            value = value.value
        setattr(item, key, value.strip() if isinstance(value, str) else value)
    if lat is not None and lng is not None:
        item.location = _point_wkt(lat, lng)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item