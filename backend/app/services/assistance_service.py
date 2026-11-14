import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from app.core.config import settings
from geoalchemy2.elements import WKTElement
from geoalchemy2.functions import ST_DWithin, ST_Distance, ST_MakePoint, ST_SetSRID
from sqlalchemy import cast, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.assistance import (
    AssistanceReview,
    OfferStatus,
    ProviderPortfolio,
    PortfolioServiceCategory,
    ServiceCategory,
    ServiceJob,
    ServiceJobEvent,
    ServiceJobStatus,
    ServiceOffer,
    ServiceRequest,
    ServiceRequestStatus,
    SkillVerificationStatus,
)
from app.services import message_service as msg_svc
from app.services.provider_ratings import provider_rating_aggregate
from app.models.role import Role
from app.models.user import User
from app.schemas.assistance import (
    AssistanceReviewCreate,
    AssistanceReviewOut,
    OfferCreate,
    OfferOut,
    PortfolioCreate,
    ProviderPublic,
    ServiceJobEventOut,
    ServiceJobOut,
    ServiceRequestCreate,
    ServiceRequestOut,
)
from geoalchemy2.types import Geometry


def _point_wkt(lat: float, lng: float) -> WKTElement:
    return WKTElement(f"POINT({lng} {lat})", srid=4326)


def record_job_event(
    db: Session,
    job: ServiceJob,
    *,
    event_type: str,
    summary: str,
    actor_id: uuid.UUID | None = None,
) -> None:
    db.add(
        ServiceJobEvent(
            job_id=job.id,
            event_type=event_type,
            summary=summary,
            actor_id=actor_id,
        )
    )


def expire_stale_service_holds(db: Session) -> int:
    now = datetime.now(UTC)
    jobs = db.scalars(
        select(ServiceJob).where(
            ServiceJob.status == ServiceJobStatus.AWAITING_PAYMENT,
            ServiceJob.hold_expires_at.is_not(None),
            ServiceJob.hold_expires_at < now,
        )
    ).all()
    count = 0
    for job in jobs:
        job.status = ServiceJobStatus.CANCELLED
        db.add(job)
        req = db.get(ServiceRequest, job.request_id)
        if req and req.status == ServiceRequestStatus.CONFIRMED:
            req.status = ServiceRequestStatus.CANCELLED
            db.add(req)
        record_job_event(db, job, event_type="hold_expired", summary="Payment hold expired; job cancelled")
        count += 1
    if count:
        db.commit()
    return count


def _portfolio_lat_lng(db: Session, user_id: uuid.UUID) -> tuple[float, float]:
    geom = cast(ProviderPortfolio.location, Geometry(geometry_type="POINT", srid=4326))
    row = db.execute(
        select(func.ST_Y(geom).label("lat"), func.ST_X(geom).label("lng")).where(ProviderPortfolio.user_id == user_id)
    ).one()
    return float(row.lat), float(row.lng)


def ensure_provider_role(db: Session, user: User) -> None:
    if any(r.slug == "provider" for r in user.roles):
        return
    role = db.scalar(select(Role).where(Role.slug == "provider"))
    if role is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Roles not seeded")
    user.roles.append(role)
    db.add(user)


