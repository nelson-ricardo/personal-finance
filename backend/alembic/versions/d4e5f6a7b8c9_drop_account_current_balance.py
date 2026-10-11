"""add interest transaction types and drop account current_balance

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-07 11:57:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'INTEREST_CHARGE'")
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'INTEREST_EARNED'")
    op.drop_column("account", "current_balance")


def downgrade() -> None:
    op.add_column(
        "account",
        sa.Column(
            "current_balance",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
            server_default="0.00",
        ),
    )
