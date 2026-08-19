"""add FINANCED to transactiontype enum

Revision ID: a1b2c3d4e5f6
Revises: 9b1886b01d4b
Create Date: 2026-08-19 18:49:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9b1886b01d4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE transactiontype ADD VALUE IF NOT EXISTS 'FINANCED'")


def downgrade() -> None:
    pass
