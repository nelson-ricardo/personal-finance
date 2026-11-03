"""Service layer for Web Push notifications."""

import json
import logging
import os
from typing import Any, Dict, List

from pywebpush import WebPushException, webpush
from sqlmodel import Session, select

from budget_app.models.push_subscription import PushSubscription
from budget_app.schemas.notification import PushSubscriptionCreate

logger = logging.getLogger(__name__)


def get_vapid_public_key() -> str:
    """Retrieves the configured VAPID public key from environment."""
    key = os.getenv("VAPID_PUBLIC_KEY")
    if not key:
        raise ValueError("VAPID_PUBLIC_KEY is not configured in the environment.")
    return key


def get_vapid_private_key() -> str:
    """Retrieves the configured VAPID private key from environment."""
    key = os.getenv("VAPID_PRIVATE_KEY")
    if not key:
        raise ValueError("VAPID_PRIVATE_KEY is not configured in the environment.")
    return key


def get_vapid_claim_email() -> str:
    """Retrieves the contact email claim for VAPID."""
    return os.getenv("VAPID_CLAIM_EMAIL", "mailto:budgeter@example.com")


def save_subscription(session: Session, data: PushSubscriptionCreate) -> PushSubscription:
    """Registers or updates a device Web Push subscription."""
    stmt = select(PushSubscription).where(PushSubscription.endpoint == data.endpoint)
    existing = session.exec(stmt).first()

    if existing:
        existing.p256dh_key = data.keys.p256dh
        existing.auth_key = data.keys.auth
        existing.user_agent = data.user_agent
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    new_sub = PushSubscription(
        endpoint=data.endpoint,
        p256dh_key=data.keys.p256dh,
        auth_key=data.keys.auth,
        user_agent=data.user_agent,
    )
    session.add(new_sub)
    session.commit()
    session.refresh(new_sub)
    return new_sub


def remove_subscription(session: Session, endpoint: str) -> bool:
    """Removes a subscription when device unsubscribes or notification fails with 410 Gone."""
    stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    sub = session.exec(stmt).first()
    if sub:
        session.delete(sub)
        session.commit()
        return True
    return False


def get_all_subscriptions(session: Session) -> List[PushSubscription]:
    """Returns all stored push subscriptions."""
    return list(session.exec(select(PushSubscription)).all())


def send_notification(
    session: Session,
    subscription: PushSubscription,
    title: str,
    body: str,
    url: str = "/",
) -> bool:
    """Sends an encrypted web push notification to a specific subscribed device."""
    try:
        private_key = get_vapid_private_key()
        claim_email = get_vapid_claim_email()

        payload = json.dumps(
            {
                "title": title,
                "body": body,
                "url": url,
            }
        )

        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key,
                },
            },
            data=payload,
            vapid_private_key=private_key,
            vapid_claims={"sub": claim_email},
        )
        logger.info(f"Successfully delivered push notification to endpoint {subscription.endpoint[:30]}...")
        return True
    except WebPushException as ex:
        logger.warning(f"WebPushException sending to {subscription.endpoint[:30]}: {ex}")
        # Status 404 or 410 indicates the push token expired or was unsubscribed on device
        if ex.response is not None and ex.response.status_code in (404, 410):
            logger.info(f"Device unsubscribed/expired ({ex.response.status_code}); removing subscription.")
            remove_subscription(session, subscription.endpoint)
        return False
    except Exception as ex:
        logger.error(f"Unexpected error sending web push: {ex}", exc_info=True)
        return False


def broadcast_notification(
    session: Session,
    title: str,
    body: str,
    url: str = "/",
) -> Dict[str, Any]:
    """Broadcasts a notification to all active devices."""
    subs = get_all_subscriptions(session)
    sent_count = 0
    failed_count = 0

    for sub in subs:
        success = send_notification(session, sub, title, body, url)
        if success:
            sent_count += 1
        else:
            failed_count += 1

    return {
        "total_subscriptions": len(subs),
        "sent": sent_count,
        "failed": failed_count,
    }
