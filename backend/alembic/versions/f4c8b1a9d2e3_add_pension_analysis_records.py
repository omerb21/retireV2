"""add pension analysis records

Revision ID: f4c8b1a9d2e3
Revises: e2a7c9d4f1b3
Create Date: 2026-07-02 00:00:00.000000
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c8b1a9d2e3"
down_revision: Union[str, None] = "e2a7c9d4f1b3"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    op.create_table(
        "pension_analysis_record",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("pension_holding_id", sa.Integer(), nullable=False),
        sa.Column("analysis_record_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.client_id"], name="fk_pension_analysis_record_client_id"),
        sa.ForeignKeyConstraint(
            ["pension_holding_id"], ["pension_holding.id"], name="fk_pension_analysis_record_pension_holding_id"
        ),
        sa.UniqueConstraint("pension_holding_id", name="uq_pension_analysis_record_pension_holding_id"),
    )


def downgrade() -> None:
    op.drop_table("pension_analysis_record")
