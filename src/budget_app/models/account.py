"""Account database table model."""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

from budget_app.schemas import AccountBase

if TYPE_CHECKING:
    from budget_app.models.envelope import Envelope
    from budget_app.models.transaction import Transaction


class Account(AccountBase, table=True):
    """Database table representing a financial account (Cash, Credit Card, or Loan).

    Inherits core balance, naming, and account type fields from AccountBase.
    Credit card accounts link to their corresponding payment envelope via envelope_id.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    envelope_id: Optional[int] = Field(default=None, foreign_key="envelope.id")

    # One-to-one link to the payment envelope (for Credit Card accounts)
    envelope: Optional["Envelope"] = Relationship(back_populates="account")

    # One-to-many relationship with transactions where this account was the payment method
    transactions: List["Transaction"] = Relationship(back_populates="account")

