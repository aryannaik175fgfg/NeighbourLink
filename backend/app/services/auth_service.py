import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)
from app.models.profile import Profile
from app.models.role import Role
from app.models.session import Session as UserSession
from app.models.user import User


def register_user(db: Session, *, email: str, password: str, display_name: str) -> User:
    existing = db.scalar(select(User).where(User.email == email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    customer_role = db.scalar(select(Role).where(Role.slug == "customer"))
    if customer_role is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Roles not seeded; run python -m app.seed_roles",
        )

    user = User(email=email.lower(), password_hash=hash_password(password))
    user.profile = Profile(display_name=display_name.strip())
    user.roles.append(customer_role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return user


def create_session(db: Session, user: User, user_agent: str | None) -> tuple[str, str, UserSession]:
    refresh = new_refresh_token()
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        user_agent=user_agent,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    access = create_access_token(user_id=user.id, session_id=session.id)
    return access, refresh, session


def refresh_tokens(db: Session, refresh_token: str) -> tuple[str, str]:
    token_hash = hash_refresh_token(refresh_token)
    session = db.scalar(select(UserSession).where(UserSession.refresh_token_hash == token_hash))
    if session is None or session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if session.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    session.revoked_at = datetime.now(UTC)
    new_refresh = new_refresh_token()
    new_session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(new_refresh),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        user_agent=session.user_agent,
    )
    db.add(new_session)
    db.commit()
    access = create_access_token(user_id=user.id, session_id=new_session.id)
    return access, new_refresh


def logout_session(db: Session, session_id: uuid.UUID) -> None:
    session = db.get(UserSession, session_id)
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        db.commit()
