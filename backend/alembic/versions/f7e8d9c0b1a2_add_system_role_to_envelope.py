"""add system_role to envelope

Revision ID: f7e8d9c0b1a2
Revises: c2c83438c290
Create Date: 2026-10-10 11:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f7e8d9c0b1a2'
down_revision: Union[str, Sequence[str], None] = 'c2c83438c290'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

system_envelope_type_enum = sa.Enum(
    'UNASSIGNED', 'CREDIT_CARD_PAYMENT', 'ACCOUNT_ADJUSTMENT',
    name='system_envelope_type_enum'
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        pg_enum = postgresql.ENUM(
            'UNASSIGNED', 'CREDIT_CARD_PAYMENT', 'ACCOUNT_ADJUSTMENT',
            name='system_envelope_type_enum'
        )
        pg_enum.create(bind, checkfirst=True)

    op.add_column(
        'envelope',
        sa.Column(
            'system_role',
            system_envelope_type_enum,
            nullable=True,
        )
    )
    op.create_index('ix_envelope_system_role', 'envelope', ['system_role'], unique=True)

    # Backfill existing system envelopes by default names
    op.execute("UPDATE envelope SET system_role = 'UNASSIGNED' WHERE name = 'Unassigned'")
    op.execute("UPDATE envelope SET system_role = 'CREDIT_CARD_PAYMENT' WHERE name = 'Credit Card Payment'")
    op.execute("UPDATE envelope SET system_role = 'ACCOUNT_ADJUSTMENT' WHERE name = 'Account Adjustment'")


def downgrade() -> None:
    op.drop_index('ix_envelope_system_role', table_name='envelope')
    op.drop_column('envelope', 'system_role')

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        pg_enum = postgresql.ENUM(
            'UNASSIGNED', 'CREDIT_CARD_PAYMENT', 'ACCOUNT_ADJUSTMENT',
            name='system_envelope_type_enum'
        )
        pg_enum.drop(bind, checkfirst=True)
