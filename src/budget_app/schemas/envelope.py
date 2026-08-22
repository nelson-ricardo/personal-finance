"""Envelope data schemas and transfer result transfer objects."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    from budget_app.models.envelope import Envelope
    from budget_app.models.transaction import Transaction


class EnvelopeBase(SQLModel):
    """Base schema defining properties for a budgeting envelope category."""

    name: str = Field(unique=True, description="Unique display name of the envelope category")
    note: Optional[str] = Field(default=None, description="Optional description, goal, or monthly payment note")
    is_active: bool = Field(default=True, description="Flag indicating whether this envelope is active for budgeting")


class EnvelopeTransfer(SQLModel):
    """Response object returned after executing a transfer between two envelopes.

    Contains the modified source and destination Envelope models with their newly computed
    balances and the recorded master transfer Transaction.
    """

    source: Envelope
    new_balance_src: Decimal
    destination: Envelope
    new_balance_dest: Decimal
    transfer_transaction: Transaction


class Config:
    arbitrary_types_allows = True

