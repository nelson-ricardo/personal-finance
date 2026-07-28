from typing import TYPE_CHECKING, Optional
from decimal import Decimal

from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy import Numeric

if TYPE_CHECKING:
    from budget_app.models.transaction import Transaction
    from budget_app.models.envelope import Envelope


class Ledger(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: int = Field(
        foreign_key="transaction.id",
        ondelete="CASCADE"
    )
    envelope_id: int = Field(foreign_key="envelope.id")
    amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column= Column(Numeric(precision=14, scale=2), nullable=False)
    )

    transaction: Optional["Transaction"] = Relationship(back_populates="entries")
    envelope: Optional["Envelope"] = Relationship(back_populates="ledger_entries")