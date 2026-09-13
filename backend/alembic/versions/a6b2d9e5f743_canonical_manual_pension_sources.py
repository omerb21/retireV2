"""Add canonical manual pension facts, without rewriting any existing source."""
from alembic import op
import sqlalchemy as sa

revision = "a6b2d9e5f743"
down_revision = "f5a1c8d4e632"
branch_labels = None
depends_on = None


def upgrade():
    money = sa.String(22) if op.get_bind().dialect.name == "sqlite" else sa.Numeric(20, 2)
    op.create_table("canonical_manual_pension_sources",
        sa.Column("manual_pension_source_id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("input_mode", sa.String(16), nullable=False),
        sa.Column("payer_name", sa.String(255)), sa.Column("description", sa.Text()),
        sa.Column("source_reference", sa.String(255)),
        sa.Column("monthly_amount", money), sa.Column("balance", money),
        sa.Column("annuity_factor", sa.String(128)), sa.Column("pension_start_date", sa.Date()),
        sa.Column("tax_treatment", sa.String(64)), sa.Column("indexation_method", sa.String(64)),
        sa.Column("fixed_indexation_rate", sa.String(128)), sa.Column("source_note", sa.Text()),
        sa.Column("lifecycle_status", sa.String(16), nullable=False, server_default="current"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("input_mode IN ('entered','calculated')", name="ck_manual_pension_mode"),
        sa.CheckConstraint("lifecycle_status IN ('current','superseded')", name="ck_manual_pension_lifecycle"),
        sa.CheckConstraint("version > 0", name="ck_manual_pension_version"),
        sa.CheckConstraint("monthly_amount IS NULL OR CAST(monthly_amount AS NUMERIC) >= 0", name="ck_manual_pension_amount"),
        sa.CheckConstraint("balance IS NULL OR CAST(balance AS NUMERIC) >= 0", name="ck_manual_pension_balance"),
        sa.CheckConstraint("annuity_factor IS NULL OR CAST(annuity_factor AS NUMERIC) > 0", name="ck_manual_pension_factor"),
        sa.CheckConstraint("(input_mode = 'entered' AND balance IS NULL AND annuity_factor IS NULL) OR (input_mode = 'calculated' AND monthly_amount IS NULL)", name="ck_manual_pension_exclusive"))
    op.create_index("ix_canonical_manual_pension_sources_client_id", "canonical_manual_pension_sources", ["client_id"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT 1 FROM canonical_manual_pension_sources LIMIT 1")).first():
        raise RuntimeError("MANUAL_PENSION_SOURCE_DOWNGRADE_WOULD_LOSE_HISTORY")
    op.drop_table("canonical_manual_pension_sources")
