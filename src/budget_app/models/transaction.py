from typing import Optional, TYPE_CHECKING, List

from sqlmodel import Field, Relationship
from budget_app.schemas.transaction import TransactionBase

if TYPE_CHECKING:
    from budget_app.models.account import Account
    from budget_app.models.ledger import Ledger

# database model
class Transaction(TransactionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    account: "Account" = Relationship(back_populates="transactions")
    entries: List["Ledger"] = Relationship(
        back_populates="transaction", 
        cascade_delete=True
    )