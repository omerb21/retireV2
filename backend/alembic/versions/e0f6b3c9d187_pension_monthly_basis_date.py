"""Explicit manual pension base date; no default, inference or backfill."""
from alembic import op
import sqlalchemy as sa

revision = 'e0f6b3c9d187'
down_revision = 'd9e5a2b8c076'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('canonical_manual_pension_sources', sa.Column('base_amount_effective_date', sa.Date(), nullable=True))


def downgrade():
    if op.get_bind().execute(sa.text('SELECT 1 FROM canonical_manual_pension_sources WHERE base_amount_effective_date IS NOT NULL LIMIT 1')).first():
        raise RuntimeError('PENSION_BASIS_DOWNGRADE_WOULD_LOSE_DATES')
    op.drop_column('canonical_manual_pension_sources', 'base_amount_effective_date')
