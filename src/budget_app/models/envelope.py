from typing import TYPE_CHECKING, List
import uuid

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from budget_app.models.ledger import Ledger

class Envelope(SQLModel, table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        nullable=False,
        index=True
    )
    name: str
    note: str
    is_active: bool = Field(default=True)

    ledger_entries: List["Ledger"] = Relationship(back_populates="envelope")