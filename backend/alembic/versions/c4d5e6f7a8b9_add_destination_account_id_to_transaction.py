"""add destination_account_id to transaction

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-10-21 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'transaction',
        sa.Column(
            'destination_account_id',
            sa.Integer(),
            sa.ForeignKey('account.id', ondelete='SET NULL'),
            nullable=True,
        )
    )
    op.create_index(
        'ix_transaction_destination_account_id',
        'transaction',
        ['destination_account_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_transaction_destination_account_id', table_name='transaction')
    op.drop_column('transaction', 'destination_account_id')
