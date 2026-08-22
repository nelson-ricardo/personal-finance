"""Account data schemas and enumerations."""

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

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

    name: str = Field(unique=True, description="Unique display name of the account")
    current_balance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(precision=14, scale=2), nullable=False),
        description="Current liquid balance (for Cash) or outstanding owed balance (for Credit Card/Loan)",
    )
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

