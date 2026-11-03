"""Pydantic schemas for obligations and notification configuration."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ObligationBase(BaseModel):
    """Base 4-column obligation schema."""

    name: str = Field(description="Obligation name (e.g. Rent, Verizon, Chase Freedom)")
    due_day: int = Field(ge=1, le=31, description="Day of month due (1-31)")
    amount: Decimal = Field(gt=0, description="Monthly amount due")
    note: Optional[str] = Field(default=None, description="Notes; auto-populated for accounts")
    account_id: Optional[int] = Field(default=None, description="Optional linked credit card / loan account")


class ObligationCreate(ObligationBase):
    """Payload to create a new obligation."""

    pass


class ObligationUpdate(BaseModel):
    """Payload to update an obligation."""

    name: Optional[str] = None
    due_day: Optional[int] = Field(default=None, ge=1, le=31)
    amount: Optional[Decimal] = Field(default=None, gt=0)
    note: Optional[str] = None
    account_id: Optional[int] = None
    is_active: Optional[bool] = None


class ObligationResponse(BaseModel):
    """Rich response schema including computed payment and calendar status."""

    id: int
    name: str
    due_day: int
    amount: Decimal
    note: Optional[str] = None
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    is_active: bool
    last_paid_date: Optional[date] = None
    last_paid_amount: Optional[Decimal] = None
    created_at: datetime

    # Computed fields for calendar and dashboard
    next_due_date: date
    days_until_due: int
    is_overdue: bool
    is_paid_this_month: bool


class ObligationMarkPaidRequest(BaseModel):
    """Payload when manually marking an obligation as paid or unpaid."""

    paid: bool = True
    paid_date: Optional[date] = None
    paid_amount: Optional[Decimal] = None


class NotificationConfigResponse(BaseModel):
    """Response schema for daily push reminder configuration."""

    reminder_time: str
    reminder_days_ahead: int
    is_enabled: bool
    last_dispatched_date: Optional[date] = None


class NotificationConfigUpdate(BaseModel):
    """Payload to update daily push reminder configuration."""

    reminder_time: Optional[str] = Field(
        default=None,
        pattern=r"^([01]\d|2[0-3]):([0-5]\d)$",
        description="HH:MM 24-hour time string",
    )
    reminder_days_ahead: Optional[int] = Field(default=None, ge=0, le=30)
    is_enabled: Optional[bool] = None