def upsert_portfolio(db: Session, user: User, data: PortfolioCreate) -> ProviderPortfolio:
    cats = db.scalars(select(ServiceCategory).where(ServiceCategory.slug.in_(data.category_slugs))).all()
    if len(cats) != len(set(data.category_slugs)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown service category")

    ensure_provider_role(db, user)
    portfolio = db.get(ProviderPortfolio, user.id)
    if portfolio is None:
        portfolio = ProviderPortfolio(
            user_id=user.id,
            headline=data.headline.strip(),
            introduction=data.introduction.strip(),
            service_area_label=data.service_area_label.strip(),
            location=_point_wkt(data.latitude, data.longitude),
        )
        db.add(portfolio)
    else:
        portfolio.headline = data.headline.strip()
        portfolio.introduction = data.introduction.strip()
        portfolio.service_area_label = data.service_area_label.strip()
        portfolio.location = _point_wkt(data.latitude, data.longitude)

    db.flush()

    prev_links = {
        link.category_id: link
        for link in db.scalars(
            select(PortfolioServiceCategory).where(PortfolioServiceCategory.portfolio_user_id == user.id)
        ).all()
    }
    db.execute(
        PortfolioServiceCategory.__table__.delete().where(PortfolioServiceCategory.portfolio_user_id == user.id)
    )
    for cat in cats:
        prev = prev_links.get(cat.id)
        if cat.requires_verification:
            if prev and prev.verification_status == SkillVerificationStatus.APPROVED:
                v_status = SkillVerificationStatus.APPROVED
                admin_note = prev.admin_note
                reviewed_at = prev.reviewed_at
                reviewed_by = prev.reviewed_by
            else:
                v_status = SkillVerificationStatus.PENDING
                admin_note = None
                reviewed_at = None
                reviewed_by = None
        else:
            v_status = SkillVerificationStatus.NOT_REQUIRED
            admin_note = None
            reviewed_at = None
            reviewed_by = None
        db.add(
            PortfolioServiceCategory(
                portfolio_user_id=user.id,
                category_id=cat.id,
                verification_status=v_status,
                admin_note=admin_note,
                reviewed_at=reviewed_at,
                reviewed_by=reviewed_by,
            )
        )

    db.commit()
    db.refresh(portfolio)
    portfolio = db.scalar(
        select(ProviderPortfolio)
        .where(ProviderPortfolio.user_id == user.id)
        .options(joinedload(ProviderPortfolio.categories), joinedload(ProviderPortfolio.user).joinedload(User.profile))
    )
    assert portfolio is not None
    return portfolio


def search_providers(
    db: Session,
    *,
    category: str | None,
    latitude: float | None,
    longitude: float | None,
    radius_km: float,
) -> list[ProviderPublic]:
    stmt = (
        select(ProviderPortfolio)
        .join(User, ProviderPortfolio.user_id == User.id)
        .options(joinedload(ProviderPortfolio.categories), joinedload(ProviderPortfolio.user).joinedload(User.profile))
        .where(ProviderPortfolio.is_active.is_(True))
    )
    if category:
        stmt = stmt.join(PortfolioServiceCategory, PortfolioServiceCategory.portfolio_user_id == ProviderPortfolio.user_id)
        stmt = stmt.join(ServiceCategory).where(ServiceCategory.slug == category)
        stmt = stmt.where(
            (ServiceCategory.requires_verification.is_(False))
            | (PortfolioServiceCategory.verification_status == SkillVerificationStatus.APPROVED)
        )

    origin = None
    if latitude is not None and longitude is not None:
        origin = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        stmt = stmt.where(ST_DWithin(ProviderPortfolio.location, origin, radius_km * 1000))
        stmt = stmt.order_by(ST_Distance(ProviderPortfolio.location, origin).asc())
    else:
        stmt = stmt.order_by(ProviderPortfolio.created_at.desc())

    portfolios = db.scalars(stmt.limit(50)).unique().all()
    results: list[ProviderPublic] = []
    for p in portfolios:
        lat, lng = _portfolio_lat_lng(db, p.user_id)
        dist = None
        if origin is not None:
            dist = db.scalar(
                select(ST_Distance(ProviderPortfolio.location, origin)).where(ProviderPortfolio.user_id == p.user_id)
            )
            dist = float(dist) if dist is not None else None
        avg, count = provider_rating_aggregate(db, p.user_id)
        results.append(
            ProviderPublic(
                user_id=p.user_id,
                display_name=p.user.profile.display_name,
                headline=p.headline,
                introduction=p.introduction,
                service_area_label=p.service_area_label,
                latitude=round(lat, 4),
                longitude=round(lng, 4),
                categories=p.categories,
                assistance_rating=avg,
                assistance_rating_count=count,
                distance_meters=round(dist, 1) if dist is not None else None,
            )
        )
    return results


def create_request(db: Session, user: User, data: ServiceRequestCreate) -> ServiceRequest:
    cat = db.scalar(select(ServiceCategory).where(ServiceCategory.slug == data.category_slug))
    if cat is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown category")
    req = ServiceRequest(
        customer_id=user.id,
        category_id=cat.id,
        title=data.title.strip(),
        description=data.description.strip(),
        service_area_label=data.service_area_label.strip(),
        location=_point_wkt(data.latitude, data.longitude),
        budget_cents=data.budget_cents,
        status=ServiceRequestStatus.PUBLISHED,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def request_to_out(db: Session, req: ServiceRequest) -> ServiceRequestOut:
    req = db.scalar(
        select(ServiceRequest).where(ServiceRequest.id == req.id).options(joinedload(ServiceRequest.category))
    )
    assert req is not None
    offer_count = db.scalar(select(func.count()).select_from(ServiceOffer).where(ServiceOffer.request_id == req.id)) or 0
    return ServiceRequestOut(
        id=req.id,
        title=req.title,
        description=req.description,
        status=req.status,
        service_area_label=req.service_area_label,
        budget_cents=req.budget_cents,
        category=req.category,
        offer_count=int(offer_count),
        created_at=req.created_at,
    )


def submit_offer(db: Session, user: User, request_id: uuid.UUID, data: OfferCreate) -> ServiceOffer:
    if db.get(ProviderPortfolio, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Create a provider portfolio first")

    from app.services import supervision_service as sup_svc

    if any(r.slug == "trainee" for r in user.roles) and not sup_svc.trainee_has_active_supervision(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trainees need an active supervisor before bidding on jobs",
        )

    req = db.scalar(
        select(ServiceRequest).where(ServiceRequest.id == request_id).options(joinedload(ServiceRequest.category))
    )
    if req is None or req.status != ServiceRequestStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not open for offers")
    if req.customer_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot offer on your own request")

    if req.category.requires_verification:
        link = db.scalar(
            select(PortfolioServiceCategory).where(
                PortfolioServiceCategory.portfolio_user_id == user.id,
                PortfolioServiceCategory.category_id == req.category_id,
            )
        )
        if link is None or link.verification_status != SkillVerificationStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This skill category requires administrator verification before bidding",
            )

    existing = db.scalar(
        select(ServiceOffer).where(ServiceOffer.request_id == request_id, ServiceOffer.provider_id == user.id)
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already submitted an offer")

    offer = ServiceOffer(
        request_id=request_id,
        provider_id=user.id,
        price_cents=data.price_cents,
        included_work=data.included_work.strip(),
        excluded_work=data.excluded_work.strip() if data.excluded_work else None,
        estimated_days=data.estimated_days,
        status=OfferStatus.PENDING,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def offer_to_out(db: Session, offer: ServiceOffer) -> OfferOut:
    provider = db.scalar(select(User).where(User.id == offer.provider_id).options(joinedload(User.profile)))
    return OfferOut(
        id=offer.id,
        provider_id=offer.provider_id,
        provider_name=provider.profile.display_name if provider else "Provider",
        price_cents=offer.price_cents,
        included_work=offer.included_work,
        excluded_work=offer.excluded_work,
        estimated_days=offer.estimated_days,
        status=offer.status,
        created_at=offer.created_at,
    )


def accept_offer(db: Session, user: User, offer_id: uuid.UUID) -> ServiceJob:
    offer = db.scalar(
        select(ServiceOffer).where(ServiceOffer.id == offer_id).options(joinedload(ServiceOffer.request))
    )
    if offer is None or offer.status != OfferStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not available")
    req = offer.request
    if req.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your request")
    if req.status != ServiceRequestStatus.PUBLISHED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request no longer accepting offers")

    offer.status = OfferStatus.ACCEPTED
    req.status = ServiceRequestStatus.CONFIRMED
    hold_until = datetime.now(UTC) + timedelta(minutes=settings.payment_hold_minutes)
    job = ServiceJob(
        request_id=req.id,
        offer_id=offer.id,
        provider_id=offer.provider_id,
        customer_id=req.customer_id,
        status=ServiceJobStatus.AWAITING_PAYMENT,
        price_cents_snapshot=offer.price_cents,
        included_work_snapshot=offer.included_work,
        hold_expires_at=hold_until,
    )

    other_offers = db.scalars(
        select(ServiceOffer).where(
            ServiceOffer.request_id == req.id,
            ServiceOffer.id != offer.id,
            ServiceOffer.status == OfferStatus.PENDING,
        )
    ).all()
    for o in other_offers:
        o.status = OfferStatus.DECLINED

    db.add(offer)
    db.add(req)
    db.add(job)
    db.flush()
    record_job_event(
        db,
        job,
        event_type="offer_accepted",
        summary="Customer accepted provider offer",
        actor_id=user.id,
    )
    record_job_event(
        db,
        job,
        event_type="awaiting_payment",
        summary="Awaiting customer payment to confirm job",
    )
    msg_svc.ensure_conversation(db, job)
    from app.services import notification_service as notify_svc

    notify_svc.emit(
        db,
        job.customer_id,
        kind="service_payment",
        title="Offer accepted — pay to confirm",
        body="You chose a provider. Complete payment to lock in the job.",
        link_path="/app/activity",
        dedupe_key=f"service-awaiting-pay-{job.id}",
    )
    notify_svc.emit(
        db,
        job.provider_id,
        kind="service_offer",
        title="Your offer was accepted",
        body="Waiting for customer payment. You will be notified when the job is confirmed.",
        link_path="/app/activity",
        dedupe_key=f"service-offer-won-{job.id}",
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An offer was already accepted") from exc
    db.refresh(job)
    return job


def get_job_for_user(db: Session, user: User, job_id: uuid.UUID) -> ServiceJob:
    expire_stale_service_holds(db)
    job = db.get(ServiceJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.provider_id != user.id and job.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
    return job


def job_to_out(db: Session, job: ServiceJob, viewer: User) -> ServiceJobOut:
    job = db.scalar(
        select(ServiceJob)
        .where(ServiceJob.id == job.id)
        .options(joinedload(ServiceJob.timeline), joinedload(ServiceJob.conversation), joinedload(ServiceJob.review))
    )
    assert job is not None
    req = db.get(ServiceRequest, job.request_id)
    provider = db.scalar(select(User).where(User.id == job.provider_id).options(joinedload(User.profile)))
    customer = db.scalar(select(User).where(User.id == job.customer_id).options(joinedload(User.profile)))
    return ServiceJobOut(
        id=job.id,
        request_id=job.request_id,
        request_title=req.title if req else "",
        status=job.status,
        price_cents_snapshot=job.price_cents_snapshot,
        included_work_snapshot=job.included_work_snapshot,
        provider_name=provider.profile.display_name if provider else "",
        customer_name=customer.profile.display_name if customer else "",
        is_provider_view=job.provider_id == viewer.id,
        hold_expires_at=job.hold_expires_at,
        paid_at=job.paid_at,
        started_at=job.started_at,
        timeline=[ServiceJobEventOut.model_validate(e) for e in job.timeline],
        conversation_id=job.conversation.id if job.conversation else None,
        has_review=job.review is not None,
        created_at=job.created_at,
    )


def submit_assistance_review(
    db: Session, user: User, job_id: uuid.UUID, data: AssistanceReviewCreate
) -> AssistanceReviewOut:
    job = db.get(ServiceJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the customer can review")
    if job.status != ServiceJobStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job must be completed first")
    existing = db.scalar(select(AssistanceReview).where(AssistanceReview.service_job_id == job.id))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review already submitted")

    review = AssistanceReview(
        service_job_id=job.id,
        customer_id=user.id,
        provider_id=job.provider_id,
        rating=data.rating,
        comment=data.comment.strip(),
    )
    db.add(review)
    record_job_event(db, job, event_type="reviewed", summary="Customer left an assistance rating", actor_id=user.id)
    db.commit()
    db.refresh(review)
    return AssistanceReviewOut(rating=review.rating, comment=review.comment, created_at=review.created_at)


def portfolio_category_statuses(db: Session, user_id: uuid.UUID) -> list[tuple[ServiceCategory, str]]:
    rows = db.scalars(
        select(PortfolioServiceCategory)
        .where(PortfolioServiceCategory.portfolio_user_id == user_id)
        .options(joinedload(PortfolioServiceCategory.category))
    ).all()
    return [(row.category, row.verification_status) for row in rows]


def list_my_requests(db: Session, user: User) -> list[ServiceRequest]:
    return list(
        db.scalars(select(ServiceRequest).where(ServiceRequest.customer_id == user.id).order_by(ServiceRequest.created_at.desc()))
    )


def list_open_requests_for_providers(db: Session, category: str | None) -> list[ServiceRequest]:
    stmt = (
        select(ServiceRequest)
        .where(ServiceRequest.status == ServiceRequestStatus.PUBLISHED)
        .options(joinedload(ServiceRequest.category))
        .order_by(ServiceRequest.created_at.desc())
    )
    if category:
        stmt = stmt.join(ServiceCategory).where(ServiceCategory.slug == category)
    return list(db.scalars(stmt.limit(50)).all())


def list_offers_for_request(db: Session, user: User, request_id: uuid.UUID) -> list[ServiceOffer]:
    req = db.get(ServiceRequest, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your request")
    return list(db.scalars(select(ServiceOffer).where(ServiceOffer.request_id == request_id).order_by(ServiceOffer.created_at)))


def list_my_jobs(db: Session, user: User) -> list[ServiceJob]:
    expire_stale_service_holds(db)
    return list(
        db.scalars(
            select(ServiceJob)
            .where((ServiceJob.provider_id == user.id) | (ServiceJob.customer_id == user.id))
            .order_by(ServiceJob.created_at.desc())
        ).all()
    )


def start_job(db: Session, user: User, job_id: uuid.UUID) -> ServiceJob:
    job = db.get(ServiceJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.provider_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
    if job.status != ServiceJobStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job cannot be started")
    job.status = ServiceJobStatus.IN_PROGRESS
    job.started_at = datetime.now(UTC)
    req = db.get(ServiceRequest, job.request_id)
    if req:
        req.status = ServiceRequestStatus.IN_PROGRESS
        db.add(req)
    record_job_event(db, job, event_type="started", summary="Provider started on-site work", actor_id=user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def submit_job_completion(db: Session, user: User, job_id: uuid.UUID) -> ServiceJob:
    job = db.get(ServiceJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.provider_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
    if job.status != ServiceJobStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job is not in progress")
    job.status = ServiceJobStatus.COMPLETION_SUBMITTED
    record_job_event(
        db, job, event_type="completion_submitted", summary="Provider submitted completion", actor_id=user.id
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def confirm_job_completion(db: Session, user: User, job_id: uuid.UUID) -> ServiceJob:
    job = db.get(ServiceJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your job")
    if job.status != ServiceJobStatus.COMPLETION_SUBMITTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Completion not submitted")
    job.status = ServiceJobStatus.COMPLETED
    job.completed_at = datetime.now(UTC)
    req = db.get(ServiceRequest, job.request_id)
    if req:
        req.status = ServiceRequestStatus.COMPLETED
        db.add(req)
    record_job_event(db, job, event_type="completed", summary="Customer confirmed job complete", actor_id=user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def mark_job_paid(db: Session, job: ServiceJob) -> None:
    if job.status != ServiceJobStatus.AWAITING_PAYMENT:
        return
    job.status = ServiceJobStatus.CONFIRMED
    job.paid_at = datetime.now(UTC)
    record_job_event(db, job, event_type="payment_succeeded", summary="Customer payment received")
    db.add(job)