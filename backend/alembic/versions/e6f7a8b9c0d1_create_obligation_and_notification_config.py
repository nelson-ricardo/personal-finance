"""create obligation and notification_config tables

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-11-02 21:18:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, Sequence[str], None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create obligation table
    op.create_table(
        'obligation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('due_day', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column('note', sa.String(), nullable=True),
        sa.Column(
            'account_id',
            sa.Integer(),
            sa.ForeignKey('account.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_paid_date', sa.Date(), nullable=True),
        sa.Column('last_paid_amount', sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_obligation_account_id', 'obligation', ['account_id'])
    op.create_index('ix_obligation_due_day', 'obligation', ['due_day'])

    # 2. Create notification_config table
    op.create_table(
        'notification_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reminder_time', sa.String(), nullable=False, server_default='09:00'),
        sa.Column('reminder_days_ahead', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_dispatched_date', sa.Date(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('notification_config')
    op.drop_index('ix_obligation_due_day', table_name='obligation')
    op.drop_index('ix_obligation_account_id', table_name='obligation')
    op.drop_table('obligation')
