"""bind M03 authority to deterministic M02 evidence

Revision ID: a1c7e4d9f208
Revises: e6b4c8d2f507
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a1c7e4d9f208"
down_revision: str | None = "e6b4c8d2f507"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "m03_review_revisions",
        sa.Column("m02_evidence_digest", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("m03_review_revisions", "m02_evidence_digest")
