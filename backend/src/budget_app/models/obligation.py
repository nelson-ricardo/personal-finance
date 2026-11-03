"""Database models for obligations and notification configuration."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Numeric
from sqlmodel import Field, SQLModel


class Obligation(SQLModel, table=True):
    """Represents a bill, debt payment, or recurring obligation to be paid on a specific day."""

    __tablename__ = "obligation"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Core 4 User Columns
    name: str = Field(description="Name of the obligation, e.g. Rent, Verizon, Chase Sapphire")
    due_day: int = Field(ge=1, le=31, description="Day of the month the payment is due (1-31)")
    amount: Decimal = Field(
        sa_column=Column(Numeric(precision=14, scale=2), nullable=False),
        description="Amount due each billing cycle",
    )
    note: Optional[str] = Field(
        default=None,
        description="User notes; defaults to 'Monthly payment for {Account}' for linked accounts",
    )

    # Link to financial account (Credit Card or Loan)
    account_id: Optional[int] = Field(
        default=None,
        foreign_key="account.id",
        nullable=True,
        description="Optional link to a credit card or loan account",
    )

    # Status & tracking
    is_active: bool = Field(default=True, description="Whether this obligation is active")
    last_paid_date: Optional[date] = Field(
        default=None,
        description="Most recent date this obligation was paid or marked as paid",
    )
    last_paid_amount: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(precision=14, scale=2), nullable=True),
        description="Amount of the last payment",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class NotificationConfig(SQLModel, table=True):
    """Stores user preferences for daily push reminder schedule."""

    __tablename__ = "notification_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    reminder_time: str = Field(
        default="09:00",
        description="Time of day in 24h format (HH:MM) to dispatch daily push reminders",
    )
    reminder_days_ahead: int = Field(
        default=3,
        description="Number of days in advance to notify about upcoming due dates",
    )
    is_enabled: bool = Field(default=True, description="Master toggle for daily reminder pushes")
    last_dispatched_date: Optional[date] = Field(
        default=None,
        description="Last calendar date notifications were successfully dispatched to prevent double-alerts",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
