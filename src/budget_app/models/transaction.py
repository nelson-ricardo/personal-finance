from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Column, Field, Relationship
from sqlmodel import Enum as SQLEnum

from budget_app.schemas import TransactionBase, TransactionType

if TYPE_CHECKING:
    from budget_app.models.account import Account
    from budget_app.models.ledger import Ledger


# database model
class Transaction(TransactionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    payment_method_id: Optional[int] = Field(
        default=None, foreign_key="account.id", nullable=False
    )
    transaction_type: TransactionType = Field(
        sa_column=Column(
            SQLEnum(TransactionType), nullable=False, default=TransactionType.EXPENSE
        )
    )

    account: "Account" = Relationship(back_populates="transactions")
    entries: List["Ledger"] = Relationship(
        back_populates="transaction", cascade_delete=True
    )
