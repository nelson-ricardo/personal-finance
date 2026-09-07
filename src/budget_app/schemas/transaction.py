"""Transaction data schemas and classification types."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional

from pydantic import model_validator
from sqlmodel import Field, SQLModel

from budget_app.schemas.envelope_split import (
    EnvelopeSplitRequest,
    EnvelopeSplitResponse,
)


class TransactionType(str, Enum):
    """Classification of transactions within the budgeting system."""

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"
    FINANCED = "FINANCED"
    REVERSAL = "REVERSAL"
    INTEREST_CHARGE = "INTEREST_CHARGE"
    INTEREST_EARNED = "INTEREST_EARNED"


class TransactionBase(SQLModel):
    """Base schema for master transactions containing shared metadata."""

    merchant: str = Field(description="Payee, merchant, or income source name")
    logged_date: date = Field(default_factory=date.today, description="Date when the transaction occurred or was recorded")
    posted_date: Optional[date] = Field(default=None, description="Date when the transaction cleared on bank statement")
    note: Optional[str] = Field(default=None, description="Optional user notes or tags")
    is_reconciled: Optional[bool] = Field(default=False, description="Whether the transaction has been matched to bank records")


class TransactionRequest(TransactionBase):
    """Payload for creating a regular transaction with envelope splits.

    Attributes:
        payment_method_name: Name of the account used (Cash, Credit Card).
        transaction_type: INCOME, EXPENSE, TRANSFER, or FINANCED.
        splits: Envelope allocations and deduction/addition amounts.
    """

    payment_method_name: str = Field(description="Name of the paying or receiving Account")
    transaction_type: TransactionType = Field(description="Type classification of this transaction")
    splits: List[EnvelopeSplitRequest] = Field(description="Envelope allocations and amounts")

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_split_names(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "splits" not in data:
                if "ledger_entries" in data:
                    data["splits"] = data["ledger_entries"]
                elif "entries" in data:
                    data["splits"] = data["entries"]
        return data

    @property
    def ledger_entries(self) -> List[EnvelopeSplitRequest]:
        """Backward-compatible alias for splits."""
        return self.splits

    @property
    def entries(self) -> List[EnvelopeSplitRequest]:
        """Backward-compatible alias for splits."""
        return self.splits


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


class TransactionDetailResponse(TransactionResponse):
    """Detailed response model for a single transaction including its envelope split entries."""

    splits: List[EnvelopeSplitResponse] = Field(
        default_factory=list,
        description="List of envelope split entries with envelope and amount information",
    )

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_split_names(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "splits" not in data:
                if "entries" in data:
                    data["splits"] = data["entries"]
                elif "ledger_entries" in data:
                    data["splits"] = data["ledger_entries"]
        return data

    @property
    def entries(self) -> List[EnvelopeSplitResponse]:
        """Alias for splits."""
        return self.splits

    @property
    def ledger_entries(self) -> List[EnvelopeSplitResponse]:
        """Backward-compatible alias for splits."""
        return self.splits


class TransactionUpdateRequest(SQLModel):
    """Payload for modifying an existing transaction.

    All fields are optional; only specified fields will be updated.
    Attributes:
        merchant: Updated payee, merchant, or income source name.
        logged_date: Updated transaction date.
        posted_date: Updated cleared date.
        note: Updated user notes or tags.
        is_reconciled: Updated reconciliation status.
        payment_method_name: Updated account name (Cash, Credit Card, etc.).
        splits: Updated envelope allocations and split amounts.
    """

    merchant: Optional[str] = Field(default=None, description="Payee, merchant, or income source name")
    logged_date: Optional[date] = Field(default=None, description="Date when the transaction occurred or was recorded")
    posted_date: Optional[date] = Field(default=None, description="Date when the transaction cleared on bank statement")
    note: Optional[str] = Field(default=None, description="Optional user notes or tags")
    is_reconciled: Optional[bool] = Field(default=None, description="Whether the transaction has been matched to bank records")
    payment_method_name: Optional[str] = Field(default=None, description="Name of the paying or receiving Account")
    splits: Optional[List[EnvelopeSplitRequest]] = Field(
        default=None, description="Updated envelope allocations and amounts"
    )

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_split_names(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "splits" not in data:
                if "ledger_entries" in data:
                    data["splits"] = data["ledger_entries"]
                elif "entries" in data:
                    data["splits"] = data["entries"]
        return data

    @property
    def ledger_entries(self) -> Optional[List[EnvelopeSplitRequest]]:
        """Backward-compatible alias for splits."""
        return self.splits

    @property
    def entries(self) -> Optional[List[EnvelopeSplitRequest]]:
        """Backward-compatible alias for splits."""
        return self.splits



class FinancedTransactionUpdateRequest(SQLModel):
    """Payload for modifying an existing financed installment transaction.

    All fields are optional; only specified fields will be updated.
    If amount is modified, term must also be provided to calculate new monthly payments.

    Attributes:
        merchant: Updated merchant or payee name.
        amount: Updated total principal financed amount.
        term: Updated number of monthly installment terms.
        payment_method_name: Updated credit card account name.
        envelope_name: Optional custom or updated envelope name.
        note: Updated user notes or tags.
        logged_date: Updated transaction date.
        posted_date: Updated cleared date.
        is_reconciled: Updated reconciliation status.
    """

    merchant: Optional[str] = Field(
        default=None, description="Updated merchant or payee name"
    )
    amount: Optional[Decimal] = Field(
        default=None, description="Updated total financed amount"
    )
    term: Optional[int] = Field(
        default=None, description="Updated number of monthly installment terms"
    )
    payment_method_name: Optional[str] = Field(
        default=None, description="Updated name of the credit card account used"
    )
    envelope_name: Optional[str] = Field(
        default=None, description="Optional custom name for the financing envelope"
    )
    note: Optional[str] = Field(
        default=None, description="Updated user notes or tags"
    )
    logged_date: Optional[date] = Field(
        default=None, description="Updated transaction date"
    )
    posted_date: Optional[date] = Field(
        default=None, description="Updated bank statement posted date"
    )
    is_reconciled: Optional[bool] = Field(
        default=None, description="Updated reconciliation status"
    )