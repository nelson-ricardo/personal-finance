"""Envelope data schemas and transfer result transfer objects."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    from budget_app.models.envelope import Envelope
    from budget_app.models.transaction import Transaction


class SystemEnvelopeType(str, Enum):
    """System envelope roles within the budgeting system."""

    UNASSIGNED = "UNASSIGNED"
    CREDIT_CARD_PAYMENT = "CREDIT_CARD_PAYMENT"
    ACCOUNT_ADJUSTMENT = "ACCOUNT_ADJUSTMENT"


class EnvelopeBase(SQLModel):
    """Base schema defining properties for a budgeting envelope category."""

    name: str = Field(unique=True, description="Unique display name of the envelope category")
    note: Optional[str] = Field(default=None, description="Optional description, goal, or monthly payment note")
    is_active: bool = Field(default=True, description="Flag indicating whether this envelope is active for budgeting")
    system_role: Optional[SystemEnvelopeType] = Field(
        default=None, description="Designated system role for this envelope, if any"
    )

class EnvelopeCreate(EnvelopeBase):
    """Payload for creating a new envelope, with an optional initial category assignment."""

    category_name: Optional[str] = Field(
        default=None, description="Optional name of the category group to assign to"
    )


class EnvelopeTransferRequest(SQLModel):
    """Payload for transferring funds between two envelopes."""

    source_envelope: str = Field(description="Name of source envelope to withdraw funds from")
    destination_envelope: str = Field(description="Name of destination envelope to deposit funds into")
    amount: Decimal = Field(description="Transfer amount (must be positive)")
    note: Optional[str] = Field(default=None, description="Optional note describing the transfer")


class EnvelopeAssignRequest(SQLModel):
    """Payload for allocating funds from Unassigned to an envelope."""

    envelope_name: str = Field(description="Target envelope name to assign funds to")
    amount: Decimal = Field(description="Assignment amount (must be positive)")
    note: Optional[str] = Field(default=None, description="Optional note describing the assignment")


class CashIncomeRequest(SQLModel):
    """Payload for adding cash income directly into Unassigned envelope."""

    amount: Decimal = Field(description="Income amount to add (must be positive)")
    source: str = Field(description="Source or merchant of the income")
    note: Optional[str] = Field(default=None, description="Optional note describing the income")


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

class EnvelopeWithBalance(EnvelopeBase):
    """Envelope Base with its database ID, category information, and balance."""

    id: Optional[int] = Field(default=None, description="Primary key ID of the envelope")
    category_id: Optional[int] = Field(default=None, description="Primary key ID of the category group")
    category_name: Optional[str] = Field(default=None, description="Name of the category group")
    balance: Decimal = Field(description="Current net balance of the envelope")


class EnvelopeUpdate(SQLModel):
    """Payload for updating an envelope's name, note, or category."""

    name: Optional[str] = Field(default=None, description="Updated unique display name")
    note: Optional[str] = Field(default=None, description="Updated note or goal description")
    category_name: Optional[str] = Field(
        default=None, description="Updated category name (or empty string to unassign)"
    )

class Config:
    arbitrary_types_allows = True

