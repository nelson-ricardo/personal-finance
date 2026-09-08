"""Envelope database table model."""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

from budget_app.schemas import EnvelopeBase

if TYPE_CHECKING:
    from budget_app.models.account import Account
    from budget_app.models.category import EnvelopeCategory
    from budget_app.models.envelope_split import EnvelopeSplit


class Envelope(EnvelopeBase, table=True):
    """Database table representing a budgeting category envelope.

    Holds allocated funds for specific expense categories (e.g. Groceries, Rent)
    or special purpose envelopes (Unassigned, Credit Card Payment).
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    category_id: Optional[int] = Field(default=None, foreign_key="envelope_category.id")

    # Category group relationship
    category: Optional["EnvelopeCategory"] = Relationship(back_populates="envelopes")

    # Reverse link for credit card payment envelope association
    account: "Account" = Relationship(
        back_populates="envelope", sa_relationship_kwargs={"uselist": False}
    )

    # One-to-many relationship with all splits allocated to this envelope
    splits: List["EnvelopeSplit"] = Relationship(back_populates="envelope")

    @property
    def ledger_entries(self) -> List["EnvelopeSplit"]:
        """Backward-compatible alias for splits."""
        return self.splits

