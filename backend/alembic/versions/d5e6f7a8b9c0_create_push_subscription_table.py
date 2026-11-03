"""create push_subscription table

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-11-02 20:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'push_subscription',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.String(), nullable=False),
        sa.Column('p256dh_key', sa.String(), nullable=False),
        sa.Column('auth_key', sa.String(), nullable=False),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_push_subscription_endpoint',
        'push_subscription',
        ['endpoint'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_push_subscription_endpoint', table_name='push_subscription')
    op.drop_table('push_subscription')
