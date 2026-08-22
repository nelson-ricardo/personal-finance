from datetime import date
from enum import Enum
from typing import List, Optional
from decimal import Decimal

from sqlmodel import Field, SQLModel

from budget_app.schemas import ledger


class TransactionType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"
    FINANCED = "FINANCED"


class TransactionBase(SQLModel):
    merchant: str
    logged_date: date = Field(default_factory=date.today)
    posted_date: Optional[date] = Field(default=None)
    note: Optional[str] = Field(default=None)
    is_reconciled: Optional[bool] = Field(default=False)


class TransactionRequest(TransactionBase):
    """
    - payment_method_name: used to match to the payment_method_id
    - transaction_type: INCOME, EXPENSE, TRANSFER, or FINANCED
    - ledger_entries: list of KV pairs with the envelope name and amount
    deducted
    """

    payment_method_name: str
    transaction_type: TransactionType
    ledger_entries: List[ledger.LedgerRequest]

class FinancedTransaction(TransactionBase):
    """
        term: number of monthly payments
        amount: total amount financed
        envelope_name: [OPTIONAL] desired name for the envelope
        payment_method_name: name of the account used
    """
    term: int
    amount: Decimal
    envelope_name: str | None
    payment_method_name: str


class TransactionResponse(TransactionBase):
    """Schema representing fetched transaction with its computed total."""
    id: int
    payment_method_id: int
    payment_method_name: str
    transaction_type: TransactionType
    total: Decimal

    @property
    def total_amount(self) -> Decimal:
        return self.total

    @property
    def account_name(self) -> str:
        return self.payment_method_name