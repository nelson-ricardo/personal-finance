"""Database model for storing Web Push subscriptions."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class PushSubscription(SQLModel, table=True):
    """Stores Web Push API subscription endpoints and cryptographic keys per device."""

    __tablename__ = "push_subscription"

    id: Optional[int] = Field(default=None, primary_key=True)
    endpoint: str = Field(index=True, unique=True, nullable=False, description="Push service delivery URL")
    p256dh_key: str = Field(nullable=False, description="Client public encryption key (P-256)")
    auth_key: str = Field(nullable=False, description="Client authentication secret")
    user_agent: Optional[str] = Field(default=None, description="Client browser / device identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
