from datetime import date
from typing import Optional
from sqlmodel import SQLModel
from decimal import Decimal
from enum import Enum

from sqlmodel import Column, Field
from sqlalchemy import Enum as SAEnum, Numeric

class AccountType(str, Enum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    LOAN = "loan"

class AccountBase(SQLModel):
    name: str = Field(unique=True)
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