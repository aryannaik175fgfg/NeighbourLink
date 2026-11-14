import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_roles
from app.db.session import get_db
from app.schemas.admin import SkillVerificationDecision, SkillVerificationOut
from app.schemas.community import CommunityModerationHide, CommunityPostOut
from app.schemas.audit import AuditLogOut
from app.schemas.dispute import DisputeOut, DisputeResolve
from app.schemas.identity import IdentityAdminRow, IdentityDecision, IdentityOut
from app.services import admin_service as admin_svc
from app.services import audit_service as audit_svc
from app.services import dispute_service as dispute_svc
from app.services import community_service as comm_svc
from app.services import identity_service as id_svc

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/skill-verifications",
    response_model=list[SkillVerificationOut],
    dependencies=[Depends(require_roles("administrator"))],
)
def list_skill_verifications(
    db: Annotated[Session, Depends(get_db)],
    status: str | None = Query(default="pending"),
) -> list[SkillVerificationOut]:
    return admin_svc.list_skill_verifications(db, status_filter=status)


@router.post(
    "/skill-verifications/{portfolio_user_id}/{category_id}",
    response_model=SkillVerificationOut,
    dependencies=[Depends(require_roles("administrator"))],
)
def decide_skill_verification(
    portfolio_user_id: uuid.UUID,
    category_id: uuid.UUID,
    body: SkillVerificationDecision,
    admin: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> SkillVerificationOut:
    return admin_svc.review_skill(db, admin, portfolio_user_id, category_id, body)


@router.get(
    "/identity-verifications",
    response_model=list[IdentityAdminRow],
    dependencies=[Depends(require_roles("administrator"))],
)
def list_identity_queue(
    db: Annotated[Session, Depends(get_db)],
    status: str | None = Query(default="pending"),
) -> list[IdentityAdminRow]:
    return id_svc.list_for_admin(db, status_filter=status)


@router.post(
    "/identity-verifications/{user_id}",
    response_model=IdentityOut,
    dependencies=[Depends(require_roles("administrator"))],
)
def decide_identity(
    user_id: uuid.UUID,
    body: IdentityDecision,
    admin: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> IdentityOut:
    return id_svc.decide(db, admin, user_id, body)


@router.get(
    "/disputes",
    response_model=list[DisputeOut],
    dependencies=[Depends(require_roles("administrator"))],
)
def list_disputes(
    db: Annotated[Session, Depends(get_db)],
    status: str | None = Query(default=None),
) -> list[DisputeOut]:
    return dispute_svc.list_admin(db, status_filter=status)


@router.patch(
    "/disputes/{dispute_id}",
    response_model=DisputeOut,
    dependencies=[Depends(require_roles("administrator"))],
)
def resolve_dispute(
    dispute_id: uuid.UUID,
    body: DisputeResolve,
    admin: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> DisputeOut:
    return dispute_svc.resolve_dispute(db, admin, dispute_id, body)


@router.get(
    "/audit-log",
    response_model=list[AuditLogOut],
    dependencies=[Depends(require_roles("administrator"))],
)
def audit_log(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditLogOut]:
    return audit_svc.list_recent(db, limit=limit)


@router.get(
    "/community/posts",
    response_model=list[CommunityPostOut],
    dependencies=[Depends(require_roles("administrator"))],
)
def admin_community_posts(
    db: Annotated[Session, Depends(get_db)],
    hidden_only: bool = Query(default=False),
) -> list[CommunityPostOut]:
    return comm_svc.list_all_posts_admin(db, hidden_only=hidden_only)


@router.post(
    "/community/posts/{post_id}/hide",
    response_model=CommunityPostOut,
    dependencies=[Depends(require_roles("administrator"))],
)
def hide_community_post(
    post_id: uuid.UUID,
    body: CommunityModerationHide,
    admin: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CommunityPostOut:
    return comm_svc.hide_post(db, admin, post_id, reason=body.reason)