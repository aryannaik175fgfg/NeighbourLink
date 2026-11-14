"""Optional out-of-band delivery (email). SMTP not required for local dev."""

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification

logger = logging.getLogger("neighbourlink.notify_delivery")


def deliver_email(db: Session, user_id, notification: Notification) -> None:
    _ = db, user_id
    if not getattr(settings, "smtp_host", None):
        logger.debug(
            "email skipped (no SMTP): to_user=%s title=%s",
            user_id,
            notification.title,
        )
        return
    logger.info("email queued: to_user=%s title=%s", user_id, notification.title)