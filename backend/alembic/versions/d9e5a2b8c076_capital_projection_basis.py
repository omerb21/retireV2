"""Explicit per-capital-source projection basis, without backfill."""
from alembic import op
import sqlalchemy as sa

revision = 'd9e5a2b8c076'
down_revision = 'c8d4f1a7b965'
branch_labels = None
depends_on = None


def upgrade():
    rate_type = sa.Text() if op.get_bind().dialect.name == 'sqlite' else sa.Numeric()
    op.create_table('capital_projection_basis_decisions',
        sa.Column('capital_asset_id', sa.Integer(), sa.ForeignKey('capital_asset.id', ondelete='RESTRICT'), primary_key=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.client_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('annual_rate', rate_type, nullable=False),
        sa.Column('return_basis', sa.String(8), nullable=False),
        sa.Column('price_basis', sa.String(8), nullable=False),
        sa.Column('contract_version', sa.String(80), nullable=False),
        sa.Column('source_semantic_fingerprint_at_decision', sa.String(64), nullable=False),
        sa.Column('timing_context_fingerprint_at_decision', sa.String(64), nullable=False),
        sa.Column('planning_calculation_input_fingerprint_at_decision', sa.String(64), nullable=False),
        sa.Column('actor', sa.String(128), nullable=False),
        sa.Column('provenance', sa.String(80), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("return_basis IN ('NET','GROSS')", name='ck_projection_return_basis'),
        sa.CheckConstraint("price_basis IN ('NOMINAL','REAL')", name='ck_projection_price_basis'),
        sa.CheckConstraint("contract_version = 'canonical-pre-retirement-projection-basis-v1'", name='ck_projection_contract'),
        sa.CheckConstraint("provenance = 'explicit_professional_capital_projection_basis'", name='ck_projection_provenance'))


def downgrade():
    if op.get_bind().execute(sa.text('SELECT 1 FROM capital_projection_basis_decisions LIMIT 1')).first():
        raise RuntimeError('PROJECTION_DOWNGRADE_WOULD_LOSE_DECISIONS')
    op.drop_table('capital_projection_basis_decisions')
