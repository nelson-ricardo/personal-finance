"""Envelope database table model."""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

from budget_app.schemas import EnvelopeBase

if TYPE_CHECKING:
    from budget_app.models.account import Account
    from budget_app.models.ledger import Ledger


class Envelope(EnvelopeBase, table=True):
    """Database table representing a budgeting category envelope.

    Holds allocated funds for specific expense categories (e.g. Groceries, Rent)
    or special purpose envelopes (Unassigned, Credit Card Payment).
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    # Reverse link for credit card payment envelope association
    account: "Account" = Relationship(
        back_populates="envelope", sa_relationship_kwargs={"uselist": False}
    )

    # One-to-many relationship with all ledger splits allocated to this envelope
    ledger_entries: List["Ledger"] = Relationship(back_populates="envelope")

