from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    from budget_app.models.envelope import Envelope
    from budget_app.models.transaction import Transaction


class EnvelopeBase(SQLModel):
    name: str = Field(unique=True)
    note: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)


class EnvelopeTransfer(SQLModel):
    source: Envelope
    new_balance_src: Decimal
    destination: Envelope
    new_balance_dest: Decimal
    transfer_transaction: Transaction


class Config:
    arbitrary_types_allows = True
