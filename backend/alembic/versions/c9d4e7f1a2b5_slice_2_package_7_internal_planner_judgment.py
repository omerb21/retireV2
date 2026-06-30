"""slice 2 package 7 internal planner judgment

Revision ID: c9d4e7f1a2b5
Revises: 8a4f6c2d1e90
Create Date: 2026-06-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9d4e7f1a2b5"
down_revision: Union[str, None] = "8a4f6c2d1e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "internal_planner_judgments",
        sa.Column("internal_planner_judgment_id", sa.String(length=64), nullable=False),
        sa.Column("fixation_run_id", sa.Integer(), nullable=False),
        sa.Column("handling_status", sa.String(length=64), nullable=False),
        sa.Column("next_internal_action", sa.Text(), nullable=False),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "handling_status IN ("
            "'not_used_for_decision', "
            "'continue_internal_review', "
            "'internal_action_identified'"
            ")",
            name="ck_internal_planner_judgments_handling_status",
        ),
        sa.ForeignKeyConstraint(["fixation_run_id"], ["fixation_runs.id"]),
        sa.PrimaryKeyConstraint("internal_planner_judgment_id"),
        sa.UniqueConstraint("fixation_run_id"),
    )


def downgrade() -> None:
    op.drop_table("internal_planner_judgments")
