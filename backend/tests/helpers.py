import uuid

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.role import Role, UserRole
from app.models.user import User


def grant_role_by_email(email: str, role_slug: str) -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email.lower()))
        role = db.scalar(select(Role).where(Role.slug == role_slug))
        if user is None or role is None:
            raise RuntimeError("User or role missing")
        exists = db.scalar(
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
        )
        if exists is None:
            db.add(UserRole(user_id=user.id, role_id=role.id))
            db.commit()
    finally:
        db.close()


def grant_role_by_user_id(user_id: uuid.UUID, role_slug: str) -> None:
    db = SessionLocal()
    try:
        role = db.scalar(select(Role).where(Role.slug == role_slug))
        if role is None:
            raise RuntimeError("Role missing")
        exists = db.scalar(select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.id))
        if exists is None:
            db.add(UserRole(user_id=user_id, role_id=role.id))
            db.commit()
    finally:
        db.close()