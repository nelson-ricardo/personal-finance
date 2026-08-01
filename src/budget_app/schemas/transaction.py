from datetime import date
from typing import Optional, List, Dict
from decimal import Decimal

from sqlmodel import SQLModel, Field

from budget_app.schemas import ledger

class TransactionBase(SQLModel):
    merchant: str
    logged_date: date = Field(default_factory=date.today)
    posted_date: Optional[date] = Field(default=None)
    note: Optional[str] = Field(default=None)
    is_reconciled: Optional[bool] = Field(default=False)

class TransactionRequest(TransactionBase):
    """
        - is_financed: financed transaction, does not deduct from its assigned
        envelope but goes to the financed envelope.
        - term: number of monthly payments if it is financed
        - payment_method_name: used to match to the payment_method_id
        - ledger_entries: list of KV pairs with the envelope name and amount
        deducted
    """
    is_financed: bool 
    term: int | None = None
    payment_method_name: str 
    ledger_entries: List[ledger.LedgerRequest]