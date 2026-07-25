from typing import Optional
from decimal import Decimal
from datetime import date
from enum import Enum
import uuid

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import Numeric, Enum as SAEnum

class AccountType(str, Enum):
    CASH = "cash"
    CREDIT_CARD = "credit credit"
    LOAN = "loan"

class Account(SQLModel, Table=True):
    id: uuid.UUID = Field(
        primary_key=True,
        nullable=False,
        index=True,
        default_factory=uuid.uuid4
    )
    name: str
    current_balance: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(precision=14, scale=2), nullable=False)
    )
    account_type: AccountType = Field(
        sa_column_kwargs={"type_": SAEnum(AccountType, name="account_type_enum")}
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
    monthly_payment: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(precision=14, scale=2))
    )
    due_date: Optional[date] = Field(default=None, default_factory=date.today)