from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.settings import UserSettings
from app.models.user import User
from app.schemas.settings import ChangePasswordRequest, UserSettingsOut, UserSettingsUpdate


def get_or_create_settings(db: Session, user: User) -> UserSettings:
    if user.settings is not None:
        return user.settings
    settings = db.get(UserSettings, user.id)
    if settings is None:
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def get_settings_out(db: Session, user: User) -> UserSettingsOut:
    s = get_or_create_settings(db, user)
    return UserSettingsOut(
        notify_rentals=s.notify_rentals,
        notify_assistance=s.notify_assistance,
        notify_messages=s.notify_messages,
        notify_community=s.notify_community,
        preferred_locale=user.profile.preferred_locale,
        default_latitude=s.default_latitude,
        default_longitude=s.default_longitude,
        default_radius_km=s.default_radius_km,
    )


def update_settings(db: Session, user: User, body: UserSettingsUpdate) -> UserSettingsOut:
    s = get_or_create_settings(db, user)
    data = body.model_dump(exclude_unset=True)
    locale = data.pop("preferred_locale", None)
    if locale is not None:
        user.profile.preferred_locale = locale
        db.add(user.profile)
    for key, value in data.items():
        setattr(s, key, value)
    db.add(s)
    db.commit()
    db.refresh(s)
    db.refresh(user.profile)
    return get_settings_out(db, user)


def change_password(db: Session, user: User, body: ChangePasswordRequest) -> None:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    db.add(user)
    db.commit()


def notification_allowed(db: Session, user_id, kind: str) -> bool:
    from uuid import UUID

    uid = user_id if isinstance(user_id, UUID) else UUID(str(user_id))
    s = db.get(UserSettings, uid)
    if s is None:
        return True
    if kind in ("rental_payment",):
        return s.notify_rentals
    if kind in ("service_payment", "service_offer", "skill_verification"):
        return s.notify_assistance
    if kind == "message":
        return s.notify_messages
    if kind in ("identity", "dispute", "supervision"):
        return s.notify_rentals or s.notify_assistance
    if kind == "community":
        return s.notify_community
    return True