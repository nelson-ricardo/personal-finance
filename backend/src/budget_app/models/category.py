"""Envelope category database table model."""

from typing import TYPE_CHECKING, Any, List, Optional

from sqlmodel import Field, Relationship

from budget_app.schemas import EnvelopeCategoryBase

if TYPE_CHECKING:
    from budget_app.models.envelope import Envelope


class EnvelopeCategory(EnvelopeCategoryBase, table=True):
    """Database table representing an envelope category group.

    Groups budgeting envelopes into logical sections (e.g. Fixed Monthly Expenses,
    Variable Monthly Expenses, Savings, Wants, System).
    """

    __tablename__: Any = "envelope_category"

    id: Optional[int] = Field(default=None, primary_key=True)

    # One-to-many relationship with child envelopes
    envelopes: List["Envelope"] = Relationship(back_populates="category")
