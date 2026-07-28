"""add PKG-006 M01 client case fields

Revision ID: f3a7c9d2e610
Revises: a9c4e7f2b615
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "f3a7c9d2e610"
down_revision: str | None = "a9c4e7f2b615"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("clients") as batch_op:
        batch_op.add_column(sa.Column("employment_status", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("planned_retirement_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("planned_retirement_age", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_clients_employment_status",
            "employment_status IS NULL OR employment_status IN "
            "('salaried_employee', 'self_employed', 'salaried_and_self_employed', "
            "'not_currently_working', 'unknown')",
        )
        batch_op.create_check_constraint(
            "ck_clients_planned_retirement_age",
            "planned_retirement_age IS NULL "
            "OR planned_retirement_age BETWEEN 18 AND 120",
        )
        batch_op.create_check_constraint(
            "ck_clients_planned_retirement_exclusive",
            "planned_retirement_age IS NULL OR planned_retirement_date IS NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("clients") as batch_op:
        batch_op.drop_constraint(
            "ck_clients_planned_retirement_exclusive",
            type_="check",
        )
        batch_op.drop_constraint("ck_clients_planned_retirement_age", type_="check")
        batch_op.drop_constraint("ck_clients_employment_status", type_="check")
        batch_op.drop_column("planned_retirement_age")
        batch_op.drop_column("planned_retirement_date")
        batch_op.drop_column("employment_status")
