"""payroll attendance deductions and overtime

Payroll lines record the unpaid days (Absent, Half Day, unpaid leave) and the overtime
hours taken from attendance, with the amounts they add or deduct.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-27 17:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ("unpaid_days", "unpaid_deduction", "overtime_hours", "overtime_pay")


def upgrade() -> None:
    # A database brought to the baseline from a pre-migration version already has every
    # column of the current models, so only add the ones that are missing.
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("payroll")}
    missing = [c for c in COLUMNS if c not in existing]
    if missing:
        with op.batch_alter_table("payroll", schema=None) as batch_op:
            for name in missing:
                batch_op.add_column(sa.Column(name, sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("payroll", schema=None) as batch_op:
        for name in reversed(COLUMNS):
            batch_op.drop_column(name)
