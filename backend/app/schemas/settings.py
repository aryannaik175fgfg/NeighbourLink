from pydantic import BaseModel, Field


class UserSettingsOut(BaseModel):
    notify_rentals: bool
    notify_assistance: bool
    notify_messages: bool
    notify_community: bool
    preferred_locale: str
    default_latitude: float | None
    default_longitude: float | None
    default_radius_km: int

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    notify_rentals: bool | None = None
    notify_assistance: bool | None = None
    notify_messages: bool | None = None
    notify_community: bool | None = None
    preferred_locale: str | None = Field(default=None, pattern=r"^(en|hi|mr)$")
    default_latitude: float | None = Field(default=None, ge=-90, le=90)
    default_longitude: float | None = Field(default=None, ge=-180, le=180)
    default_radius_km: int | None = Field(default=None, ge=1, le=200)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)