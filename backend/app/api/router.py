from fastapi import APIRouter

from app.api.v1 import (
    admin,
    assistance,
    auth,
    bookings,
    community,
    condition,
    disputes,
    files,
    listings,
    me,
    messages,
    notifications,
    payments,
    supervision,
    wishlist,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(listings.router)
api_router.include_router(assistance.router)
api_router.include_router(bookings.router)
api_router.include_router(payments.router)
api_router.include_router(condition.router)
api_router.include_router(files.router)
api_router.include_router(messages.router)
api_router.include_router(admin.router)
api_router.include_router(notifications.router)
api_router.include_router(wishlist.router)
api_router.include_router(community.router)
api_router.include_router(disputes.router)
api_router.include_router(supervision.router)
