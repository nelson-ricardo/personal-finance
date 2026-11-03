"""API routes for Web Push notifications."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from budget_app.db import get_session
from budget_app.schemas.notification import (
    PushNotificationTestRequest,
    PushSubscriptionCreate,
    PushSubscriptionRead,
)
from budget_app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/vapid-public-key")
def get_vapid_public_key() -> Dict[str, str]:
    """Returns the VAPID public key needed by the browser to subscribe."""
    try:
        return {"public_key": notification_service.get_vapid_public_key()}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/subscribe", response_model=PushSubscriptionRead, status_code=status.HTTP_201_CREATED)
def subscribe(
    payload: PushSubscriptionCreate,
    session: Session = Depends(get_session),
):
    """Subscribes or updates a device's push notification registration."""
    try:
        sub = notification_service.save_subscription(session, payload)
        return PushSubscriptionRead(
            id=sub.id or 0,
            endpoint=sub.endpoint,
            created_at=sub.created_at,
            user_agent=sub.user_agent,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/unsubscribe")
def unsubscribe(
    endpoint: str,
    session: Session = Depends(get_session),
) -> Dict[str, bool]:
    """Removes a push subscription for the given endpoint."""
    removed = notification_service.remove_subscription(session, endpoint)
    return {"removed": removed}


@router.get("/subscriptions", response_model=List[PushSubscriptionRead])
def list_subscriptions(
    session: Session = Depends(get_session),
):
    """Lists currently registered push subscriptions."""
    subs = notification_service.get_all_subscriptions(session)
    return [
        PushSubscriptionRead(
            id=sub.id or 0,
            endpoint=sub.endpoint,
            created_at=sub.created_at,
            user_agent=sub.user_agent,
        )
        for sub in subs
    ]


@router.post("/test")
def send_test_notification(
    payload: PushNotificationTestRequest,
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Dispatches a test push notification to all subscribed devices."""
    result = notification_service.broadcast_notification(
        session=session,
        title=payload.title or "🔔 Homeledger Test",
        body=payload.body or "Web push notifications are working smoothly on your device!",
        url=payload.url or "/",
    )
    return {
        "status": "completed",
        **result,
    }
