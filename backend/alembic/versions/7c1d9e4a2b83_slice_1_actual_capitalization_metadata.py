"""slice 1 actual capitalization metadata

Revision ID: 7c1d9e4a2b83
Revises: 5b8d2e1f4c61
Create Date: 2026-06-28 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c1d9e4a2b83"
down_revision: Union[str, None] = "5b8d2e1f4c61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.add_column("actual_capitalizations", sa.Column("source_basis", sa.String(length=255), nullable=True))
        op.add_column("actual_capitalizations", sa.Column("planner_assertion", sa.String(length=255), nullable=True))
        op.add_column("actual_capitalizations", sa.Column("planner_assertion_basis", sa.Text(), nullable=True))
        return

    with op.batch_alter_table("actual_capitalizations") as batch_op:
        batch_op.add_column(sa.Column("source_basis", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("planner_assertion", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("planner_assertion_basis", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("actual_capitalizations") as batch_op:
        batch_op.drop_column("planner_assertion_basis")
        batch_op.drop_column("planner_assertion")
        batch_op.drop_column("source_basis")
