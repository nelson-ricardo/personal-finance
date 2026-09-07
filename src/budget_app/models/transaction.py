"""Transaction database table model."""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Column, Field, Relationship
from sqlmodel import Enum as SQLEnum

from budget_app.schemas import TransactionBase, TransactionType

if TYPE_CHECKING:
    from budget_app.models.account import Account
    from budget_app.models.envelope_split import EnvelopeSplit


class Transaction(TransactionBase, table=True):
    """Database table representing a master transaction.

    Encapsulates merchant, dates, reconciliation state, notes, payment account linkage,
    transaction classification (INCOME, EXPENSE, TRANSFER, FINANCED), and associated
    envelope split entries.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    payment_method_id: Optional[int] = Field(
        default=None, foreign_key="account.id", nullable=False
    )
    transaction_type: TransactionType = Field(
        sa_column=Column(
            SQLEnum(TransactionType), nullable=False, default=TransactionType.EXPENSE
        )
    )

    # Link to payment method account
    account: "Account" = Relationship(back_populates="transactions")

    # One-to-many relationship with child envelope split entries (cascades on delete)
    splits: List["EnvelopeSplit"] = Relationship(
        back_populates="transaction", cascade_delete=True
    )

    @property
    def entries(self) -> List["EnvelopeSplit"]:
        """Backward-compatible alias for splits."""
        return self.splits


