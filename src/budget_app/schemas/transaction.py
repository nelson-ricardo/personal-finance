from datetime import date
from typing import Optional

from sqlmodel import SQLModel, Field

class TransactionBase(SQLModel):
    merchant: str
    payment_method_id: int = Field(foreign_key="account.id")
    logged_date: date = Field(default_factory=date.today)
    posted_date: Optional[date] = Field(default=None)
    note: Optional[str] = Field(default=None)
    is_reconciled: Optional[bool] = Field(default=False)