"""remove placeholder department metrics

Seniority, attrition, trend and tag were fixed demo values shown as if they were
measured. Average seniority is now calculated from hire dates; the others had no
data behind them and are removed.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-05 16:30:43.280710
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ("tag", "seniority", "attrition", "trend")


def upgrade() -> None:
    # Databases brought to the baseline from a pre-migration version may not have these
    # columns, so only drop the ones that exist.
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("departments")}
    to_drop = [c for c in COLUMNS if c in existing]
    if to_drop:
        with op.batch_alter_table("departments", schema=None) as batch_op:
            for column in to_drop:
                batch_op.drop_column(column)


def downgrade() -> None:
    with op.batch_alter_table("departments", schema=None) as batch_op:
        batch_op.add_column(sa.Column("trend", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("attrition", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("seniority", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("tag", sa.String(length=40), nullable=False, server_default=""))
