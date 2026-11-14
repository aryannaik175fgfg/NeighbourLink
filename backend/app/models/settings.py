import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    notify_rentals: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_assistance: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_messages: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_community: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    default_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_radius_km: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="settings")