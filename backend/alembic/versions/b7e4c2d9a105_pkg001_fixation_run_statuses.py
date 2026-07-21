"""allow PKG-001 non-success fixation run statuses

Revision ID: b7e4c2d9a105
Revises: f4c8b1a9d2e3
Create Date: 2026-07-21 15:00:00.000000
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e4c2d9a105"
down_revision: Union[str, None] = "f4c8b1a9d2e3"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    with op.batch_alter_table("fixation_runs") as batch_op:
        batch_op.drop_constraint("ck_fixation_runs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_fixation_runs_status",
            "status IN ('success', 'validation_failed', 'unsupported', 'requires_special_handling')",
        )


def downgrade() -> None:
    with op.batch_alter_table("fixation_runs") as batch_op:
        batch_op.drop_constraint("ck_fixation_runs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_fixation_runs_status",
            "status IN ('success', 'validation_failed')",
        )
