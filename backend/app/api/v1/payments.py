import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.db.session import get_db
from app.schemas.payments import PaymentIntentOut, PaymentOut, PaymentWebhookPayload
from app.services import assistance_service as asvc
from app.services import booking_service as book_svc
from app.services import payment_service as pay_svc

router = APIRouter(tags=["payments"])


@router.post("/rental-bookings/{booking_id}/payment-intent", response_model=PaymentIntentOut)
def create_booking_payment_intent(
    booking_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> PaymentIntentOut:
    booking = book_svc.get_booking(db, booking_id)
    if booking.renter_id != user.id:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your booking")
    return pay_svc.create_payment_intent(db, booking)


@router.post("/rental-bookings/{booking_id}/sandbox-pay", response_model=PaymentOut)
def sandbox_pay_booking(
    booking_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    payment_id: Annotated[uuid.UUID, Query()],
) -> PaymentOut:
    from app.core.config import settings
    from fastapi import HTTPException, status

    if settings.environment != "development":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not available")

    booking = book_svc.get_booking(db, booking_id)
    if booking.renter_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your booking")

    payment = pay_svc.sandbox_complete_payment(db, booking, payment_id)
    return PaymentOut.model_validate(payment)


@router.post("/service-jobs/{job_id}/payment-intent", response_model=PaymentIntentOut)
def create_service_payment_intent(
    job_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> PaymentIntentOut:
    from fastapi import HTTPException, status

    job = asvc.get_job_for_user(db, user, job_id)
    if job.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the customer can pay")
    return pay_svc.create_service_payment_intent(db, job)


@router.post("/service-jobs/{job_id}/sandbox-pay", response_model=PaymentOut)
def sandbox_pay_service_job(
    job_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    payment_id: Annotated[uuid.UUID, Query()],
) -> PaymentOut:
    from app.core.config import settings
    from fastapi import HTTPException, status

    if settings.environment != "development":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not available")

    job = asvc.get_job_for_user(db, user, job_id)
    if job.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the customer can pay")

    payment = pay_svc.sandbox_complete_service_payment(db, job, payment_id)
    return PaymentOut.model_validate(payment)


@router.post("/webhooks/payments", response_model=PaymentOut)
async def payment_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_nl_signature: Annotated[str | None, Header()] = None,
) -> PaymentOut:
    body = await request.body()
    pay_svc.verify_webhook_signature(body, x_nl_signature)
    data = json.loads(body.decode("utf-8"))
    payload = PaymentWebhookPayload.model_validate(data)
    payment = pay_svc.apply_payment_webhook(db, payload)
    return PaymentOut.model_validate(payment)