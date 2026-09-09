"""Add historical-compatible source batch identity without changing evidence."""
from alembic import op
import sqlalchemy as sa

revision = "e4f0b7c3d521"
down_revision = "d3e9a6b2c410"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pension_product_source_links", sa.Column("batch_identity", sa.String(64), nullable=True))
    op.create_index("ix_pension_source_client_batch", "pension_product_source_links", ["client_id", "batch_identity"])


def downgrade():
    # Dropping batch membership after writes would lose overlap protection.
    raise RuntimeError("SOURCE_BATCH_DOWNGRADE_PROHIBITED: restore a verified pre-upgrade backup")
