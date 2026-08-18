from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship

from budget_app.schemas import LedgerBase

if TYPE_CHECKING:
    from budget_app.models.envelope import Envelope
    from budget_app.models.transaction import Transaction


class Ledger(LedgerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    transaction_id: Optional[int] = Field(
        foreign_key="transaction.id", ondelete="CASCADE", nullable=False, default=None
    )
    envelope_id: Optional[int] = Field(
        default=None, foreign_key="envelope.id", nullable=False
    )

    transaction: Optional["Transaction"] = Relationship(back_populates="entries")
    envelope: Optional["Envelope"] = Relationship(back_populates="ledger_entries")
