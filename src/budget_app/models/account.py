from typing import Optional, TYPE_CHECKING, List

from sqlmodel import Field, Relationship
from budget_app.schemas.account import AccountBase

if TYPE_CHECKING:
    from budget_app.models.transaction import Transaction
    from budget_app.models.envelope import Envelope


class Account(AccountBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    envelope_id: Optional[int] = Field(default=None, foreign_key="envelope.id")

    envelope: Optional["Envelope"] = Relationship(back_populates="account")
    transactions: List["Transaction"] = Relationship(back_populates="account")