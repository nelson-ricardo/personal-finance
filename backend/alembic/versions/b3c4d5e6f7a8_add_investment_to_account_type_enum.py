"""add INVESTMENT to account_type_enum

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-10-21 20:55:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE account_type_enum ADD VALUE IF NOT EXISTS 'INVESTMENT'")
        op.execute("ALTER TYPE account_type_enum ADD VALUE IF NOT EXISTS 'investment'")


def downgrade() -> None:
    pass
