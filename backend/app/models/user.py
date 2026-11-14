import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False)
    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        back_populates="users",
        primaryjoin="User.id == UserRole.user_id",
        secondaryjoin="Role.id == UserRole.role_id",
    )
    items: Mapped[list["Item"]] = relationship(back_populates="owner")
    portfolio: Mapped["ProviderPortfolio | None"] = relationship(back_populates="user", uselist=False)
    settings: Mapped["UserSettings | None"] = relationship(back_populates="user", uselist=False)
    identity_verification: Mapped["UserIdentityVerification | None"] = relationship(
        back_populates="user", uselist=False, foreign_keys="UserIdentityVerification.user_id"
    )
