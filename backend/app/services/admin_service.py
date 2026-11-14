import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.assistance import (
    PortfolioServiceCategory,
    ProviderPortfolio,
    ServiceCategory,
    SkillVerificationStatus,
)
from app.models.user import User
from app.schemas.admin import SkillVerificationDecision, SkillVerificationOut


def list_skill_verifications(
    db: Session, *, status_filter: str | None = "pending"
) -> list[SkillVerificationOut]:
    stmt = (
        select(PortfolioServiceCategory)
        .join(ServiceCategory)
        .join(ProviderPortfolio)
        .options(
            joinedload(PortfolioServiceCategory.category),
            joinedload(PortfolioServiceCategory.portfolio).joinedload(ProviderPortfolio.user).joinedload(User.profile),
        )
        .where(ServiceCategory.requires_verification.is_(True))
    )
    if status_filter:
        stmt = stmt.where(PortfolioServiceCategory.verification_status == status_filter)
    stmt = stmt.order_by(PortfolioServiceCategory.portfolio_user_id)
    links = db.scalars(stmt).unique().all()
    return [_link_out(link) for link in links]


def review_skill(
    db: Session,
    admin: User,
    portfolio_user_id: uuid.UUID,
    category_id: uuid.UUID,
    body: SkillVerificationDecision,
) -> SkillVerificationOut:
    link = db.get(PortfolioServiceCategory, (portfolio_user_id, category_id))
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill claim not found")
    cat = db.get(ServiceCategory, category_id)
    if cat is None or not cat.requires_verification:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category does not require verification")
    if link.verification_status not in (SkillVerificationStatus.PENDING, SkillVerificationStatus.REJECTED):
        if body.approve and link.verification_status == SkillVerificationStatus.APPROVED:
            return _link_out(link)

    if body.approve:
        link.verification_status = SkillVerificationStatus.APPROVED
        link.admin_note = body.note.strip() if body.note else None
    else:
        if not body.note or len(body.note.strip()) < 5:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejection requires a short note")
        link.verification_status = SkillVerificationStatus.REJECTED
        link.admin_note = body.note.strip()

    link.reviewed_at = datetime.now(UTC)
    link.reviewed_by = admin.id
    db.add(link)
    from app.services import audit_service as audit_svc
    from app.services import notification_service as notify_svc

    audit_svc.record(
        db,
        admin,
        action="skill_verification",
        target_type="portfolio_category",
        target_id=f"{portfolio_user_id}:{category_id}",
        detail={"approve": body.approve, "note": link.admin_note},
    )

    if body.approve:
        notify_svc.emit(
            db,
            portfolio_user_id,
            kind="skill_verification",
            title=f"{cat.name} skill approved",
            body="You can now bid on regulated jobs in this category.",
            link_path="/app/assistance/open-jobs",
            dedupe_key=f"skill-approved-{portfolio_user_id}-{category_id}",
        )
    else:
        notify_svc.emit(
            db,
            portfolio_user_id,
            kind="skill_verification",
            title=f"{cat.name} skill not approved",
            body=link.admin_note or "See admin note on your portfolio.",
            link_path="/app/assistance/portfolio",
            dedupe_key=f"skill-rejected-{portfolio_user_id}-{category_id}",
        )
    db.commit()
    link = db.scalar(
        select(PortfolioServiceCategory)
        .where(
            PortfolioServiceCategory.portfolio_user_id == portfolio_user_id,
            PortfolioServiceCategory.category_id == category_id,
        )
        .options(
            joinedload(PortfolioServiceCategory.category),
            joinedload(PortfolioServiceCategory.portfolio).joinedload(ProviderPortfolio.user).joinedload(User.profile),
        )
    )
    assert link is not None
    return _link_out(link)


def _link_out(link: PortfolioServiceCategory) -> SkillVerificationOut:
    provider = link.portfolio.user
    return SkillVerificationOut(
        portfolio_user_id=link.portfolio_user_id,
        category_id=link.category_id,
        category_slug=link.category.slug,
        category_name=link.category.name,
        provider_name=provider.profile.display_name,
        provider_headline=link.portfolio.headline,
        verification_status=link.verification_status,
        admin_note=link.admin_note,
        reviewed_at=link.reviewed_at,
    )