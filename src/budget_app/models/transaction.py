from datetime import date
from typing import Optional, TYPE_CHECKING, List

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from budget_app.models.account import Account
    from budget_app.models.ledger import Ledger

# database model
class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    merchant: str
    payment_method_id: int = Field(foreign_key="account.id")
    logged_date: date = Field(default_factory=date.today)
    posted_date: Optional[date] = Field(default=None)
    note: Optional[str] = Field(default=None)
    is_reconciled: Optional[bool] = Field(default=False)

    account: Optional["Account"] = Relationship(back_populates="transactions")
    entries: List["Ledger"] = Relationship(
        back_populates="transaction", 
        cascade_delete=True
    )