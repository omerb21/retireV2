"""allow PKG-002 CBS calculation failure statuses

Revision ID: c2f8a4d1e706
Revises: b7e4c2d9a105
Create Date: 2026-07-21 17:00:00.000000

The upgrade changes only the fixation-run status check constraint and preserves
all rows. Downgrade is refused while PKG-002-only statuses remain because those
rows cannot satisfy the previous constraint without destructive rewriting.
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2f8a4d1e706"
down_revision: Union[str, None] = "b7e4c2d9a105"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    with op.batch_alter_table("fixation_runs") as batch_op:
        batch_op.drop_constraint("ck_fixation_runs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_fixation_runs_status",
            "status IN ('success', 'validation_failed', 'unsupported', "
            "'requires_special_handling', 'calculation_failed', 'unsupported_calculation')",
        )


def downgrade() -> None:
    connection = op.get_bind()
    blocked_count = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM fixation_runs "
            "WHERE status IN ('calculation_failed', 'unsupported_calculation')"
        )
    ).scalar_one()
    if blocked_count:
        raise RuntimeError(
            "Cannot downgrade while PKG-002 calculation failure statuses are present"
        )

    with op.batch_alter_table("fixation_runs") as batch_op:
        batch_op.drop_constraint("ck_fixation_runs_status", type_="check")
        batch_op.create_check_constraint(
            "ck_fixation_runs_status",
            "status IN ('success', 'validation_failed', 'unsupported', 'requires_special_handling')",
        )
