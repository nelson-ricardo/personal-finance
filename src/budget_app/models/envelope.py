from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

from budget_app.schemas.envelope import EnvelopeBase

if TYPE_CHECKING:
    from budget_app.models.account import Account
    from budget_app.models.ledger import Ledger


class Envelope(EnvelopeBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    account: "Account" = Relationship(
        back_populates="envelope", sa_relationship_kwargs={"uselist": False}
    )
    ledger_entries: List["Ledger"] = Relationship(back_populates="envelope")
