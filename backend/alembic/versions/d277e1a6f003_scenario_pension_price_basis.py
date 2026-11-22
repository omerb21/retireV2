"""Add explicit price comparison evidence for scenario-decision pensions.

Revision ID: d277e1a6f003
Revises: c194e2f0a816
"""
from alembic import op
import sqlalchemy as sa

revision = "d277e1a6f003"
down_revision = "c194e2f0a816"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "scenario_pension_price_basis_decisions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scenario_id", sa.String(64), sa.ForeignKey("scenario_drafts.scenario_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision_id", sa.String(64), sa.ForeignKey("scenario_draft_decisions.decision_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scenario_version", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("target_fingerprint", sa.String(64), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("price_basis", sa.String(48), nullable=False),
        sa.Column("actor_id", sa.String(128), nullable=False),
        sa.Column("record_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("client_id", "scenario_id", "decision_id", "revision", name="uq_s6_price_basis_revision"),
        sa.CheckConstraint("scenario_version > 0 AND revision > 0", name="ck_s6_price_basis_versions"),
        sa.CheckConstraint("price_basis IN ('NOMINAL_AT_RETIREMENT_TARGET_DATE','UNKNOWN')", name="ck_s6_price_basis_choice"),
        sa.CheckConstraint("length(actor_id) BETWEEN 1 AND 128", name="ck_s6_price_basis_actor"),
        sa.CheckConstraint("length(source_fingerprint) = 64 AND length(target_fingerprint) = 64 AND length(record_fingerprint) = 64", name="ck_s6_price_basis_hashes"),
    )


def downgrade():
    # Do not silently destroy professional decision history.
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM scenario_pension_price_basis_decisions")):
        raise RuntimeError("S6_PRICE_BASIS_DOWNGRADE_WOULD_DELETE_DECISIONS")
    op.drop_table("scenario_pension_price_basis_decisions")
