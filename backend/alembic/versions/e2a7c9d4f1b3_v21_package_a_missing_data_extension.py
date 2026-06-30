"""v21 package a missing data extension

Revision ID: e2a7c9d4f1b3
Revises: d1f4a8c2e9b0
Create Date: 2026-06-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2a7c9d4f1b3"
down_revision: Union[str, None] = "d1f4a8c2e9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("missing_data_items") as batch_op:
        batch_op.add_column(sa.Column("planning_domain", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("related_record_type", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("related_record_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("advisory_status", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("neutral_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("missing_data_items") as batch_op:
        batch_op.drop_column("neutral_reason")
        batch_op.drop_column("advisory_status")
        batch_op.drop_column("related_record_id")
        batch_op.drop_column("related_record_type")
        batch_op.drop_column("planning_domain")
