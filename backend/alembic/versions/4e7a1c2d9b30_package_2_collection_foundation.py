"""package 2 collection foundation

Revision ID: 4e7a1c2d9b30
Revises: 3d2f8a7b4c19
Create Date: 2026-06-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4e7a1c2d9b30"
down_revision: Union[str, None] = "3d2f8a7b4c19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clearinghouse_snapshots",
        sa.Column("clearinghouse_snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("import_date", sa.Date(), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("collection_status", sa.String(length=100), nullable=False),
        sa.Column("collection_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.client_id"]),
        sa.PrimaryKeyConstraint("clearinghouse_snapshot_id"),
    )
    op.create_table(
        "retirement_planning_documents",
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=True),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("collection_date", sa.Date(), nullable=False),
        sa.Column("collection_status", sa.String(length=100), nullable=False),
        sa.Column("collection_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.client_id"]),
        sa.PrimaryKeyConstraint("document_id"),
    )


def downgrade() -> None:
    op.drop_table("retirement_planning_documents")
    op.drop_table("clearinghouse_snapshots")
