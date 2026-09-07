"""Account data schemas and enumerations."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import model_validator
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Numeric
from sqlmodel import Column, Field, SQLModel


class AccountType(str, Enum):
    """Supported financial account types in the budgeting system."""

    CASH = "cash"
    CREDIT_CARD = "credit_card"
    LOAN = "loan"


class AccountBase(SQLModel):
    """Base schema for financial accounts.

    Contains foundational fields applicable across all account types, as well as
    credit/debt-specific fields (statement balance, interest saving balance, due date).
    """

    model_config = {"extra": "allow"}

    name: str = Field(unique=True, description="Unique display name of the account")
    account_type: AccountType = Field(
        sa_column=Column(SAEnum(AccountType, name="account_type_enum"), nullable=False),
        description="Type classification of the financial account",
    )

    # Debt and Credit Card specific tracking fields
    total_statement_balance: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(precision=14, scale=2)),
        description="Full statement balance owed on the last billing cycle",
    )
    interest_saving_balance: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(precision=14, scale=2)),
        description="Balance needed to avoid interest charges (e.g. for promotional rates)",
    )
    monthly_payment: Optional[Decimal] = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(precision=14, scale=2)),
        description="Minimum or scheduled monthly payment amount",
    )
    due_date: Optional[date] = Field(
        default=None,
        description="Next payment due date",
    )
    is_active: bool = Field(
        default=True,
        description="Flag indicating whether this account is active",
    )


class AccountUpdate(SQLModel):
    """Schema for updating account details."""

    name: Optional[str] = Field(default=None, description="New display name")
    is_active: Optional[bool] = Field(default=None, description="Active status")
    total_statement_balance: Optional[Decimal] = Field(default=None)
    interest_saving_balance: Optional[Decimal] = Field(default=None)
    monthly_payment: Optional[Decimal] = Field(default=None)
    due_date: Optional[date] = Field(default=None)


class AccountCreate(AccountBase):
    """Schema for creating a new account with an optional starting balance."""

    starting_balance: Decimal = Field(
        default=Decimal("0.00"),
        description="Initial starting balance (added to Cash via Unassigned, or debt for Credit/Loan via Account Adjustment)",
    )

    @model_validator(mode="before")
    @classmethod
    def handle_current_balance_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "current_balance" in data and "starting_balance" not in data:
                data["starting_balance"] = data["current_balance"]
        return data


class AccountWithBalance(AccountBase):
    """Response schema for an account including its dynamically derived balance."""

    id: int = Field(description="Unique account ID")
    current_balance: Decimal = Field(
        default=Decimal("0.00"),
        description="Derived balance (liquid cash assets or outstanding debt owed)",
    )
    envelope_id: Optional[int] = Field(
        default=None, description="Linked CC payment envelope ID"
    )


AccountResponse = AccountWithBalance


class InterestChargeRequest(SQLModel):
    """Request payload for logging an interest charge on a debt account."""

    account_name: str = Field(description="Name of the Credit Card or Loan account")
    amount: Decimal = Field(description="Interest charge amount (must be positive)")
    note: Optional[str] = Field(default="Interest Charge", description="Optional note")
    logged_date: Optional[date] = Field(default_factory=date.today, description="Transaction date")


class InterestEarnedRequest(SQLModel):
    """Request payload for logging interest earned on a cash account."""

    account_name: str = Field(description="Name of the Cash/Savings account")
    amount: Decimal = Field(description="Interest earned amount (must be positive)")
    note: Optional[str] = Field(default="Interest Earned", description="Optional note")
    logged_date: Optional[date] = Field(default_factory=date.today, description="Transaction date")
