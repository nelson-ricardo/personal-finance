"""Transaction data schemas and classification types."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from sqlmodel import Field, SQLModel

from budget_app.schemas import ledger


class TransactionType(str, Enum):
    """Classification of transactions within the budgeting system."""

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"
    FINANCED = "FINANCED"
    REVERSAL = "REVERSAL"


class TransactionBase(SQLModel):
    """Base schema for master transactions containing shared metadata."""

    merchant: str = Field(description="Payee, merchant, or income source name")
    logged_date: date = Field(default_factory=date.today, description="Date when the transaction occurred or was recorded")
    posted_date: Optional[date] = Field(default=None, description="Date when the transaction cleared on bank statement")
    note: Optional[str] = Field(default=None, description="Optional user notes or tags")
    is_reconciled: Optional[bool] = Field(default=False, description="Whether the transaction has been matched to bank records")


class TransactionRequest(TransactionBase):
    """Payload for creating a regular transaction with ledger envelope splits.

    Attributes:
        payment_method_name: Name of the account used (Cash, Credit Card).
        transaction_type: INCOME, EXPENSE, TRANSFER, or FINANCED.
        ledger_entries: Envelope allocations and deduction/addition amounts.
    """

    payment_method_name: str = Field(description="Name of the paying or receiving Account")
    transaction_type: TransactionType = Field(description="Type classification of this transaction")
    ledger_entries: List[ledger.LedgerRequest] = Field(description="Envelope allocations and amounts")


class FinancedTransaction(TransactionBase):
    """Payload for creating a financed installment transaction.

    Attributes:
        term: Number of installment months.
        amount: Total principal amount financed.
        envelope_name: Optional custom envelope name (auto-generated if None).
        payment_method_name: Name of the credit card account used.
    """

    term: int = Field(description="Number of monthly payment terms")
    amount: Decimal = Field(description="Total financed purchase amount")
    envelope_name: str | None = Field(default=None, description="Optional custom name for the financing envelope")
    payment_method_name: str = Field(description="Name of the credit card account used")


class TransactionResponse(TransactionBase):
    """Response model representing a transaction with its computed overall total.

    Instead of listing individual ledger lines, provides the net total spent/received,
    with automated credit card balancing entries excluded from the total.
    """

    id: int = Field(description="Unique database identifier")
    payment_method_id: int = Field(description="ID of the associated payment account")
    payment_method_name: str = Field(description="Display name of the payment account")
    transaction_type: TransactionType = Field(description="Transaction type enum")
    total: Decimal = Field(description="Computed positive monetary total of the transaction")

    @property
    def total_amount(self) -> Decimal:
        """Alias for total."""
        return self.total

    @property
    def account_name(self) -> str:
        """Alias for payment_method_name."""
        return self.payment_method_name