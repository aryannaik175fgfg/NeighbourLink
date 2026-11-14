import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.schemas.assistance import (
    AssistanceReviewCreate,
    AssistanceReviewOut,
    OfferCreate,
    OfferOut,
    PortfolioCreate,
    ProviderCategoryOut,
    ProviderPublic,
    ServiceCategoryOut,
    ServiceJobOut,
    ServiceRequestCreate,
    ServiceRequestOut,
)
from app.services.provider_ratings import provider_rating_aggregate
from app.models.assistance import ServiceCategory
from app.services import assistance_service as asvc
from sqlalchemy import select

router = APIRouter(tags=["assistance"])


@router.get("/service-categories", response_model=list[ServiceCategoryOut])
def list_service_categories(db: Annotated[Session, Depends(get_db)]) -> list[ServiceCategoryOut]:
    cats = db.scalars(select(ServiceCategory).order_by(ServiceCategory.sort_order)).all()
    return [ServiceCategoryOut.model_validate(c) for c in cats]


@router.get("/providers", response_model=list[ProviderPublic])
def search_providers(
    db: Annotated[Session, Depends(get_db)],
    category: str | None = None,
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float = Query(default=25, ge=1, le=200),
) -> list[ProviderPublic]:
    return asvc.search_providers(db, category=category, latitude=latitude, longitude=longitude, radius_km=radius_km)


@router.put("/me/provider-portfolio", response_model=ProviderPublic)
def upsert_portfolio(body: PortfolioCreate, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> ProviderPublic:
    p = asvc.upsert_portfolio(db, user, body)
    lat, lng = asvc._portfolio_lat_lng(db, p.user_id)
    avg, count = provider_rating_aggregate(db, p.user_id)
    return ProviderPublic(
        user_id=p.user_id,
        display_name=p.user.profile.display_name,
        headline=p.headline,
        introduction=p.introduction,
        service_area_label=p.service_area_label,
        latitude=lat,
        longitude=lng,
        categories=p.categories,
        assistance_rating=avg,
        assistance_rating_count=count,
    )


@router.get("/me/provider-portfolio/categories", response_model=list[ProviderCategoryOut])
def my_portfolio_categories(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[ProviderCategoryOut]:
    rows = asvc.portfolio_category_statuses(db, user.id)
    return [
        ProviderCategoryOut(slug=cat.slug, name=cat.name, verification_status=status) for cat, status in rows
    ]


@router.post("/service-requests", response_model=ServiceRequestOut, status_code=201)
def create_service_request(
    body: ServiceRequestCreate, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> ServiceRequestOut:
    req = asvc.create_request(db, user, body)
    return asvc.request_to_out(db, req)


@router.get("/me/service-requests", response_model=list[ServiceRequestOut])
def my_service_requests(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[ServiceRequestOut]:
    return [asvc.request_to_out(db, r) for r in asvc.list_my_requests(db, user)]


@router.get("/service-requests/open", response_model=list[ServiceRequestOut])
def open_service_requests(
    db: Annotated[Session, Depends(get_db)],
    category: str | None = None,
) -> list[ServiceRequestOut]:
    return [asvc.request_to_out(db, r) for r in asvc.list_open_requests_for_providers(db, category)]


@router.get("/service-requests/{request_id}/offers", response_model=list[OfferOut])
def list_offers(
    request_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[OfferOut]:
    return [asvc.offer_to_out(db, o) for o in asvc.list_offers_for_request(db, user, request_id)]


@router.post("/service-requests/{request_id}/offers", response_model=OfferOut, status_code=201)
def create_offer(
    request_id: uuid.UUID, body: OfferCreate, user: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> OfferOut:
    offer = asvc.submit_offer(db, user, request_id, body)
    return asvc.offer_to_out(db, offer)


@router.post("/offers/{offer_id}/accept", response_model=ServiceJobOut)
def accept_offer(offer_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> ServiceJobOut:
    job = asvc.accept_offer(db, user, offer_id)
    return asvc.job_to_out(db, job, user)


@router.get("/me/service-jobs", response_model=list[ServiceJobOut])
def my_service_jobs(user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> list[ServiceJobOut]:
    return [asvc.job_to_out(db, j, user) for j in asvc.list_my_jobs(db, user)]


@router.post("/service-jobs/{job_id}/start", response_model=ServiceJobOut)
def start_job(job_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> ServiceJobOut:
    job = asvc.start_job(db, user, job_id)
    return asvc.job_to_out(db, job, user)


@router.post("/service-jobs/{job_id}/submit-completion", response_model=ServiceJobOut)
def submit_completion(job_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> ServiceJobOut:
    job = asvc.submit_job_completion(db, user, job_id)
    return asvc.job_to_out(db, job, user)


@router.post("/service-jobs/{job_id}/confirm-completion", response_model=ServiceJobOut)
def confirm_completion(job_id: uuid.UUID, user: CurrentUser, db: Annotated[Session, Depends(get_db)]) -> ServiceJobOut:
    job = asvc.confirm_job_completion(db, user, job_id)
    return asvc.job_to_out(db, job, user)


@router.post("/service-jobs/{job_id}/review", response_model=AssistanceReviewOut, status_code=201)
def review_service_job(
    job_id: uuid.UUID,
    body: AssistanceReviewCreate,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> AssistanceReviewOut:
    return asvc.submit_assistance_review(db, user, job_id, body)