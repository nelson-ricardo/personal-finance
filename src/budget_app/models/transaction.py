from datetime import datetime, date
from typing import Optional
import uuid

from sqlmodel import SQLModel, Field

# database model
class Transaction(SQLModel, Table=True):
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False
    )
    merchant: str
    # TODO: make a connection with the account table
    payment_method_id: uuid.UUID
    logged_date: date = Field(default_factory=datetime.today)
    posted_date: Optional[date] = Field(default=None)
    note: Optional[str] = Field(default=None)
    is_reconciled: Optional[bool] = Field(default=False)
    # TODO: make a connection with the ledger table
    ledger_id: uuid.UUID