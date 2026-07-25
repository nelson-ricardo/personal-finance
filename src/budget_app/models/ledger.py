from typing import TYPE_CHECKING, Optional
from decimal import Decimal
import uuid

from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy import Numeric

if TYPE_CHECKING:
    from budget_app.models.transaction import Transaction
    from budget_app.models.envelope import Envelope


class Ledger(SQLModel, table=True):
    id: uuid.UUID = Field(
        primary_key=True,
        index=True,
        nullable=False,
        default_factory= uuid.uuid4
    )
    transaction_id: uuid.UUID = Field(
        foreign_key="transaction.id",
        ondelete="CASCADE"
    )
    envelope_id: uuid.UUID = Field(foreign_key="envelope.id")
    amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column= Column(Numeric(precision=14, scale=2), nullable=False)
    )

    transaction: Optional["Transaction"] = Relationship(back_populates="ledger")
    envelope: Optional["Envelope"] = Relationship(back_populates="entires")