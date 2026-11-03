"""Schemas for push notification management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PushSubscriptionKeys(BaseModel):
    """Client cryptographic keys supplied by the browser PushManager."""

    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    """Payload sent by client when subscribing to push notifications."""

    endpoint: str
    keys: PushSubscriptionKeys
    user_agent: Optional[str] = None


class PushSubscriptionRead(BaseModel):
    """Response schema for a stored push subscription."""

    id: int
    endpoint: str
    created_at: datetime
    user_agent: Optional[str] = None


class PushNotificationTestRequest(BaseModel):
    """Payload to trigger an immediate test notification."""

    title: Optional[str] = Field(default="🔔 Homeledger Test", description="Notification title")
    body: Optional[str] = Field(
        default="Web push notifications are working smoothly on your device!",
        description="Notification body text",
    )
    url: Optional[str] = Field(default="/", description="Target URL when tapping notification")
