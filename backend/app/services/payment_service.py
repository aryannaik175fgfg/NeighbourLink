import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assistance import ServiceJob, ServiceJobStatus
from app.models.payment import Payment, PaymentEvent, PaymentStatus
from app.models.rental_booking import RentalBooking, RentalBookingStatus
from app.services import assistance_service as asvc
from app.schemas.payments import PaymentIntentOut, PaymentWebhookPayload


def expire_stale_holds(db: Session) -> int:
    now = datetime.now(UTC)
    bookings = db.scalars(
        select(RentalBooking).where(
            RentalBooking.status == RentalBookingStatus.AWAITING_PAYMENT,
            RentalBooking.hold_expires_at.is_not(None),
            RentalBooking.hold_expires_at < now,
        )
    ).all()
    count = 0
    for booking in bookings:
        booking.status = RentalBookingStatus.EXPIRED
        db.add(booking)
        count += 1
    if count:
        db.commit()
    return count


def create_payment_intent(db: Session, booking: RentalBooking) -> PaymentIntentOut:
    if booking.status != RentalBookingStatus.AWAITING_PAYMENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking is not awaiting payment")

    expire_stale_holds(db)
    db.refresh(booking)
    if booking.status == RentalBookingStatus.EXPIRED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment hold expired")

    existing = db.scalar(
        select(Payment).where(
            Payment.rental_booking_id == booking.id,
            Payment.status == PaymentStatus.PENDING,
        )
    )
    if existing:
        checkout_token = _checkout_token(existing.id)
        return PaymentIntentOut(
            payment_id=existing.id,
            rental_booking_id=booking.id,
            amount_cents=existing.amount_cents,
            currency=existing.currency,
            status=existing.status,
            provider=existing.provider,
            idempotency_key=existing.idempotency_key,
            checkout_token=checkout_token,
        )

    idem = f"booking-{booking.id}-{secrets.token_hex(8)}"
    provider_ref = f"sandbox_{secrets.token_hex(12)}"
    payment = Payment(
        rental_booking_id=booking.id,
        amount_cents=booking.total_cents,
        currency="INR",
        status=PaymentStatus.PENDING,
        provider=settings.payments_provider,
        provider_reference=provider_ref,
        idempotency_key=idem,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return PaymentIntentOut(
        payment_id=payment.id,
        rental_booking_id=booking.id,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        status=payment.status,
        provider=payment.provider,
        idempotency_key=payment.idempotency_key,
        checkout_token=_checkout_token(payment.id),
    )


def _checkout_token(payment_id: uuid.UUID) -> str:
    return secrets.token_urlsafe(24)


def verify_webhook_signature(body: bytes, signature_header: str | None) -> None:
    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")
    expected = hmac.new(
        settings.payment_webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")


def apply_payment_webhook(db: Session, payload: PaymentWebhookPayload) -> Payment:
    existing_event = db.scalar(select(PaymentEvent).where(PaymentEvent.provider_event_id == payload.event_id))
    if existing_event:
        payment = db.get(Payment, existing_event.payment_id)
        assert payment is not None
        return payment

    payment = db.get(Payment, payload.payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    event = PaymentEvent(
        payment_id=payment.id,
        event_type=payload.event_type,
        provider_event_id=payload.event_id,
        payload=payload.model_dump(mode="json"),
    )
    db.add(event)

    if payload.status == PaymentStatus.SUCCEEDED and payment.status != PaymentStatus.SUCCEEDED:
        payment.status = PaymentStatus.SUCCEEDED
        payment.succeeded_at = datetime.now(UTC)
        db.add(payment)
        if payment.rental_booking_id:
            booking = db.get(RentalBooking, payment.rental_booking_id)
            if booking and booking.status == RentalBookingStatus.AWAITING_PAYMENT:
                booking.status = RentalBookingStatus.CONFIRMED
                booking.paid_at = datetime.now(UTC)
                db.add(booking)
                from app.services import escrow_service as escrow_svc

                escrow_svc.try_create_hold(db, booking, payment)
        if payment.service_job_id:
            job = db.get(ServiceJob, payment.service_job_id)
            if job and job.status == ServiceJobStatus.AWAITING_PAYMENT:
                asvc.mark_job_paid(db, job)

    elif payload.status == PaymentStatus.FAILED and payment.status == PaymentStatus.PENDING:
        payment.status = PaymentStatus.FAILED
        db.add(payment)

    try:
        db.commit()
    except Exception:
        db.rollback()
        existing_event = db.scalar(select(PaymentEvent).where(PaymentEvent.provider_event_id == payload.event_id))
        if existing_event:
            payment = db.get(Payment, existing_event.payment_id)
            assert payment is not None
            return payment
        raise

    db.refresh(payment)
    return payment


def create_service_payment_intent(db: Session, job: ServiceJob) -> PaymentIntentOut:
    if job.status != ServiceJobStatus.AWAITING_PAYMENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job is not awaiting payment")

    asvc.expire_stale_service_holds(db)
    db.refresh(job)
    if job.status == ServiceJobStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment hold expired")

    existing = db.scalar(
        select(Payment).where(
            Payment.service_job_id == job.id,
            Payment.status == PaymentStatus.PENDING,
        )
    )
    if existing:
        return PaymentIntentOut(
            payment_id=existing.id,
            service_job_id=job.id,
            amount_cents=existing.amount_cents,
            currency=existing.currency,
            status=existing.status,
            provider=existing.provider,
            idempotency_key=existing.idempotency_key,
            checkout_token=_checkout_token(existing.id),
        )

    idem = f"service-job-{job.id}-{secrets.token_hex(8)}"
    provider_ref = f"sandbox_{secrets.token_hex(12)}"
    payment = Payment(
        service_job_id=job.id,
        amount_cents=job.price_cents_snapshot,
        currency="INR",
        status=PaymentStatus.PENDING,
        provider=settings.payments_provider,
        provider_reference=provider_ref,
        idempotency_key=idem,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return PaymentIntentOut(
        payment_id=payment.id,
        service_job_id=job.id,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        status=payment.status,
        provider=payment.provider,
        idempotency_key=payment.idempotency_key,
        checkout_token=_checkout_token(payment.id),
    )


def sandbox_complete_service_payment(db: Session, job: ServiceJob, payment_id: uuid.UUID) -> Payment:
    payment = db.scalar(select(Payment).where(Payment.id == payment_id, Payment.service_job_id == job.id))
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    payload = PaymentWebhookPayload(
        event_id=f"sandbox-complete-{payment.id}-{secrets.token_hex(4)}",
        event_type="payment.succeeded",
        payment_id=payment.id,
        status=PaymentStatus.SUCCEEDED,
    )
    return apply_payment_webhook(db, payload)


def sandbox_complete_payment(db: Session, booking: RentalBooking, payment_id: uuid.UUID) -> Payment:
    """Renter-authenticated sandbox checkout completing via same webhook path."""
    payment = db.scalar(
        select(Payment).where(Payment.id == payment_id, Payment.rental_booking_id == booking.id)
    )
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    payload = PaymentWebhookPayload(
        event_id=f"sandbox-complete-{payment.id}-{secrets.token_hex(4)}",
        event_type="payment.succeeded",
        payment_id=payment.id,
        status=PaymentStatus.SUCCEEDED,
    )
    return apply_payment_webhook(db, payload)


def build_webhook_signature(body: bytes) -> str:
    digest = hmac.new(settings.payment_webhook_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"