from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.deps import CurrentUser, bearer_scheme
from app.core.security import decode_access_token
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
    user_agent: Annotated[str | None, Header(alias="User-Agent")] = None,
) -> TokenResponse:
    user = auth_service.register_user(
        db, email=body.email, password=body.password, display_name=body.display_name
    )
    access, refresh, _ = auth_service.create_session(db, user, user_agent)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    user_agent: Annotated[str | None, Header(alias="User-Agent")] = None,
) -> TokenResponse:
    user = auth_service.authenticate_user(db, email=body.email, password=body.password)
    access, refresh, _ = auth_service.create_session(db, user, user_agent)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    access, new_refresh = auth_service.refresh_tokens(db, body.refresh_token)
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    _user: CurrentUser,
    credentials: Annotated[object | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)  # type: ignore[union-attr]
        session_id = payload.get("sid")
        if session_id:
            import uuid

            auth_service.logout_session(db, uuid.UUID(session_id))
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
