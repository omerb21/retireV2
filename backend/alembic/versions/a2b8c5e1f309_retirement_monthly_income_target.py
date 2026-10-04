"""Canonical retirement monthly income target authority."""
from alembic import op
import sqlalchemy as sa

revision = "a2b8c5e1f309"
down_revision = "f1a7c4d0e298"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "retirement_monthly_income_target_elections",
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.client_id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("lifecycle_state", sa.String(16), nullable=False),
        sa.Column("planning_calculation_input_fingerprint", sa.String(64), nullable=False),
        sa.Column("retirement_target_date", sa.Date(), nullable=False),
        sa.Column("monthly_amount_text", sa.String(25), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("income_basis", sa.String(8), nullable=False),
        sa.Column("price_basis", sa.String(40), nullable=False),
        sa.Column("price_reference_date", sa.Date(), nullable=True),
        sa.Column("source_kind", sa.String(40), nullable=False),
        sa.Column("confirmation_state", sa.String(16), nullable=False),
        sa.Column("confirmation_actor", sa.String(128), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_semantic_fingerprint", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("version BETWEEN 1 AND 9223372036854775807", name="ck_rit_version"),
        sa.CheckConstraint("lifecycle_state IN ('CONFIRMED','STALE')", name="ck_rit_lifecycle"),
        sa.CheckConstraint("currency = 'ILS'", name="ck_rit_currency"),
        sa.CheckConstraint("income_basis IN ('GROSS','NET')", name="ck_rit_income_basis"),
        sa.CheckConstraint("price_basis IN ('NOMINAL_AT_RETIREMENT_TARGET_DATE','REAL_AT_REFERENCE_DATE')", name="ck_rit_price_basis"),
        sa.CheckConstraint("(price_basis = 'NOMINAL_AT_RETIREMENT_TARGET_DATE' AND price_reference_date IS NULL) OR (price_basis = 'REAL_AT_REFERENCE_DATE' AND price_reference_date IS NOT NULL)", name="ck_rit_price_reference"),
        sa.CheckConstraint("source_kind IN ('CLIENT_SUPPLIED','PLANNER_SUPPLIED','CLIENT_SUPPLIED_PLANNER_CONFIRMED')", name="ck_rit_source_kind"),
        sa.CheckConstraint("confirmation_state = 'CONFIRMED'", name="ck_rit_confirmation_state"),
        sa.CheckConstraint("length(confirmation_actor) BETWEEN 1 AND 128", name="ck_rit_actor_length"),
    )


def downgrade():
    op.drop_table("retirement_monthly_income_target_elections")
