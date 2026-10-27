"""payroll proration and adjustments

Employees get a last working day (termination_date) so payroll can skip leavers and pay
only the days worked in a joining or leaving month. Payroll lines get a free adjustment
(+ earning / - deduction), a note, and the number of paid days for a partial month.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-27 16:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_COLUMNS = {
    "employees": [sa.Column("termination_date", sa.Date(), nullable=True)],
    "payroll": [sa.Column("adjustment", sa.Float(), nullable=False, server_default="0"),
                sa.Column("note", sa.String(length=200), nullable=False, server_default=""),
                sa.Column("paid_days", sa.Integer(), nullable=True)],
}


def upgrade() -> None:
    # A database brought to the baseline from a pre-migration version already has every
    # column of the current models, so only add the ones that are missing.
    insp = sa.inspect(op.get_bind())
    for table, columns in NEW_COLUMNS.items():
        existing = {c["name"] for c in insp.get_columns(table)}
        missing = [c for c in columns if c.name not in existing]
        if missing:
            with op.batch_alter_table(table, schema=None) as batch_op:
                for column in missing:
                    batch_op.add_column(column)


def downgrade() -> None:
    with op.batch_alter_table("payroll", schema=None) as batch_op:
        batch_op.drop_column("paid_days")
        batch_op.drop_column("note")
        batch_op.drop_column("adjustment")
    with op.batch_alter_table("employees", schema=None) as batch_op:
        batch_op.drop_column("termination_date")
