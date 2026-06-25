"""package 3 verification and missing data

Revision ID: 5b8d2e1f4c61
Revises: 4e7a1c2d9b30
Create Date: 2026-06-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5b8d2e1f4c61"
down_revision: Union[str, None] = "4e7a1c2d9b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.add_column(
            "clearinghouse_snapshots",
            sa.Column("verification_status", sa.String(length=100), nullable=False, server_default="unverified"),
        )
        op.add_column("clearinghouse_snapshots", sa.Column("verification_notes", sa.Text(), nullable=True))
        op.add_column("clearinghouse_snapshots", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(
            "retirement_planning_documents",
            sa.Column("verification_status", sa.String(length=100), nullable=False, server_default="unverified"),
        )
        op.add_column("retirement_planning_documents", sa.Column("verification_notes", sa.Text(), nullable=True))
        op.add_column("retirement_planning_documents", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    else:
        with op.batch_alter_table("clearinghouse_snapshots") as batch_op:
            batch_op.add_column(
                sa.Column("verification_status", sa.String(length=100), nullable=False, server_default="unverified")
            )
            batch_op.add_column(sa.Column("verification_notes", sa.Text(), nullable=True))
            batch_op.add_column(sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
        with op.batch_alter_table("retirement_planning_documents") as batch_op:
            batch_op.add_column(
                sa.Column("verification_status", sa.String(length=100), nullable=False, server_default="unverified")
            )
            batch_op.add_column(sa.Column("verification_notes", sa.Text(), nullable=True))
            batch_op.add_column(sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "missing_data_items",
        sa.Column("missing_data_item_id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("missing_item_type", sa.String(length=50), nullable=False),
        sa.Column("missing_item_label", sa.String(length=255), nullable=False),
        sa.Column("missing_status", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.client_id"]),
        sa.PrimaryKeyConstraint("missing_data_item_id"),
    )


def downgrade() -> None:
    op.drop_table("missing_data_items")
    with op.batch_alter_table("retirement_planning_documents") as batch_op:
        batch_op.drop_column("verified_at")
        batch_op.drop_column("verification_notes")
        batch_op.drop_column("verification_status")
    with op.batch_alter_table("clearinghouse_snapshots") as batch_op:
        batch_op.drop_column("verified_at")
        batch_op.drop_column("verification_notes")
        batch_op.drop_column("verification_status")
