from typing import TYPE_CHECKING, List, Optional

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from budget_app.models.ledger import Ledger
    from budget_app.models.account import Account

class Envelope(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    note: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)

    account: Optional["Account"] = Relationship(back_populates="envelope",
                                                sa_relationship_kwargs={"uselist": False}
                                                )
    ledger_entries: List["Ledger"] = Relationship(back_populates="envelope")