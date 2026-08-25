"""Ledger entry data schemas for transaction splits."""

from decimal import Decimal

from sqlalchemy import Numeric
from sqlmodel import Column, Field, SQLModel


class LedgerBase(SQLModel):
    """Base schema for ledger split entries."""

    amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(precision=14, scale=2), nullable=False),
        description="Signed monetary amount (negative for deductions/spending, positive for allocations/credits)",
    )


class LedgerRequest(LedgerBase):
    """Request payload for specifying a ledger entry with an envelope name."""

    envelope_name: str = Field(description="Name of the envelope associated with this split")


class LedgerResponse(LedgerBase):
    """Response schema for a single ledger entry with envelope details."""

    id: int = Field(description="Unique identifier for the ledger entry")
    envelope_id: int = Field(description="ID of the associated envelope")
    envelope_name: str = Field(description="Display name of the associated envelope")


