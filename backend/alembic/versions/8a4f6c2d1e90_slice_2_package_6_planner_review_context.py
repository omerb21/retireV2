"""slice 2 package 6 planner review context

Revision ID: 8a4f6c2d1e90
Revises: 7c1d9e4a2b83
Create Date: 2026-06-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8a4f6c2d1e90"
down_revision: Union[str, None] = "7c1d9e4a2b83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("fixation_input_snapshots") as batch_op:
        batch_op.add_column(sa.Column("planner_review_context", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("fixation_input_snapshots") as batch_op:
        batch_op.drop_column("planner_review_context")
