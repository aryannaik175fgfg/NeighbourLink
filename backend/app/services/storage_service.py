import mimetypes
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})


def storage_root() -> Path:
    root = Path(settings.storage_path)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[3] / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def validate_image_upload(file: UploadFile) -> str:
    content_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")
    return content_type


async def save_upload(file: UploadFile, *, prefix: str) -> tuple[str, str, int]:
    validate_image_upload(file)
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large")

    ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }.get(file.content_type or "", ".bin")

    object_key = f"{prefix}/{uuid.uuid4().hex}{ext}"
    full_path = storage_root() / object_key
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)
    filename = file.filename or f"upload{ext}"
    return object_key, filename, len(data)


def resolve_object_path(object_key: str) -> Path:
    full = (storage_root() / object_key).resolve()
    root = storage_root().resolve()
    if not str(full).startswith(str(root)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid object key")
    if not full.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return full