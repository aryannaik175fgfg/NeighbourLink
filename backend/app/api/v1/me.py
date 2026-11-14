import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentSessionId, CurrentUser
from app.db.session import get_db
from app.schemas.identity import IdentityOut, IdentitySubmit
from app.schemas.session import SessionOut
from app.schemas.settings import ChangePasswordRequest, UserSettingsOut, UserSettingsUpdate
from app.schemas.user import MeResponse, ProfileOut, ProfileUpdate, RoleOut
from app.services import identity_service as id_svc
from app.services import session_service as sess_svc
from app.services import settings_service as sett_svc

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeResponse)
def read_me(user: CurrentUser) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        created_at=user.created_at,
        profile=ProfileOut.model_validate(user.profile),
        roles=[RoleOut.model_validate(r) for r in user.roles],
    )


@router.patch("/profile", response_model=ProfileOut)
def update_profile(
    body: ProfileUpdate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ProfileOut:
    profile = user.profile
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(profile, key, value)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return ProfileOut.model_validate(profile)


@router.get("/settings", response_model=UserSettingsOut)
def read_settings(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> UserSettingsOut:
    return sett_svc.get_settings_out(db, user)


@router.patch("/settings", response_model=UserSettingsOut)
def patch_settings(
    body: UserSettingsUpdate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> UserSettingsOut:
    return sett_svc.update_settings(db, user, body)


@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    sett_svc.change_password(db, user, body)


@router.get("/identity", response_model=IdentityOut | None)
def read_identity(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> IdentityOut | None:
    return id_svc.get_mine(db, user)


@router.post("/identity", response_model=IdentityOut, status_code=201)
def submit_identity(
    body: IdentitySubmit, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> IdentityOut:
    return id_svc.submit(db, user, body)


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    session_id: CurrentSessionId,
) -> list[SessionOut]:
    return sess_svc.list_sessions(db, user, current_session_id=session_id)


@router.delete("/sessions/{target_session_id}", status_code=204)
def revoke_session(
    target_session_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    session_id: CurrentSessionId,
) -> None:
    sess_svc.revoke_session(db, user, target_session_id, current_session_id=session_id)


@router.post("/sessions/revoke-others", status_code=204)
def revoke_other_sessions(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    session_id: CurrentSessionId,
) -> None:
    sess_svc.revoke_other_sessions(db, user, current_session_id=session_id)
