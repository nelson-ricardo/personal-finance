"""change account due_date to day of month

Revision ID: a2b3c4d5e6f7
Revises: f7e8d9c0b1a2
Create Date: 2026-10-17 17:21:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f7e8d9c0b1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            ALTER TABLE account
            ALTER COLUMN due_date TYPE INTEGER
            USING (
                CASE
                    WHEN due_date IS NOT NULL THEN EXTRACT(DAY FROM due_date)::INTEGER
                    ELSE NULL
                END
            )
            """
        )
        op.create_check_constraint(
            "account_due_date_day_range",
            "account",
            "due_date IS NULL OR (due_date >= 1 AND due_date <= 31)",
        )
    else:
        with op.batch_alter_table("account") as batch_op:
            batch_op.alter_column("due_date", type_=sa.Integer())


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("account_due_date_day_range", "account", type_="check")
        op.execute(
            """
            ALTER TABLE account
            ALTER COLUMN due_date TYPE DATE
            USING (
                CASE
                    WHEN due_date IS NOT NULL THEN MAKE_DATE(
                        2026,
                        1,
                        due_date
                    )
                    ELSE NULL
                END
            )
            """
        )
    else:
        with op.batch_alter_table("account") as batch_op:
            batch_op.alter_column("due_date", type_=sa.Date())
