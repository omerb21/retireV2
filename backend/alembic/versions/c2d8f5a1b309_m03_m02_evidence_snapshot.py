"""persist canonical M02 evidence snapshots on M03 revisions

Revision ID: c2d8f5a1b309
Revises: a1c7e4d9f208
"""

from alembic import op
import sqlalchemy as sa


revision: str = "c2d8f5a1b309"
down_revision: str | None = "a1c7e4d9f208"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "m03_review_revisions",
        sa.Column("m02_evidence_snapshot_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("m03_review_revisions", "m02_evidence_snapshot_json")
