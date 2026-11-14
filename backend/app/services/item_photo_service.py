import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.condition_report import ItemPhoto
from app.models.item import Item
from app.models.user import User
from app.schemas.condition import ItemPhotoOut
from app.services.storage_service import save_upload


def _item_photo_url(object_key: str) -> str:
    return f"/api/v1/files/listing/{object_key}"


async def upload_item_photo(db: Session, user: User, item_id: uuid.UUID, file: UploadFile) -> ItemPhotoOut:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if item.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your listing")

    count = db.scalar(select(func.count()).select_from(ItemPhoto).where(ItemPhoto.item_id == item_id)) or 0
    if count >= 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 8 photos per listing")

    key, filename, size = await save_upload(file, prefix=f"listings/{item_id}")
    photo = ItemPhoto(
        item_id=item_id,
        object_key=key,
        original_filename=filename,
        content_type=file.content_type or "image/jpeg",
        byte_size=size,
        sort_order=int(count),
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return ItemPhotoOut(
        id=photo.id,
        url=_item_photo_url(photo.object_key),
        sort_order=photo.sort_order,
        original_filename=photo.original_filename,
    )


def list_item_photos(db: Session, item_id: uuid.UUID) -> list[ItemPhotoOut]:
    photos = db.scalars(select(ItemPhoto).where(ItemPhoto.item_id == item_id).order_by(ItemPhoto.sort_order)).all()
    return [
        ItemPhotoOut(
            id=p.id,
            url=_item_photo_url(p.object_key),
            sort_order=p.sort_order,
            original_filename=p.original_filename,
        )
        for p in photos
    ]