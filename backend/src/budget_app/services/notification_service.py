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


def check_and_dispatch_due_reminders(session: Session, force: bool = False) -> Dict[str, Any]:
    """Evaluates upcoming obligations against reminder config and dispatches pushes."""
    from datetime import date, datetime

    from budget_app.models.obligation import NotificationConfig
    from budget_app.services import obligation_service

    config = session.exec(select(NotificationConfig)).first()
    if not config:
        config = NotificationConfig()
        session.add(config)
        session.commit()
        session.refresh(config)

    today = date.today()

    if not force:
        if not config.is_enabled:
            return {"status": "skipped", "reason": "reminders_disabled"}
        if config.last_dispatched_date == today:
            return {"status": "skipped", "reason": "already_dispatched_today"}

        now_str = datetime.now().strftime("%H:%M")
        if now_str < config.reminder_time:
            return {
                "status": "pending",
                "current_time": now_str,
                "scheduled_time": config.reminder_time,
            }

    # Fetch active obligations
    all_obls = obligation_service.get_all_obligations(session, is_active=True)
    due_obls = [
        o for o in all_obls
        if not o.is_paid_this_month and o.days_until_due <= config.reminder_days_ahead
    ]

    if not due_obls:
        if not force:
            config.last_dispatched_date = today
            session.add(config)
            session.commit()
        return {"status": "completed", "due_count": 0, "message": "No obligations due soon"}

    # Construct push message
    if len(due_obls) == 1:
        obl = due_obls[0]
        if obl.days_until_due == 0:
            title = f"⚡ Payment Due Today: {obl.name}"
            body = f"{obl.name} (${obl.amount:,.2f}) is due today! Don't forget to pay."
        elif obl.days_until_due < 0:
            title = f"⚠️ Overdue Payment: {obl.name}"
            body = f"{obl.name} (${obl.amount:,.2f}) was due on the {obl.due_day}th."
        else:
            title = f"🔔 Upcoming Payment: {obl.name}"
            days_txt = "tomorrow" if obl.days_until_due == 1 else f"in {obl.days_until_due} days"
            body = f"{obl.name} (${obl.amount:,.2f}) is due {days_txt} (day {obl.due_day})."
    else:
        names = ", ".join(o.name for o in due_obls[:2])
        if len(due_obls) > 2:
            names += f" and {len(due_obls) - 2} more"
        title = f"🔔 {len(due_obls)} Obligations Due Soon"
        body = f"{names} are due within the next {config.reminder_days_ahead} days."

    result = broadcast_notification(
        session=session,
        title=title,
        body=body,
        url="/obligations",
    )

    config.last_dispatched_date = today
    session.add(config)
    session.commit()

    return {
        "status": "dispatched",
        "due_count": len(due_obls),
        "title": title,
        "body": body,
        **result,
    }
