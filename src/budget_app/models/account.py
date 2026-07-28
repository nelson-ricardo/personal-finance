from typing import Optional, TYPE_CHECKING, List
from decimal import Decimal
from datetime import date
from enum import Enum

from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy import Numeric, Enum as SAEnum

if TYPE_CHECKING:
    from budget_app.models.transaction import Transaction
    from budget_app.models.envelope import Envelope

class AccountType(str, Enum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    LOAN = "loan"

class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    current_balance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(precision=14, scale=2), nullable=False)
    )
    account_type: AccountType = Field(
        sa_column=Column(
            SAEnum(AccountType, name="account_type_enum"),
            nullable=False
        )
    )
    """
    Fields under here are only used when an account is either a loan or a 
    credit card
    """
    total_statement_balance: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(precision=14, scale=2))
    )
    interest_saving_balance: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(precision=14, scale=2))
    )
    monthly_payment: Optional[Decimal] = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(precision=14, scale=2))
    )
    due_date: Optional[date] = Field(default=None)
    envelope_id: Optional[int] = Field(default=None, foreign_key="envelope.id")

    envelope: Optional["Envelope"] = Relationship(back_populates="account")
    transactions: List["Transaction"] = Relationship(back_populates="account")