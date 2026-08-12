from decimal import Decimal

from sqlalchemy import Numeric
from sqlmodel import Column, Field, SQLModel


class LedgerBase(SQLModel):
    amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(precision=14, scale=2), nullable=False),
    )


class LedgerRequest(LedgerBase):
    envelope_name: str
