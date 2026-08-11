"""align grants with the PKG-012 six-field contract

Revision ID: f9a1c3e5b702
Revises: e8f4b7c2d305
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f9a1c3e5b702"
down_revision: str | None = "e8f4b7c2d305"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("grants", recreate="always") as batch_op:
        batch_op.add_column(
            sa.Column("employer_withholding_file_number", sa.String(128), nullable=True)
        )
        batch_op.alter_column(
            "indexed_amount",
            existing_type=sa.Numeric(14, 2),
            nullable=True,
        )
        batch_op.drop_constraint("ck_grants_indexed_amount_non_negative", type_="check")
        batch_op.drop_constraint("ck_grants_work_dates_order", type_="check")
        batch_op.create_check_constraint(
            "ck_grants_indexed_amount_non_negative",
            "indexed_amount IS NULL OR indexed_amount >= 0",
        )
        batch_op.create_check_constraint(
            "ck_grants_work_dates_order", "work_end_date > work_start_date"
        )


def downgrade() -> None:
    # A downgrade cannot invent indexed values for PKG-012 rows.
    connection = op.get_bind()
    missing = connection.execute(
        sa.text("SELECT COUNT(*) FROM grants WHERE indexed_amount IS NULL")
    ).scalar_one()
    if missing:
        raise RuntimeError(
            "cannot downgrade while system-derived indexed amounts are absent"
        )
    with op.batch_alter_table("grants", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_grants_work_dates_order", type_="check")
        batch_op.drop_constraint("ck_grants_indexed_amount_non_negative", type_="check")
        batch_op.create_check_constraint(
            "ck_grants_indexed_amount_non_negative", "indexed_amount >= 0"
        )
        batch_op.create_check_constraint(
            "ck_grants_work_dates_order", "work_end_date >= work_start_date"
        )
        batch_op.alter_column(
            "indexed_amount",
            existing_type=sa.Numeric(14, 2),
            nullable=False,
        )
        batch_op.drop_column("employer_withholding_file_number")
