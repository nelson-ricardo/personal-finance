"""Envelope split data schemas for transaction allocations."""

from decimal import Decimal

from sqlalchemy import Numeric
from sqlmodel import Column, Field, SQLModel


class EnvelopeSplitBase(SQLModel):
    """Base schema for envelope split allocations."""

    amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(precision=14, scale=2), nullable=False),
        description="Signed monetary amount (negative for deductions/spending, positive for allocations/credits)",
    )


class EnvelopeSplitRequest(EnvelopeSplitBase):
    """Request payload for specifying an envelope split with an envelope name."""

    envelope_name: str = Field(description="Name of the envelope associated with this split")


class EnvelopeSplitResponse(EnvelopeSplitBase):
    """Response schema for a single envelope split with envelope details."""

    id: int = Field(description="Unique identifier for the envelope split entry")
    envelope_id: int = Field(description="ID of the associated envelope")
    envelope_name: str = Field(description="Display name of the associated envelope")
